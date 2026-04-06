import logging
from concurrent.futures import TimeoutError as FutureTimeoutError
from threading import Thread

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from nemo import config
from nemo.agent import process_message
from nemo.conversation import add_user_message, get_history, add_assistant_message
from nemo.services.code_execution import (
    CodeExecutionError,
    authorize_request,
    job_manager,
)
from nemo.tools.claude_code_tool import run_claude_code
from nemo.tools.codex_tool import run_codex

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

    _handle(channel, text, say, user_id=event["user"], thread_ts=thread_ts)


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

    _handle(channel, text, say, user_id=event["user"], thread_ts=event.get("ts"))


def _parse_code_command(text: str) -> tuple[str, str, str] | None:
    stripped = text.strip()
    lowered = stripped.lower()
    if lowered.startswith("code:"):
        task = stripped[5:].strip()
        return ("Claude Code", "code", task)
    if lowered.startswith("codex:"):
        task = stripped[6:].strip()
        return ("Codex", "codex", task)
    return None


def _post_thread_reply(channel: str, text: str, thread_ts: str | None):
    app.client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)


def _format_execution_result(tool_name: str, result) -> str:
    lines = [
        f"{tool_name} job finished with status `{result.status}`.",
        f"Working directory: `{result.working_dir}`",
    ]
    if result.exit_code is not None:
        lines.append(f"Exit code: `{result.exit_code}`")
    lines.append(f"Elapsed: `{result.elapsed_seconds:.1f}s`")

    output = result.display_output.strip()
    if output:
        lines.append("")
        lines.append("```")
        lines.append(output)
        lines.append("```")
    if result.output_truncated:
        lines.append("")
        lines.append("Output was truncated to fit Slack.")
    return "\n".join(lines)


def _watch_code_job(job, tool_name: str):
    future = job.future
    if future is None:
        return

    while True:
        try:
            result = future.result(timeout=config.CODE_HEARTBEAT_SECONDS)
            _post_thread_reply(
                job.channel,
                _format_execution_result(tool_name, result),
                job.thread_ts,
            )
            return
        except FutureTimeoutError:
            elapsed = job_manager.elapsed_seconds(job.job_id)
            _post_thread_reply(
                job.channel,
                f"{tool_name} job `{job.job_id}` is still running. Elapsed: `{elapsed}s`.",
                job.thread_ts,
            )
        except Exception as exc:
            logger.exception("Code job %s failed", job.job_id)
            _post_thread_reply(
                job.channel,
                f"{tool_name} job `{job.job_id}` failed: {exc}",
                job.thread_ts,
            )
            return


def _submit_code_job(channel: str, text: str, say, user_id: str, thread_ts: str | None):
    parsed = _parse_code_command(text)
    if parsed is None:
        return False

    tool_name, command_name, task = parsed
    if not task:
        say(f"Usage: `{command_name}: <task>`", thread_ts=thread_ts)
        return True

    runner = run_claude_code if tool_name == "Claude Code" else run_codex

    try:
        authorize_request(user_id, channel)
        job = job_manager.submit(
            tool_name=tool_name,
            task=task,
            channel=channel,
            thread_ts=thread_ts,
            user_id=user_id,
            requested_workdir=None,
            runner=runner,
        )
    except CodeExecutionError as exc:
        say(str(exc), thread_ts=thread_ts)
        return True

    say(
        f"Accepted {tool_name} job `{job.job_id}` in `{config.DEFAULT_CODE_WORKDIR}`. "
        "I'll post progress updates in this thread.",
        thread_ts=thread_ts,
    )
    watcher = Thread(
        target=_watch_code_job,
        args=(job, tool_name),
        name=f"nemo-{tool_name.lower().replace(' ', '-')}-watcher",
        daemon=True,
    )
    watcher.start()
    return True


def _handle(channel: str, text: str, say, user_id: str, thread_ts: str = None):
    """Common handler: send to Claude agent, post response."""
    try:
        if _submit_code_job(channel, text, say, user_id, thread_ts):
            return

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
