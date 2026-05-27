"""Google Authentication and Client Manager for GraphMind Connectors"""

import logging
from typing import Any, Dict, List, Optional
import httpx
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import credentials as google_credentials
from google.oauth2 import service_account
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Standard scopes required for Google Drive indexing & user discovery
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
]


class GoogleAPIError(Exception):
    """Base exception for Google API client transport failures"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Google API Error {status_code}: {message}")


class GoogleRateLimitError(GoogleAPIError):
    """Exception raised for Google API rate limit (403/429) errors"""
    pass


class GoogleAuthManager:
    """
    Manages loading Google credentials, refreshing access tokens,
    and generating authenticated async HTTPX clients for Google Drive APIs.
    """

    def __init__(self) -> None:
        self.creds: Optional[Any] = None
        self.creds_dict: Dict[str, Any] = {}
        self.is_service_account: bool = False
        self.primary_admin_email: Optional[str] = None

    def load_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse credentials dict. Supports:
        1. Service Account JSON structure (requires 'type': 'service_account')
        2. Individual OAuth2 credentials (requires 'client_id', 'client_secret', 'refresh_token')
        """
        self.creds_dict = credentials.copy()
        self.primary_admin_email = credentials.get("primary_admin_email")

        # Determine authentication mode
        if credentials.get("type") == "service_account":
            self.is_service_account = True
            logger.info("Initializing Google Service Account credentials")
            self.creds = service_account.Credentials.from_service_account_info(
                credentials, scopes=SCOPES
            )
        else:
            self.is_service_account = False
            logger.info("Initializing Google User OAuth2 credentials")
            self.creds = google_credentials.Credentials(
                token=credentials.get("access_token"),
                refresh_token=credentials.get("refresh_token"),
                client_id=credentials.get("client_id"),
                client_secret=credentials.get("client_secret"),
                token_uri="https://oauth2.googleapis.com/token",
                scopes=SCOPES,
            )

        return self.creds_dict

    def get_access_token(self, impersonate_email: Optional[str] = None) -> str:
        """
        Retrieve a valid access token.
        If using a Service Account and impersonate_email is provided,
        performs domain-wide delegation to impersonate the target workspace user.
        """
        if not self.creds:
            raise ValueError("Credentials not loaded. Call load_credentials() first.")

        active_creds = self.creds

        if self.is_service_account and impersonate_email:
            logger.debug(f"Impersonating user subject: {impersonate_email}")
            # Domain-wide delegation impersonation
            active_creds = self.creds.with_subject(impersonate_email)

        # Refresh token using google-auth library
        try:
            active_creds.refresh(GoogleRequest())
            if not active_creds.token:
                raise ValueError("Refreshed token is empty.")
            return active_creds.token
        except Exception as e:
            logger.error(f"Failed to refresh Google credentials token: {e}", exc_info=True)
            raise RuntimeError(f"Authentication token refresh failed: {str(e)}")

    def get_client(self, impersonate_email: Optional[str] = None) -> httpx.AsyncClient:
        """
        Constructs an authenticated AsyncClient with standard headers
        pointing to Google APIs.
        """
        token = self.get_access_token(impersonate_email)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        return httpx.AsyncClient(
            base_url="https://www.googleapis.com",
            headers=headers,
            timeout=httpx.Timeout(30.0),
        )


# Exponential backoff retry handler for Google Drive API rate limits (403 User Rate Limit Exceeded / 429 Too Many Requests)
@retry(
    retry=retry_if_exception_type(GoogleRateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def execute_google_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Executes an async request and handles rate-limiting / error raising with tenancy retries.
    """
    response = await client.request(method, url, **kwargs)

    # 1. Handle Success
    if response.status_code in (200, 201, 204):
        if response.status_code == 204:
            return {}
        return response.json()

    # 2. Extract detailed error payload if possible
    try:
        err_data = response.json()
        err_msg = err_data.get("error", {}).get("message", response.text)
    except Exception:
        err_msg = response.text

    # 3. Handle Rate Limiting & API Quota Exceeded (HTTP 429 & specific HTTP 403 blocks)
    if response.status_code == 429 or (response.status_code == 403 and "limit" in err_msg.lower()):
        logger.warning(f"Google API rate limit hit. Status Code: {response.status_code}. Retrying... Msg: {err_msg}")
        raise GoogleRateLimitError(response.status_code, err_msg)

    # 4. Standard failures (401, 403 Unauthorized, 404, etc.)
    raise GoogleAPIError(response.status_code, err_msg)
