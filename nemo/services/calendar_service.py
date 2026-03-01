"""Google Calendar API service."""

import os
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from nemo import config

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    def __init__(self):
        self.creds = self._authenticate()
        self.service = build("calendar", "v3", credentials=self.creds)
        self.calendar_id = config.GOOGLE_CALENDAR_ID

    def _authenticate(self) -> Credentials:
        """OAuth2 flow with token caching."""
        creds = None
        token_path = config.GOOGLE_TOKEN_PATH
        creds_path = config.GOOGLE_CREDENTIALS_PATH

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, "w") as f:
                f.write(creds.to_json())

        return creds

    def get_events(self, time_min: str = None, time_max: str = None,
                   max_results: int = 10) -> list[dict]:
        """Fetch events from Google Calendar."""
        now = datetime.utcnow()
        if time_min is None:
            time_min = now.isoformat() + "Z"
        if time_max is None:
            time_max = (now + timedelta(days=7)).isoformat() + "Z"

        result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for item in result.get("items", []):
            events.append({
                "id": item["id"],
                "summary": item.get("summary", "(No title)"),
                "start": item["start"].get("dateTime", item["start"].get("date")),
                "end": item["end"].get("dateTime", item["end"].get("date")),
                "location": item.get("location", ""),
                "description": item.get("description", ""),
            })
        return events

    def create_event(self, summary: str, start_time: str, end_time: str,
                     description: str = None, location: str = None) -> dict:
        """Create a new calendar event."""
        event_body = {
            "summary": summary,
            "start": {"dateTime": start_time, "timeZone": "America/Los_Angeles"},
            "end": {"dateTime": end_time, "timeZone": "America/Los_Angeles"},
        }
        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location

        event = self.service.events().insert(
            calendarId=self.calendar_id,
            body=event_body,
        ).execute()

        return {
            "id": event["id"],
            "summary": event.get("summary"),
            "start": event["start"].get("dateTime"),
            "htmlLink": event.get("htmlLink"),
        }

    def find_free_time(self, date: str, duration_minutes: int = 30,
                       work_hours_only: bool = True) -> list[dict]:
        """Find free time slots on a given date."""
        day_start = f"{date}T09:00:00" if work_hours_only else f"{date}T00:00:00"
        day_end = f"{date}T17:00:00" if work_hours_only else f"{date}T23:59:00"

        body = {
            "timeMin": f"{day_start}-08:00",
            "timeMax": f"{day_end}-08:00",
            "timeZone": "America/Los_Angeles",
            "items": [{"id": self.calendar_id}],
        }
        result = self.service.freebusy().query(body=body).execute()
        busy_periods = result["calendars"][self.calendar_id]["busy"]

        slots = []
        current = datetime.fromisoformat(day_start)
        end_of_day = datetime.fromisoformat(day_end)

        for busy in busy_periods:
            busy_start_str = busy["start"].replace("Z", "+00:00")
            busy_start = datetime.fromisoformat(busy_start_str).replace(tzinfo=None)
            if (busy_start - current).total_seconds() >= duration_minutes * 60:
                slots.append({
                    "start": current.strftime("%I:%M %p"),
                    "end": busy_start.strftime("%I:%M %p"),
                })
            busy_end_str = busy["end"].replace("Z", "+00:00")
            current = datetime.fromisoformat(busy_end_str).replace(tzinfo=None)

        if (end_of_day - current).total_seconds() >= duration_minutes * 60:
            slots.append({
                "start": current.strftime("%I:%M %p"),
                "end": end_of_day.strftime("%I:%M %p"),
            })

        return slots
