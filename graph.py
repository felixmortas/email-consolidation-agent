from langgraph.graph import StateGraph, START, END
from playwright.sync_api import sync_playwright
from contextlib import contextmanager

from state import OverallState, InputState, OutputState
from nodes import find_url, find_login_button, navigate_to_login, analyze_page, login, find_change_email_access, navigate_to_change_email_section, check_if_email_change_reached
from context import ContextSchema

# ===================== BUILDING THE GRAPH =====================
builder = StateGraph(OverallState, input_schema=InputState, output_schema=OutputState, context_schema=ContextSchema)

builder.add_node("find_url", find_url)
builder.add_node("find_login_button", find_login_button)
builder.add_node("analyze_page", analyze_page)
builder.add_node("navigate_to_login", navigate_to_login)
builder.add_node("login", login)
builder.add_node("find_change_email_access", find_change_email_access)
builder.add_node("navigate_to_change_email_section", navigate_to_change_email_section)
builder.add_node("check_if_email_change_reached", check_if_email_change_reached)


# ===================== CONDITIONAL EDGES =====================
def is_url_missing(state: OverallState) -> bool:
    return state.get("initial_url") is None

def should_retry_look_for_login(state: OverallState) -> bool:
    return not state["is_login_page_reached"] and state["retry_count"] < 3

def should_retry_change_email_section(state: OverallState) -> bool:
    return not state.get("is_change_email_section_reached", False) and state.get("retry_count", 0) < 3

# ===================== EDGES =====================
builder.add_conditional_edges(START, is_url_missing, {True: "find_url", False: "find_login_button"})
builder.add_edge("find_url", "find_login_button")
builder.add_edge("find_login_button", "navigate_to_login")
builder.add_edge("navigate_to_login", "analyze_page")
builder.add_conditional_edges("analyze_page", should_retry_look_for_login, {True: "find_login_button", False: "login"})
builder.add_edge("login", "find_change_email_access")
builder.add_edge("find_change_email_access", "navigate_to_change_email_section")
builder.add_edge("navigate_to_change_email_section", "check_if_email_change_reached")
builder.add_conditional_edges("check_if_email_change_reached", should_retry_change_email_section, {True: "find_change_email_access", False: END})

# ===================== PLAYWRIGHT CONTEXT MANAGER =====================
@contextmanager
def playwright_session(context: ContextSchema):
    """Context manager for managing the Playwright lifecycle"""
    with sync_playwright() as p:
        context.playwright = p
        context.browser = p.chromium.launch(headless=False)
        context.page = context.browser.new_page()
        try:
            yield context
        finally:
            context.page.close()
            context.browser.close()
            context.playwright = None
            context.browser = None
            context.page = None

# ===================== INVOKING THE GRAPH =====================
graph = builder.compile()

from dotenv import load_dotenv
import os

context = ContextSchema(
            debug_mode=True,  # Enable debug mode for detailed logging
            llm_provider="mistralai",
            llm_model="mistral-small-latest",
            username=os.getenv("EMAIL_USERNAME"),  
            password=os.getenv("EMAIL_PASSWORD")
        )

with playwright_session(context):
    result = graph.invoke(
        {"website_name":"Agrosemens"}, 
        context=context
    )

print("\n=== FINAL RESULT ===")
print(result)