import operator
from typing import Annotated, Literal, Optional, TypedDict


class InputState(TypedDict):
    website_name: str
    initial_url: Optional[str]

class OutputState(TypedDict):
    output_status: str

class OverallState(TypedDict):
    # Input states    
    website_name: str
    initial_url: Optional[str]

    # Output states
    output_status: str

    # Page Content tracking
    current_url: str
    navigation_method: Optional[Literal["url", "click"]]
    # current_dom: Optional[str]        # Cleaned Markdown/DOM
    # screenshot: Optional[str]          # Base64 or path for vlm_fallback
    # are_cookies_accepted: bool
    is_login_page_reached: bool
    username_selector: Optional[str]
    password_selector: Optional[str]
    submit_selector: Optional[str]
    # has_captcha: bool
    # is_logged_in: bool
    # is_change_password_page_reached: bool   

    # Navigation Logic
    # We use a list to track steps taken, or a simple count for fallbacks
    url_history: Annotated[list[str], operator.add] 
    retry_count: int                   # Tracks tries for Maps_to_login
    
    # The identified "Click Target" (ID, CSS selector, or description)
    next_action_location: Optional[str]
    login_href: Optional[str]          # The href associated with the login button, if any

    login_success: Optional[bool]           # Tracks if login was successful, for retry logic
    
    # Status tracking
    error: Optional[str]