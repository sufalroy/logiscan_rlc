import asyncio
import threading
import httpx
import logging


class AlarmClient:
    def __init__(self, alarm_uri, username="admin", password="Admin1234"):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.base_url = alarm_uri.rstrip('/')
        self.username = username
        self.password = password
        
        self.login_url = f"{self.base_url}/login"
        self.alarm_url = f"{self.base_url}/trigger_alarm"
        self.status_url = f"{self.base_url}/alarm_status"
        
        with httpx.Client() as client:
            response = client.post(
                self.login_url,
                auth=(self.username, self.password),
                json={"key": "value"}
            )
            response.raise_for_status()
            self.access_token = response.json().get("access_token")
            if not self.access_token:
                raise ValueError("Failed to obtain access token during initialization.")
        
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def trigger_alarm(self):
        if self.access_token:
            asyncio.run_coroutine_threadsafe(self._trigger_alarm_async(), self.loop)
        else:
           self.logger.error("Cannot trigger alarm: No valid access token available.")

    async def _trigger_alarm_async(self):
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            status_response = await client.get(self.status_url, headers=headers)
            status_data = status_response.json()
            
            if status_data.get("status") != "active":
                await client.post(self.alarm_url, headers=headers)
                self.logger.info("Alarm triggered successfully.")
            else:
                self.logger.error("Alarm is already active, skipping trigger.")