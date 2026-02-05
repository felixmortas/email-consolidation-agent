from typing import Optional


def determine_navigation_method(href: Optional[str]) -> str:
    """Determine if we should navigate by URL or click."""
    if not href:
        return "click"
    
    href_lower = href.lower()
    
    # Cas où il faut cliquer
    if href_lower in ['#', 'javascript:void(0)', 'javascript:;']:
        return "click"
    
    # Cas où c'est une vraie URL
    if href_lower.startswith(('http://', 'https://', '/')):
        return "url"
    
    # Par défaut, cliquer (plus sûr)
    return "click"