import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli, function_tool
from livekit.plugins import silero, synthesia
load_dotenv()

if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json")
else:
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", ["https://www.googleapis.com/auth/calendar.events"])
    creds = flow.run_local_server(port=0)
    open("token.json", "w").write(creds.to_json())

calendar = build("calendar", "v3", credentials=creds)

def get_events():
    """Fetch calendar events from 3 hours ago until 12 hours from now."""
    now = datetime.now().astimezone()

    events = calendar.events().list(
        calendarId="primary",  # "primary" means your main Google Calendar
        timeMin=(now - timedelta(hours=3)).isoformat(),  # start looking 3 hours ago
        timeMax=(now + timedelta(hours=12)).isoformat(),  # stop looking 12 hours from now
        singleEvents=True,  # show each repeat of a recurring event separately
        orderBy="startTime",  # earliest first
    ).execute()["items"]  # .execute() actually sends the request; "items" is the list of events

    return [{"id": e["id"], "title": e.get("summary"), "start": e["start"], "end": e["end"]} for e in events]



class CalendarAvatar(Agent):
    def __init__(self):
        super().__init__(instructions="""
            You are the user's calendar, given a face. Your job is to hold them accountable.
            You are speaking out loud, so keep replies to one or two short sentences.
            Be dry and deadpan. If they are late for something, say exactly how late.
            Check the calendar before answering questions about it.
    """)

    @function_tool
    async def get_schedule(self) -> str:
        """Get the current time and today's calendar events."""
        return f"The time is {datetime.now():%H:%M}. Events: {get_events()}"

    @function_tool
    async def reschedule_event(self, event_id: str, new_start: str) -> str:
        """Move an event to a new start time. new_start is ISO format, e.g. 2026-09-29T15:30:00."""
        event = calendar.events().get(calendarId="primary", eventId=event_id).execute()
        length = datetime.fromisoformat(event["end"]["dateTime"]) - datetime.fromisoformat(event["start"]["dateTime"])
        start = datetime.fromisoformat(new_start).astimezone()
        event["start"]["dateTime"] = start.isoformat()
        event["end"]["dateTime"] = (start + length).isoformat()
        calendar.events().update(calendarId="primary", eventId=event_id, body=event).execute()
        return "Done."


async def send_reminders(session: AgentSession):
    reminded = set()
    while True:
        await asyncio.sleep(30)
        for event in get_events():
            start = datetime.fromisoformat(event["start"].get("dateTime", event["start"].get("date")))
            minutes_left = (start.astimezone() - datetime.now().astimezone()).total_seconds() / 60
            if 0 < minutes_left <= 5 and event["id"] not in reminded:
                reminded.add(event["id"])
                session.generate_reply(instructions=f"Remind the user that '{event['title']}' starts in {round(minutes_left)} minutes.")


server = AgentServer()
@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt="cartesia/ink-2",  # Speech To Text
        llm="openai/gpt-4.1-mini",  # Large Language Model
        tts="cartesia/sonic-3",  # Text To Speech
        vad=silero.VAD.load(),  # Voice Activity Detection
    )
    avatar = synthesia.AvatarSession(synthesia.AvatarConfig(avatar_ids=["4728db18-0091-42ea-87c4-ef2d6f3a9af7"]))
    await avatar.start(session, room=ctx.room)
    await session.start(agent=CalendarAvatar(), room=ctx.room)
    session.generate_reply(instructions="Check the calendar, then open by telling the user the time and anything they are late for.")
    asyncio.create_task(send_reminders(session))

if __name__ == "__main__":
    cli.run_app(server)
