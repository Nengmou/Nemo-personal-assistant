# Nemo - Personal Assistant Slack Bot

Nemo is an AI-powered personal assistant that lives in Slack. It helps manage your work and personal life through natural conversation — handling calendar scheduling, task management, and web research using Claude as its AI backbone.

## Features

- **AI Chat** — Career advice, parenting tips, AI/ML insights, brainstorming. Powered by Claude.
- **Google Calendar** — View upcoming events, create new ones, find free time slots.
- **Task Management** — Create, list, complete, and delete tasks across work/personal/kids categories.
- **Web Search** — Search the internet for current AI news, articles, and information via Tavily.

## Architecture

```
You (Slack DM or @Nemo) → Slack Bolt (Socket Mode) → Claude API (tool_use) → Tools → Response
```

Claude decides which tools to call based on your message. No slash commands needed — just talk naturally.

## Prerequisites

- Python 3.11+
- A Slack workspace where you can create apps
- API keys: Anthropic (Claude), Tavily (web search), Google Cloud (calendar)

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd Nemo-personal-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App** → **From scratch**
2. Name it **Nemo** and select your workspace

**Enable Socket Mode:**
1. Go to **Settings → Socket Mode** → Enable
2. Generate an App-Level Token with `connections:write` scope
3. Save the token — this is your `SLACK_APP_TOKEN` (starts with `xapp-`)

**Set Bot Token Scopes:**
1. Go to **OAuth & Permissions → Scopes → Bot Token Scopes**
2. Add: `app_mentions:read`, `chat:write`, `im:history`, `im:read`, `im:write`

**Enable Events:**
1. Go to **Event Subscriptions** → Enable Events
2. Under **Subscribe to bot events**, add: `app_mention`, `message.im`

**Install the App:**
1. Go to **Install App** → Install to Workspace
2. Copy the **Bot User OAuth Token** — this is your `SLACK_BOT_TOKEN` (starts with `xoxb-`)

### 3. Get API Keys

- **Anthropic**: Get a key at [console.anthropic.com](https://console.anthropic.com/)
- **Tavily**: Get a free key at [tavily.com](https://tavily.com/) (1000 searches/month free)

### 4. Google Calendar (optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the **Google Calendar API**
3. Go to **Credentials → Create Credentials → OAuth 2.0 Client ID**
4. Select **Desktop application** as the type
5. Download the JSON file and save it as `credentials/google_credentials.json`
6. On first bot start, a browser will open for OAuth consent. After authorizing, the token is cached automatically.

### 5. Configure environment

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

### 6. Run

```bash
python run.py
```

Nemo will connect to Slack via Socket Mode. DM the bot or @mention it in a channel to start chatting.

## Usage Examples

| Message | What happens |
|---------|-------------|
| "What's on my calendar today?" | Fetches today's events from Google Calendar |
| "Add a task: review Q1 reports, high priority" | Creates a work task in the database |
| "What are my pending tasks?" | Lists all pending tasks sorted by priority |
| "Complete task 3" | Marks task #3 as done |
| "What are the latest developments in AI agents?" | Searches the web via Tavily |
| "Schedule a parent-teacher conference Thursday at 3pm" | Creates a calendar event |
| "Help me prep for my 1:1 with my director" | Claude gives advice directly (no tools) |

## Project Structure

```
├── run.py                          # Entry point
├── nemo/
│   ├── app.py                      # Slack Bolt app + event handlers
│   ├── agent.py                    # Claude API + tool-use dispatch loop
│   ├── config.py                   # Environment variable loading
│   ├── system_prompt.py            # Nemo's personality and instructions
│   ├── conversation.py             # Per-channel conversation history
│   ├── tools/
│   │   ├── __init__.py             # Tool registry + dispatch
│   │   ├── calendar_tool.py        # Google Calendar tools
│   │   ├── task_tool.py            # Task management tools
│   │   └── web_search.py           # Web search tool
│   ├── db/
│   │   ├── database.py             # SQLite connection + schema
│   │   └── models.py               # Task CRUD operations
│   └── services/
│       ├── calendar_service.py     # Google Calendar API wrapper
│       └── search_service.py       # Tavily API wrapper
├── requirements.txt
├── .env.example
└── .gitignore
```
