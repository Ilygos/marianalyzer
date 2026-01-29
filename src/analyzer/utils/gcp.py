"""GCP utilities for authentication and service communication."""

import os
from typing import Optional

try:
    import google.auth
    import google.auth.transport.requests
    from google.auth.credentials import Credentials
    HAS_GCP = True
except ImportError:
    HAS_GCP = False


def get_cloud_run_token(target_audience: Optional[str] = None) -> Optional[str]:
    """
    Get an OIDC token for authenticating to Cloud Run services.
    
    Args:
        target_audience: The URL of the target Cloud Run service.
                        If None, tries to get from environment.
    
    Returns:
        OIDC token string or None if GCP auth is not available.
    """
    if not HAS_GCP:
        return None
    
    try:
        # Get default credentials
        credentials, project = google.auth.default()
        
        # If running in Cloud Run, use the identity token
        if hasattr(credentials, "token"):
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            return credentials.token
            
        return None
    except Exception:
        # If we can't get credentials, return None
        return None


def get_authenticated_headers(target_audience: Optional[str] = None) -> dict:
    """
    Get headers with authentication token for Cloud Run service.
    
    Args:
        target_audience: The URL of the target Cloud Run service.
    
    Returns:
        Dictionary of headers including Authorization if available.
    """
    token = get_cloud_run_token(target_audience)
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def is_running_on_cloud_run() -> bool:
    """Check if code is running on Cloud Run."""
    return os.getenv("K_SERVICE") is not None
