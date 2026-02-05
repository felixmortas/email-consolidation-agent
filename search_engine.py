"""
Search engine module providing web search functionality through multiple providers.
This module implements a search engine with pluggable providers for performing web searches.
It supports both real API-based search (Brave Search API) and mock search for testing purposes.
Providers:
    - BraveProvider: Uses the Brave Search API for real web searches
    - MockProvider: Returns predefined mock results for testing without API consumption
Environment Variables:
    BRAVE_API_KEY: API key for Brave Search API authentication
Attributes:
    search_engine: Active search provider instance (currently configured as MockProvider)
"""
import requests
import os

# Load environment variables: Brave API key
from dotenv import load_dotenv
load_dotenv()

BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

# --- PROVIDERS CONFIGURATION ---

class BraveProvider:
    """Brave Search API provider"""
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.search.brave.com/res/v1/web/search"
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }

    def search(self, query, num_results=5):
        params = {"q": query}
        response = requests.get(self.url, headers=self.headers, params=params)
        
        # Check if response is successful
        if response.status_code != 200:
            return []

        results = response.json()
        web_results = results.get("web", {}).get("results", [])
        
        return [item['url'] for item in web_results[:num_results]]
        
class MockProvider:
    """A test provider to avoid unnecessary API consumption"""
    def search(self, query, num_results=5):
        return ['https://www.agrosemens.com/', 'https://graines-biologiques.com/', 'https://www.facebook.com/agrosemens.semencesbio/?locale=fr_FR', 'https://www.instagram.com/agrosemens_bio/', 'https://fr.linkedin.com/company/agrosemens']
    
# search_engine = BraveProvider(BRAVE_API_KEY)
search_engine = MockProvider()
