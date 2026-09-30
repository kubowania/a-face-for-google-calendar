# My Calendar, With a Face

A real-time AI avatar that reads your Google Calendar and holds you accountable.
One file: `agent.py`. Made in support for the tutorial [here](https://youtu.be/xQoJA9_1EXA)

## Setup

1. Keys: copy `.env.example` to `.env` and fill in your LiveKit Cloud keys and Synthesia API key.
2. Google: in Google Cloud Console, enable the **Google Calendar API**, add yourself as a test user
   on the OAuth consent screen, create an **OAuth client ID (Desktop app)** and save it here as `credentials.json`.
3. Install:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

## Run

```bash
python agent.py dev
```

The first run opens a browser to log in to Google and saves `token.json`.

Then click the **Agent Console** link the terminal prints (or go to cloud.livekit.io, open your project, Agents, Launch Console) and start talking.
The avatar takes a few seconds to join.
