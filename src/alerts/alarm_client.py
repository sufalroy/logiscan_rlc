import httpx
import logging
from typing import Dict, Tuple, Optional


class AlarmClient:
    def __init__(self, alarm_uri: str, username: str = "admin", password: str = "adminpass"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_url = alarm_uri.rstrip('/')
        self.auth = (username, password)
        
        self.urls = {
            "login": f"{self.base_url}/login",
            "alarm": f"{self.base_url}/trigger_alarm",
            "status": f"{self.base_url}/alarm_status"
        }
    
    async def _get_access_token(self) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.urls["login"],
                    auth=self.auth,
                    json={"key": "value"}
                )
                response.raise_for_status()
                return response.json().get("access_token")
        except httpx.HTTPError as e:
            self.logger.error(f"Login failed: {e}")
            return None
    
    def _get_auth_headers(self, token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def _check_alarm_status(self, token: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = self._get_auth_headers(token)
                response = await client.get(self.urls["status"], headers=headers)
                response.raise_for_status()
                return response.json().get("status") == "active"
        except httpx.HTTPError as e:
            self.logger.error(f"Failed to check alarm status: {e}")
            return False
    
    async def _activate_alarm(self, token: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = self._get_auth_headers(token)
                response = await client.post(self.urls["alarm"], headers=headers)
                response.raise_for_status()
                self.logger.info("Alarm triggered successfully")
                return True
        except httpx.HTTPError as e:
            self.logger.error(f"Failed to trigger alarm: {e}")
            return False
    
    async def trigger_alarm(self) -> bool:
        token = await self._get_access_token()
        if not token:
            self.logger.error("Cannot trigger alarm: Failed to obtain access token")
            return False
        
        is_active = await self._check_alarm_status(token)
        if is_active:
            self.logger.info("Alarm is already active, skipping trigger")
            return True
        
        return await self._activate_alarm(token)