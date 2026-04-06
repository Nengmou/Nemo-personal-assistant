import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_paths(paths: list[str]) -> list[str]:
    normalized = []
    for path in paths:
        expanded = os.path.expanduser(path)
        normalized.append(os.path.realpath(expanded))
    return normalized


SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
GOOGLE_CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials/google_credentials.json")
GOOGLE_TOKEN_PATH = os.environ.get("GOOGLE_TOKEN_PATH", "credentials/google_token.json")
GOOGLE_CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
MAX_CONVERSATION_HISTORY = int(os.environ.get("MAX_CONVERSATION_HISTORY", "50"))
MAX_TOOL_ITERATIONS = int(os.environ.get("MAX_TOOL_ITERATIONS", "10"))
DB_PATH = os.environ.get("DB_PATH", "data/nemo.db")

CODE_ALLOWED_USER_IDS = _split_csv(os.environ.get("CODE_ALLOWED_USER_IDS", ""))
CODE_ALLOWED_CHANNEL_IDS = _split_csv(os.environ.get("CODE_ALLOWED_CHANNEL_IDS", ""))
DEFAULT_CODE_WORKDIR = os.path.realpath(
    os.path.expanduser(os.environ.get("DEFAULT_CODE_WORKDIR", BASE_DIR))
)
ALLOWED_CODE_WORKDIR_ROOTS = _normalize_paths(
    _split_csv(os.environ.get("ALLOWED_CODE_WORKDIR_ROOTS", DEFAULT_CODE_WORKDIR))
)
CODE_COMMAND_TIMEOUT_SECONDS = max(1, int(os.environ.get("CODE_COMMAND_TIMEOUT_SECONDS", "300")))
CODE_MAX_OUTPUT_CHARS = max(1000, int(os.environ.get("CODE_MAX_OUTPUT_CHARS", "12000")))
CODE_MAX_CONCURRENT_JOBS = max(1, int(os.environ.get("CODE_MAX_CONCURRENT_JOBS", "2")))
CODE_MAX_QUEUED_JOBS = max(0, int(os.environ.get("CODE_MAX_QUEUED_JOBS", "2")))
CODE_HEARTBEAT_SECONDS = max(5, int(os.environ.get("CODE_HEARTBEAT_SECONDS", "45")))
