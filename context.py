"""
Data class for managing context and configuration of the email consolidation agent.

This class serves as a container for LLM provider settings and Playwright browser
automation objects. It maintains the state of the browser automation environment
throughout the agent's lifecycle.

Attributes:
    llm_provider (str): The LLM provider name. Defaults to "mistralai".
    llm_model (str): The specific LLM model to use. Defaults to "mistral-small-latest".
    playwright (Optional[Playwright]): Instance of Playwright for browser automation.
        Initialized at runtime, not through constructor.
    browser (Optional[Browser]): Playwright browser instance for web automation.
        Initialized at runtime, not through constructor.
    page (Optional[Page]): Active Playwright page/tab instance for interactions.
        Initialized at runtime, not through constructor.
"""
from dataclasses import dataclass, field
from typing import Optional
from playwright.sync_api import Browser, Page, Playwright


@dataclass
class ContextSchema:
    debug_mode: bool = False  # Added debug mode flag for testing purposes

    llm_provider: str = "mistralai"
    llm_model: str = "mistral-small-latest"

    playwright: Optional[Playwright] = field(default=None, init=False)
    browser: Optional[Browser] = field(default=None, init=False)
    page: Optional[Page] = field(default=None, init=False)

    username: str = "your_username"  # Placeholder, should be set from environment variable or secure vault
    password: str = "your_password"  # Placeholder, should be set from environment variable or secure vault