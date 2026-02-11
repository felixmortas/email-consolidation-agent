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

def verify_login_success(page, state, initial_url, new_url):
    """
    Multi-layered verification to determine if login was successful.
    Args:
        page: Playwright page instance
        state: Current state with form selectors
        initial_url: URL before login attempt
        new_url: URL after login attempt
    Returns:
        Boolean indicating login success
    """
    try:
        # Check 1: URL changed (most reliable for most sites)
        url_changed = new_url != initial_url and "/login" not in new_url.lower()
        print(f"[DEBUG] URL changed: {url_changed} ({initial_url} -> {new_url})")
        
        # Check 2: Login form disappeared
        # FIX: Passer les sélecteurs comme arguments plutôt que de les interpoler
        form_disappeared = page.evaluate("""(selectors) => {
            const usernameField = document.querySelector(selectors.username);
            const passwordField = document.querySelector(selectors.password);
            const submitButton = document.querySelector(selectors.submit);
            // If none of these exist, form disappeared
            return !usernameField && !passwordField && !submitButton;
        }""", {
            "username": state.get("username_selector", ""),
            "password": state.get("password_selector", ""),
            "submit": state.get("submit_selector", "")
        })
        print(f"[DEBUG] Login form disappeared: {form_disappeared}")
        
        # Check 3: No error messages
        no_errors = page.evaluate("""() => {
            const errorIndicators = [
                'error', 'invalid', 'incorrect', 'failed', 
                'wrong', 'échec', 'erreur', 'invalide'
            ];
            const pageText = document.body.innerText.toLowerCase();
            // Check for visible error messages
            const errorElements = document.querySelectorAll('[class*="error"], [class*="alert"], [role="alert"]');
            const hasVisibleError = Array.from(errorElements).some(el => {
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden';
            });
            const hasErrorText = errorIndicators.some(indicator => pageText.includes(indicator));
            return !hasVisibleError && !hasErrorText;
        }""")
        print(f"[DEBUG] No error messages: {no_errors}")
        
        # Check 4: Success indicators present
        success_indicators = page.evaluate("""() => {
            const successTerms = [
                'dashboard', 'welcome', 'bienvenue', 'account', 
                'profile', 'logout', 'déconnexion', 'mon compte'
            ];
            const pageText = document.body.innerText.toLowerCase();
            const hasSuccessTerm = successTerms.some(term => pageText.includes(term));
            // Check for logout button (strong indicator of being logged in)
            const logoutButton = document.querySelector(
                'a[href*="logout"], button[href*="logout"], ' +
                'a[href*="signout"], button[href*="signout"], ' +
                'a[href*="déconnexion"], button[href*="déconnexion"]'
            );
            return hasSuccessTerm || !!logoutButton;
        }""")
        print(f"[DEBUG] Success indicators present: {success_indicators}")
        
        # Decision logic: require multiple positive signals
        success = (url_changed and no_errors) or \
                  (form_disappeared and no_errors) or \
                  (success_indicators and no_errors and (url_changed or form_disappeared))
        
        return success
        
    except Exception as e:
        print(f"[ERROR] Error during login verification: {e}")
        # If verification fails, default to False (safer)
        return False