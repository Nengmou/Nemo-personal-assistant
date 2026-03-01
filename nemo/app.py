import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from nemo import config
from nemo.agent import process_message
from nemo.conversation import add_user_message, get_history, add_assistant_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App(token=config.SLACK_BOT_TOKEN)

BOT_USER_ID = None


@app.event("app_mention")
def handle_mention(event, say, client):
    """Handle @Nemo mentions in channels."""
    global BOT_USER_ID
    if BOT_USER_ID is None:
        BOT_USER_ID = client.auth_test()["user_id"]

    channel = event["channel"]
    text = event.get("text", "")
    text = text.replace(f"<@{BOT_USER_ID}>", "").strip()
    thread_ts = event.get("thread_ts", event.get("ts"))

    if not text:
        say("Hey! How can I help?", thread_ts=thread_ts)
        return

    _handle(channel, text, say, thread_ts=thread_ts)


@app.event("message")
def handle_dm(event, say, client):
    """Handle direct messages."""
    global BOT_USER_ID
    if BOT_USER_ID is None:
        BOT_USER_ID = client.auth_test()["user_id"]

    if event.get("channel_type") != "im":
        return
    if event.get("bot_id") or event.get("subtype"):
        return
    if event.get("user") == BOT_USER_ID:
        return

    channel = event["channel"]
    text = event.get("text", "")

    if not text:
        return

    _handle(channel, text, say)


def _handle(channel: str, text: str, say, thread_ts: str = None):
    """Common handler: send to Claude agent, post response."""
    try:
        add_user_message(channel, text)
        history = get_history(channel)
        response_text = process_message(history)
        add_assistant_message(channel, response_text)
        if thread_ts:
            say(response_text, thread_ts=thread_ts)
        else:
            say(response_text)
    except Exception as e:
        logger.exception("Error processing message")
        error_msg = f"Sorry, I hit an error: {e}"
        if thread_ts:
            say(error_msg, thread_ts=thread_ts)
        else:
            say(error_msg)


def start():
    """Start the bot in Socket Mode."""
    from nemo.db.database import init_db

    init_db()
    handler = SocketModeHandler(app, config.SLACK_APP_TOKEN)
    logger.info("⚡ Nemo is starting up...")
    handler.start()
