from context import ContextSchema
from state import InputState, OverallState, OutputState
from search_engine import search_engine
from models.llm import URLSelection, CSSSelector, PageAnalysis, ChangeEmailSectionAnalysis
from utils import determine_navigation_method, verify_login_success

from langgraph.runtime import Runtime
from langchain_core.messages import HumanMessage
from langchain.chat_models import init_chat_model
from playwright.sync_api import sync_playwright

# Load environment variables: LLM API keys
from dotenv import load_dotenv
load_dotenv()

def find_url(state: InputState, runtime: Runtime[ContextSchema]) -> OverallState:
    """
    Search for the official URL of the site if it is not provided.
    
    This function takes a website name and uses a search engine to find potential URLs,
    then uses an LLM to select the most likely official homepage from the results.
    
    Args:
        state: The current state containing website_name and optionally initial_url
        runtime: Runtime context providing LLM configuration and other runtime info
        
    Returns:
        Updated state with initial_url and current_url set to the found URL
    """
    # Debugging: Print current state information
    print("[DEBUG] Entering find_url node")
    print("Website Name:", state["website_name"])
    print("URL provided:", state.get("initial_url"))

    # Create search query using the website name and perform search using search engine
    query = state["website_name"]
    search_results = search_engine.search(query, num_results=5, debug_mode=runtime.context.debug_mode)
    print("Search Results:", search_results)
    
    # Prepare LLM prompt for URL selection
    model = f"{runtime.context.llm_provider}:{runtime.context.llm_model}"
    llm = init_chat_model(model) \
        .with_structured_output(URLSelection) # The URLSelection class is expected to define the output schema
    prompt = f"Given the website name '{query}', pick the most likely official homepage URL from this list: {search_results}. Return the URL in a JSON format without any other text or explanation.\n\nExample output:\n{{\"url\": \"https://www.example.com/\"}}"   
    
    if runtime.context.debug_mode:
        print("[DEBUG] Debug mode enabled - using hardcoded URL response for testing")
        response = type('obj', (object,), {"url": "https://www.agrosemens.com/"}) # TEMPORARY: Hardcoded response for testing/debugging purposes
    else:
        response = llm.invoke([HumanMessage(content=prompt)])
    print(f"Found URL: {response.url}")

    # Return updated state with the found URL
    return {"initial_url": response.url, "current_url": response.url}

def find_login_button(state: OverallState, runtime: Runtime[ContextSchema]) -> OverallState:
    """
    Analyze the DOM to find the CSS selector for the login button and determine navigation method.
    
    This function examines the webpage's DOM structure to locate login/sign-in buttons
    and determines the best way to navigate to the login page (URL vs click).
    
    Args:
        state: Current state containing URL information
        runtime: Runtime context providing browser page and LLM configuration
        
    Returns:
        Updated state with login button selector, href, navigation method, and current URL
    """
    # Debugging: Print current state information
    print("[DEBUG] Entering find_login_button node")
    print("Current URL:", state.get("current_url"))

    # Get URL from either current_url or initial_url
    url = state.get("current_url") or state["initial_url"]

    # Get browser page instance from runtime context
    page = runtime.context.page

    # Navigate to the URL with minimal loading (fast load without waiting for all resources)
    page.goto(url, wait_until="domcontentloaded")
    print(page.title())

    # Extract interactive elements from the DOM
    # Only looks at links, buttons, and elements with role="button"
    # Filters to keep only elements with href, id, or class attributes
    interactive_elements = page.evaluate("""() => {
        const items = Array.from(document.querySelectorAll('a, button, [role="button"]'));
        return items.map(el => ({
            href: el.getAttribute('href'),
            id: el.id,
            class: el.className
        })).filter(item => item.href || item.id || item.class);
    }""")

    print(f"[DEBUG] Found {len(interactive_elements)} interactive elements")
    
    # Limit to first 50 elements to avoid overwhelming the LLM
    dom_summary = "\n".join([str(el) for el in interactive_elements[:50]]) # Top 50 éléments

    # Use LLM to identify the login button from the DOM elements
    model = f"{runtime.context.llm_provider}:{runtime.context.llm_model}"
    llm = init_chat_model(model) \
        .with_structured_output(CSSSelector)
    prompt = f"""In the following DOM elements, find the LOGIN or SIGN IN button.
        Return:
        - selector: a CSS selector to target this element (use id if available, otherwise class)
        - href: the href attribute value if it exists (can be null, '#', 'javascript:void(0)', or a real URL)

        Example output:
        {{"selector": "#login-btn", "href": "https://example.com/login"}}
        or
        {{"selector": ".js-login", "href": "#"}}

        DOM elements:
        {dom_summary}"""
    
    if runtime.context.debug_mode:
        print("[DEBUG] Debug mode enabled - using hardcoded selector response for testing")
        response = type('obj', (object,), {"selector": ".login", "href": "https://www.agrosemens.com/mon-compte"}) # TEMPORARY: Hardcoded response for testing/debugging purposes
    else:
        response = llm.invoke([HumanMessage(content=prompt)])
    print(f"[DEBUG] Found selector: {response.selector}, href: {response.href}")

    # Determine navigation method based on href value
    href = response.href
    navigation_method = determine_navigation_method(href)
    print(f"[DEBUG] Determined navigation method: {navigation_method}")

    # Return state with all relevant information for next steps
    return {"next_action_location": response.selector, "login_href": href, "current_url": url, "navigation_method": navigation_method}

def navigate_to_login(state: OverallState, runtime: Runtime[ContextSchema]) -> OverallState:
    """
    Navigate to login page using the appropriate method (URL or click).
    
    This function implements the actual navigation to the login page based on
    the method determined by find_login_button.
    
    Args:
        state: Current state containing navigation method and location information
        runtime: Runtime context providing browser page instance
        
    Returns:
        Updated state with URL history and new current URL
    """
    # Debugging: Print navigation information
    print("[DEBUG] Entering navigate_to_login node")
    print(f"[DEBUG] Navigation method: {state['navigation_method']}")
    print("Current URL before click:", state.get("current_url"))

    # Get navigation parameters from state
    method = state["navigation_method"]
    url = state["current_url"]

    # Get browser page instance
    page = runtime.context.page

    # Attempt navigation based on method
    try:
        if method == "url":
            # Direct URL navigation
            login_url = state["login_href"]

            # Handle relative URLs by joining with base URL
            if login_url.startswith('/'):
                from urllib.parse import urljoin
                login_url = urljoin(url, login_url)

            print(f"[DEBUG] Navigating to URL: {login_url}")
            page.goto(login_url, wait_until="domcontentloaded")
        
        else:  # method == "click" : to test
            # Click-based navigation
            selector = state["next_action_location"]
            print(f"[DEBUG] Clicking on: {selector}")
            
            # Click the element and wait for navigation or modal
            page.click(selector, timeout=10000)
            
            # Wait for page to load or handle modal
            try:
                page.wait_for_load_state("domcontentloaded")
            except:
                # If no navigation occurs, assume it's a modal popup
                page.wait_for_timeout(2000)  # Wait for modal to appear
        
        new_url = page.url
        print(f"[DEBUG] New URL after navigation: {new_url}")
            
    except Exception as e:
        # Handle navigation failures gracefully
        print(f"[ERROR] Navigation failed: {e}")
        new_url = url # Stay on same URL if navigation fails
    
    # Return updated state with navigation history
    return {"url_history": [url], "current_url": new_url}

def analyze_page(state: OverallState, runtime: Runtime[ContextSchema]) -> OverallState:
    """
    Check if the current page is indeed the login page.
    
    This function analyzes the current page content to verify whether it's
    actually a login page by looking for typical login page elements.
    
    Args:
        state: Current state containing URL information
        runtime: Runtime context providing browser page instance
        
    Returns:
        Updated state with login page verification result and retry count
    """
    # Debugging: Print analysis information
    print("[DEBUG] Entering analyze_page node")
    print("Current URL to analyze:", state.get("current_url"))
    print("URL history:", state.get("url_history"))

    # Get browser page instance
    page = runtime.context.page

    # Extract key page elements that indicate login page characteristics
    # Focuses on input fields, buttons, forms, and headers that typically appear on login pages
    page_structure = page.evaluate("""() => {
        const selectors = 'input, button, form, h1, h2';
        const elements = Array.from(document.querySelectorAll(selectors));
        return elements.map(el => {
            const tag = el.tagName.toLowerCase();
            const type = el.getAttribute('type') || '';
            const placeholder = el.getAttribute('placeholder') || '';
            const text = (el.innerText || el.value || '').substring(0, 50);
            return `<${tag} type="${type}" placeholder="${placeholder}">${text}</${tag}>`;
        }).join('\\n');
    }""")

    print(f"[DEBUG] Page structure extracted ({len(page_structure)} chars)")

    # Use LLM to determine if current page is a login page
    model = f"{runtime.context.llm_provider}:{runtime.context.llm_model}"
    llm = init_chat_model(model) \
        .with_structured_output(PageAnalysis)
    prompt = f"""
        Does this page content look like a Login Page (form, username, password)? Return the answer in a JSON format without any other text or explanation.\n
        If yes, also return the selectors for username, password and submit button\n
        \n
        Example output:\n
        {{"is_page_reached": true, "username_selector": "input[id='email']", "password_selector": "#password", "submit_selector": "button[type='submit']"}}\n
        \n
        Content: {page_structure}
    """

    if runtime.context.debug_mode:
        print("[DEBUG] Debug mode enabled - using hardcoded selector response for testing")
        response = type('obj', (object,), {"is_page_reached": True, "username_selector": "input[id='email']", "password_selector": "input[id='passwd']", "submit_selector": "input[id='SubmitLogin'][value='Identifiez-vous']"}) # TEMPORARY: Hardcoded response for testing/debugging purposes
    else:
        response = llm.invoke([HumanMessage(content=prompt)])

    print(f"[DEBUG] Is login page: {response.is_page_reached}")
    print(f"[DEBUG] Username selector: {response.username_selector}")
    print(f"[DEBUG] Password selector: {response.password_selector}")
    print(f"[DEBUG] Submit selector: {response.submit_selector}")

    # Return state with verification results and update retry counter
    return {
        "is_login_page_reached": response.is_page_reached,
        "username_selector": response.username_selector,
        "password_selector": response.password_selector,
        "submit_selector": response.submit_selector,
        "retry_count": state.get("retry_count", 0) + 1
    }

def login(state: OverallState, runtime: Runtime[ContextSchema]) -> OverallState:
    """
    Node to login into the website.
    
    This function logs in the website and updates the OverallState state accordingly. 
    If the connection is not established, it marks the process as failed.
    
    Args:
        state: Current state containing login page url
        runtime: Runtime context, the page instance is used to perform the login action

    Returns:
        Updated state with login success status and current URL
    """
    # Debugging: Print login information
    print("[DEBUG] Entering login node")
    print("Current URL for login:", state.get("current_url"))

    # Get browser page instance
    page = runtime.context.page

    # Get credentials from state or runtime context
    username = runtime.context.username
    password = runtime.context.password

    if not username or not password:
        print("[ERROR] Missing credentials")
        return {"login_success": False, "error": "Missing username or password"}
    
    initial_url = page.url

    try:                
        # Wait for form to be ready
        # print("[DEBUG] Waiting for login form to be ready...")
        # page.wait_for_selector(state["username_selector"], state="visible", timeout=5000)
        
        # Fill in the login form
        print(f"[DEBUG] Filling username field: {state['username_selector']}")
        page.fill(state["username_selector"], username, timeout=5000)
        
        print(f"[DEBUG] Filling password field: {state['password_selector']}")
        page.fill(state["password_selector"], password, timeout=5000)
        
        # Optional: Add small delay to mimic human behavior
        # page.wait_for_timeout(500)
        
        # Connect: Click the submit button and wait for navigation or response
        print(f"[DEBUG] Clicking submit button: {state['submit_selector']}")
        page.click(state["submit_selector"], timeout=5000)
        
        # Wait for navigation or response
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except:
            page.wait_for_timeout(3000)

        # Connect: OR Use Promise.all to handle navigation properly
        # with page.expect_navigation(timeout=15000, wait_until="domcontentloaded"):
        #     page.click(state["submit_selector"])
        
        new_url = page.url
        print(f"[DEBUG] URL after login attempt: {new_url}")
        
        # Verify if login was successful
        login_success = verify_login_success(page, state, initial_url, new_url)
        print(f"[DEBUG] Login success detected: {login_success}")
        
        return {
            "login_success": login_success,
            "current_url": new_url,
            "url_history": [new_url]
        }
        
    except TimeoutError as e:
        print(f"[ERROR] Timeout during login: {e}")
        return {
            "login_success": False,
            "error": f"Timeout during login process: {str(e)}",
        }

    except Exception as e:
        print(f"[ERROR] Login failed with exception: {e}")
        return {
            "login_success": False,
            "error": str(e),
        }

def find_change_email_access(state: OverallState, runtime: Runtime[ContextSchema]) -> OverallState:
    """
    Analyze the DOM to find the CSS selector for the button which leads to the change email section, and determine navigation method.
    
    This function examines the webpage's DOM structure to locate the button which leads to the change email section
    and determines the best way to navigate to the change email section (URL vs click).
    
    Args:
        state: Current state containing URL information
        runtime: Runtime context providing browser page and LLM configuration
        
    Returns:
        Updated state with button selector which leads to the change email section, href, navigation method, and current URL
    """
    # Debugging: Print current state information
    print("[DEBUG] Entering find_change_email_access node")
    print("Current URL:", state["current_url"])

    # Get URL from either current_url or initial_url
    url = state["current_url"]

    # Get browser page instance from runtime context
    page = runtime.context.page

    # Extract interactive elements from the DOM
    # Only looks at links, buttons, and elements with role="button"
    interactive_elements = page.evaluate("""() => {
        const items = Array.from(document.querySelectorAll('a, button, [role="button"]'));
        return items.map(el => ({
            text: el.innerText,
        })).filter(item => item.text && item.text.trim() !== '');
    }""")
    print(f"[DEBUG] Found {len(interactive_elements)} interactive elements")
    
    # Limit to first 50 elements to avoid overwhelming the LLM
    # dom_summary = "\n".join([str(el) for el in interactive_elements[:50]]) # Top 50 éléments
    dom_summary = "\n".join([str(el['text']) for el in interactive_elements]) # All elements

    # Use LLM to identify the login button from the DOM elements
    model = f"{runtime.context.llm_provider}:{runtime.context.llm_model}"
    llm = init_chat_model(model) \
        .with_structured_output(CSSSelector)
    prompt = f"""In the following DOM elements, find the button which leads to the change email section directly or to an intermediate page.
        Return 'text': the innerText to target this element

        Example output:
        {{"text": "Personal informations"}}

        DOM elements:
        {dom_summary}"""
    
    if runtime.context.debug_mode:
        print("[DEBUG] Debug mode enabled - using hardcoded selector response for testing")
        response = type('obj', (object,), {"text": "Mes informations personnelles"}) # TEMPORARY: Hardcoded response for testing/debugging purposes
    else:
        response = llm.invoke([HumanMessage(content=prompt)])
    print(f"[DEBUG] Found innerText: {response.text}")

    # Return state with all relevant information for next steps
    return {"next_action_location": response.text, "current_url": url}

def navigate_to_change_email_section(state: OverallState, runtime: Runtime[ContextSchema]) -> OverallState:
    """
    Navigate to change email section using the appropriate method (URL or click).
    
    This function implements the actual navigation to the change email section based on
    the method determined by find_change_email_access.
    
    Args:
        state: Current state containing navigation method and location information
        runtime: Runtime context providing browser page instance
        
    Returns:
        Updated state with URL history and new current URL
    """
    # Debugging: Print navigation information
    print("[DEBUG] Entering navigate_to_change_email_section node")
    print("Current URL before click:", state.get("current_url"))

    # Get navigation parameters from state
    url = state["current_url"]

    # Get browser page instance
    page = runtime.context.page

    # Attempt navigation based on method
    try:        
        # Click-based navigation
        selector = state["next_action_location"]
        print(f"[DEBUG] Clicking on: {selector}")
        
        # Click the element and wait for navigation or modal
        page.get_by_text(selector).first.click(timeout=10000)
        
        # Wait for page to load or handle modal
        try:
            page.wait_for_load_state("domcontentloaded")
        except:
            # If no navigation occurs, assume it's a modal popup
            page.wait_for_timeout(2000)  # Wait for modal to appear
    
        new_url = page.url
        print(f"[DEBUG] New URL after navigation: {new_url}")
            
    except Exception as e:
        # Handle navigation failures gracefully
        print(f"[ERROR] Navigation failed: {e}")
        new_url = url # Stay on same URL if navigation fails
    
    # Return updated state with navigation history
    return {"url_history": [url], "current_url": new_url}

def check_if_email_change_reached(state: OverallState, runtime: Runtime[ContextSchema]) -> OverallState:
    """
    Check if the current page is indeed the change email section.
    
    This function analyzes the current page content to verify whether it's
    actually the change email section by looking for typical elements.
    If it is not, it gives the information to the graph to retry to find the change email access up to 3 times before failing.
    
    Args:
        state: Current state containing URL information
        runtime: Runtime context providing browser page instance
    Returns:
        Updated state with change email section verification result, retry count and next action location for retry
    """
    # Debugging: Print analysis information
    print("[DEBUG] Entering check_if_email_change_reached node")
    print("Current URL to analyze:", state.get("current_url"))

    # Get browser page instance
    page = runtime.context.page

    # Extract key page elements that indicate change email section characteristics
    page_structure = page.evaluate("""() => {
        const selectors = 'input, button, form, h1, h2';
        const elements = Array.from(document.querySelectorAll(selectors));
        return elements.map(el => {
            const tag = el.tagName.toLowerCase();
            const text = el.innerText;
            return `<${tag}>${text}</${tag}>`;
        }).join('\\n');
    }""")

    print(f"[DEBUG] Page structure extracted ({len(page_structure)} chars)")

    # Use LLM to determine if current page is the change email section
    model = f"{runtime.context.llm_provider}:{runtime.context.llm_model}"
    llm = init_chat_model(model) \
        .with_structured_output(ChangeEmailSectionAnalysis)
    prompt = f"""Does this page content look like a Change Email Section (form to change email, current email displayed, etc.)? If not, which text element is most likely to be a button to the next step? Return the answer in a JSON format without any other text or explanation.
    
    Example output if change email section is reached:
    {{"is_page_reached": true}}
    Example output if change email section is not reached:
    {{"is_page_reached": false, "next_action_location": "Personal informations"}}
    \n{page_structure}
    """

    if runtime.context.debug_mode:
        print("[DEBUG] Debug mode enabled - using hardcoded response for testing")
        response = type('obj', (object,), {"is_page_reached": True}) # TEMPORARY: Hardcoded response for testing/debugging purposes
    else:
        response = llm.invoke([HumanMessage(content=prompt)])
    print(f"[DEBUG] LLM response: {response}")
    
    print(f"[DEBUG] Is change email section: {response.is_page_reached}")

    # Return updated state with verification result
    return {"is_change_email_section_reached": response.is_page_reached, "next_action_location": response.next_action_location if not response.is_page_reached else None, "current_url": page.url}