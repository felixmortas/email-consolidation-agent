from langgraph.graph import StateGraph, START, END
from playwright.sync_api import sync_playwright
from contextlib import contextmanager

from state import OverallState, InputState, OutputState
from nodes import find_url, find_login_button, navigate_to_login, analyze_page
from context import ContextSchema

# ===================== BUILDING THE GRAPH =====================
builder = StateGraph(OverallState, input_schema=InputState, output_schema=OutputState, context_schema=ContextSchema)

builder.add_node("find_url", find_url)
builder.add_node("find_login_button", find_login_button)
builder.add_node("analyze_page", analyze_page)
builder.add_node("navigate_to_login", navigate_to_login)

# ===================== CONDITIONAL EDGES =====================
def is_url_missing(state: OverallState) -> bool:
    return state.get("initial_url") is None

def should_retry_look_for_login(state: OverallState) -> bool:
    return not state["is_login_page_reached"] or not state["retry_count"] >= 3

# ===================== EDGES =====================
builder.add_conditional_edges(START, is_url_missing, {True: "find_url", False: "find_login_button"})
builder.add_edge("find_url", "find_login_button")
builder.add_edge("find_login_button", "navigate_to_login")
builder.add_edge("navigate_to_login", "analyze_page")
builder.add_conditional_edges("analyze_page", should_retry_look_for_login, {True: "find_login_button", False: END})


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

context = ContextSchema(
            llm_provider="mistralai",
            llm_model="mistral-small-latest"
        )

with playwright_session(context):
    result = graph.invoke(
        {"website_name":"Agrosemens"}, 
        context=context
    )

print("\n=== FINAL RESULT ===")
print(result)