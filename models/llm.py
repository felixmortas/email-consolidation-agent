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


class PageAnalysis(BaseModel):
    """Analysis of whether a page is a login page."""
    
    is_login_page: bool = Field(
        description="Whether the page appears to be a login page"
    )
