"""Pydantic schemas for LLM structured outputs."""
from pydantic import BaseModel, Field


class URLSelection(BaseModel):
    """Selected URL from search results."""
    
    url: str = Field(
        description="The most likely official homepage URL"
    )


class CSSSelector(BaseModel):
    """CSS selector for a DOM element."""
    
    selector: str = Field(
        description="The CSS selector (e.g., '#login-id' or '.btn-class')"
    )
    href: str = Field(
        description="The href attribute if available",
    )
    text: str = Field(
        description="The innerText of the selected element"
    )


class PageAnalysis(BaseModel):
    """Analysis of whether a page is a login page."""
    
    is_page_reached: bool = Field(
        description="Whether the page appears to be a login page"
    )
    username_selector: str = Field(
        description="CSS selector for the username field, if identified"
    )
    password_selector: str = Field(
        description="CSS selector for the password field, if identified"
    )
    submit_selector: str = Field(
        description="CSS selector for the submit button, if identified"
    )

class ChangeEmailSectionAnalysis(BaseModel):
    """Analysis of whether the change email section is reached."""
    
    is_page_reached: bool = Field(
        description="Whether the change email section appears to be reached"
    )
    next_action_location: str = Field(
        description="Description of where to click or navigate next (e.g., 'Click the change email link with selector .change-email')"
    )
