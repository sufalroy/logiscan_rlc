import asyncio
import threading
import httpx
import logging
from typing import Optional, Dict, Any, Tuple


class AlarmClient:
    def __init__(self, alarm_uri: str, username: str = "admin", password: str = "adminpass"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_url = alarm_uri.rstrip('/')
        self.auth = (username, password)
        
        self.urls = {
            "login": f"{self.base_url}/login",
            "refresh": f"{self.base_url}/refresh",
            "alarm": f"{self.base_url}/trigger_alarm",
            "status": f"{self.base_url}/alarm_status"
        }
        
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        
        self._initialize_tokens()
        
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        self._token_lock = threading.Lock()

    def _initialize_tokens(self) -> None:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    self.urls["login"],
                    auth=self.auth,
                    json={"key": "value"}
                )
                response.raise_for_status()
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                
                if not self.access_token or not self.refresh_token:
                    raise ValueError("Failed to obtain tokens during initialization")
        except (httpx.HTTPError, ValueError) as e:
            self.logger.error(f"Login failed: {e}")
            raise

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _refresh_access_token(self) -> bool:
        with self._token_lock:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        self.urls["refresh"],
                        json={"refresh_token": self.refresh_token}
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    self.access_token = data.get("access_token")
                    if "refresh_token" in data:
                        self.refresh_token = data["refresh_token"]
                        
                    self.logger.info("Access token refreshed successfully")
                    return True
            except (httpx.HTTPError, KeyError) as e:
                self.logger.error(f"Failed to refresh access token: {e}")
                return False

    def trigger_alarm(self) -> None:
        if not self.access_token:
            self.logger.error("Cannot trigger alarm: No valid access token available")
            return
            
        future = asyncio.run_coroutine_threadsafe(self._trigger_alarm_async(), self.loop)
        try:
            future.result(timeout=30)
        except (asyncio.TimeoutError, Exception) as e:
            self.logger.error(f"Error triggering alarm: {e}")

    async def _trigger_alarm_async(self) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await self._execute_alarm_sequence(client)
    
    async def _execute_alarm_sequence(self, client: httpx.AsyncClient) -> None:
        try:
            headers = self._get_auth_headers()
            status_active = await self._check_alarm_status(client, headers)
            
            if not status_active:
                await self._activate_alarm(client, headers)
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                await self._handle_unauthorized(client)
            else:
                self.logger.error(f"HTTP error during alarm trigger: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during alarm trigger: {e}")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def _check_alarm_status(self, client: httpx.AsyncClient, headers: Dict[str, str]) -> bool:
        status_response = await client.get(self.urls["status"], headers=headers)
        status_response.raise_for_status()
        status_data = status_response.json()
        return status_data.get("status") == "active"
    
    async def _activate_alarm(self, client: httpx.AsyncClient, headers: Dict[str, str]) -> None:
        alarm_response = await client.post(self.urls["alarm"], headers=headers)
        alarm_response.raise_for_status()
        self.logger.info("Alarm triggered successfully")
    
    async def _handle_unauthorized(self, client: httpx.AsyncClient) -> None:
        if await self._refresh_access_token():
            headers = self._get_auth_headers()
            status_active = await self._check_alarm_status(client, headers)
            
            if not status_active:
                await self._activate_alarm(client, headers)
            else:
                self.logger.info("Alarm is already active after token refresh, skipping trigger")
        else:
            self.logger.error("Failed to trigger alarm after refresh attempt")
    
    def close(self) -> None:
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread.is_alive():
            self.thread.join(timeout=5)