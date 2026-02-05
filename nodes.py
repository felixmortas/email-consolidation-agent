from context import ContextSchema
from state import InputState, OverallState, OutputState
from search_engine import search_engine
from models.llm import URLSelection, CSSSelector, PageAnalysis
from utils import determine_navigation_method

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
    search_results = search_engine.search(query, num_results=5)
    print("Search Results:", search_results)
    
    # Prepare LLM prompt for URL selection
    model = f"{runtime.context.llm_provider}:{runtime.context.llm_model}"
    llm = init_chat_model(model) \
        .with_structured_output(URLSelection) # The URLSelection class is expected to define the output schema
    prompt = f"Given the website name '{query}', pick the most likely official homepage URL from this list: {search_results}. Return the URL in a JSON format without any other text or explanation.\n\nExample output:\n{{\"url\": \"https://www.example.com/\"}}"   
    
    # response = llm.invoke([HumanMessage(content=prompt)])
    response = type('obj', (object,), {"url": "https://www.agrosemens.com/"}) # TEMPORARY: Hardcoded response for testing/debugging purposes
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
    prompt = f"Does this page content look like a Login Page (form, username, password)? Return the answer in a JSON format without any other text or explanation.\n\nExample output:\n{{\"is_login_page\": true}}\n\nContent: {page_structure}"

    response = llm.invoke([HumanMessage(content=prompt)])
    print(f"[DEBUG] Is login page: {response.is_login_page}")

    # Return state with verification results and update retry counter
    return {
        "is_login_page_reached": response.is_login_page,
        "output_status": "success" if response.is_login_page else "searching",
        "retry_count": state.get("retry_count", 0) + 1
    }
