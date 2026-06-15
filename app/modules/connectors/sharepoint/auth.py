import httpx
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

class SharePointAuthManager:
    def __init__(self):
        self.client_id = None
        self.client_secret = None
        self.tenant_id = None
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = 0

    def load_credentials(self, credentials: dict) -> dict:
        self.client_id = credentials.get("client_id")
        self.client_secret = credentials.get("client_secret")
        self.tenant_id = credentials.get("tenant_id")
        self._access_token = credentials.get("access_token")
        self._refresh_token = credentials.get("refresh_token")
        return credentials

    async def get_valid_token(self) -> str:
        # If we have a token and it's not expired (giving a 60s buffer)
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        if not self.client_id or not self.client_secret or not self.tenant_id:
            raise ValueError("SharePoint credentials are not fully loaded")

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        if self._refresh_token:
            # 3-legged OAuth refresh token flow
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token"
            }
        else:
            # 2-legged App-only flow
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials"
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            if response.status_code != 200:
                logger.error(f"Failed to acquire MS Graph token: {response.text}")
                raise RuntimeError("Authentication failed with Microsoft Entra ID")
            
            result = response.json()
            self._access_token = result["access_token"]
            if "refresh_token" in result:
                self._refresh_token = result["refresh_token"]
            self._token_expires_at = time.time() + result.get("expires_in", 3600)
            
            return self._access_token

async def execute_graph_request(auth_manager: SharePointAuthManager, method: str, endpoint: str, **kwargs) -> dict:
    token = await auth_manager.get_valid_token()
    headers = kwargs.get("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    headers["Accept"] = "application/json"
    kwargs["headers"] = headers

    # Microsoft Graph API Base URL
    base_url = "https://graph.microsoft.com/v1.0"
    url = f"{base_url}{endpoint}" if endpoint.startswith("/") else f"{base_url}/{endpoint}"

    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, **kwargs)
        if response.status_code >= 400:
            logger.error(f"MS Graph Request Failed: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        # Check for 204 No Content
        if response.status_code == 204:
            return {}
            
        return response.json()
