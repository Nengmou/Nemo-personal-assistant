"""Background job runner and subprocess helpers for Slack-triggered code tasks."""

from __future__ import annotations

import os
import subprocess
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field

from nemo import config


class CodeExecutionError(Exception):
    """Raised when a Slack-triggered code execution request is invalid."""


@dataclass
class ExecutionResult:
    status: str
    stdout: str
    stderr: str
    display_output: str
    exit_code: int | None
    timed_out: bool
    elapsed_seconds: float
    command: list[str]
    working_dir: str
    output_truncated: bool = False


@dataclass
class Job:
    job_id: str
    tool_name: str
    task: str
    channel: str
    thread_ts: str | None
    user_id: str
    requested_workdir: str | None
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None
    result: ExecutionResult | None = None
    future: Future | None = None


def command_execution_enabled() -> bool:
    return bool(config.CODE_ALLOWED_USER_IDS and config.CODE_ALLOWED_CHANNEL_IDS)


def ensure_command_execution_enabled() -> None:
    if command_execution_enabled():
        return
    raise CodeExecutionError(
        "Slack-triggered code execution is disabled. Set CODE_ALLOWED_USER_IDS and "
        "CODE_ALLOWED_CHANNEL_IDS to enable it."
    )


def authorize_request(user_id: str, channel_id: str) -> None:
    ensure_command_execution_enabled()
    if user_id not in config.CODE_ALLOWED_USER_IDS:
        raise CodeExecutionError("You are not allowed to run code commands.")
    if channel_id not in config.CODE_ALLOWED_CHANNEL_IDS:
        raise CodeExecutionError("This channel is not allowed to run code commands.")


def resolve_working_directory(requested_workdir: str | None) -> str:
    candidate = requested_workdir or config.DEFAULT_CODE_WORKDIR
    expanded = os.path.expanduser(candidate)
    resolved = os.path.realpath(expanded)

    allowed = False
    for root in config.ALLOWED_CODE_WORKDIR_ROOTS:
        try:
            common = os.path.commonpath([resolved, root])
        except ValueError:
            continue
        if common == root:
            allowed = True
            break

    if not allowed:
        raise CodeExecutionError(
            f"Working directory is not allowed: {resolved}"
        )
    if not os.path.isdir(resolved):
        raise CodeExecutionError(
            f"Working directory does not exist: {resolved}"
        )
    return resolved


def _truncate_output(text: str) -> tuple[str, bool]:
    if len(text) <= config.CODE_MAX_OUTPUT_CHARS:
        return text, False
    limit = config.CODE_MAX_OUTPUT_CHARS
    suffix = "\n\n[output truncated]"
    return text[: max(0, limit - len(suffix))] + suffix, True


def run_command(command: list[str], working_dir: str) -> ExecutionResult:
    start = time.time()
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "USER": os.environ.get("USER", ""),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "en_US.UTF-8"),
    }

    try:
        completed = subprocess.run(
            command,
            cwd=working_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=config.CODE_COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
        combined = "\n".join(
            part for part in [completed.stdout.strip(), completed.stderr.strip()] if part
        ).strip()
        output, truncated = _truncate_output(combined)
        status = "succeeded" if completed.returncode == 0 else "failed"
        return ExecutionResult(
            status=status,
            stdout=completed.stdout,
            stderr=completed.stderr,
            display_output=output,
            exit_code=completed.returncode,
            timed_out=False,
            elapsed_seconds=time.time() - start,
            command=command,
            working_dir=working_dir,
            output_truncated=truncated,
        )
    except subprocess.TimeoutExpired as exc:
        combined = "\n".join(
            part
            for part in [
                (exc.stdout or "").strip(),
                (exc.stderr or "").strip(),
                f"Command timed out after {config.CODE_COMMAND_TIMEOUT_SECONDS} seconds.",
            ]
            if part
        ).strip()
        output, truncated = _truncate_output(combined)
        return ExecutionResult(
            status="timed_out",
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            display_output=output,
            exit_code=None,
            timed_out=True,
            elapsed_seconds=time.time() - start,
            command=command,
            working_dir=working_dir,
            output_truncated=truncated,
        )
    except FileNotFoundError:
        return ExecutionResult(
            status="failed",
            stdout="",
            stderr=f"Command not found: {command[0]}",
            display_output=f"Command not found: {command[0]}",
            exit_code=None,
            timed_out=False,
            elapsed_seconds=time.time() - start,
            command=command,
            working_dir=working_dir,
            output_truncated=False,
        )


class CodeJobManager:
    """Runs a bounded number of code-execution jobs with minimal state tracking."""

    def __init__(self):
        capacity = max(1, config.CODE_MAX_CONCURRENT_JOBS + config.CODE_MAX_QUEUED_JOBS)
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, config.CODE_MAX_CONCURRENT_JOBS),
            thread_name_prefix="nemo-code-job",
        )
        self._queue_gate = threading.BoundedSemaphore(capacity)
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}

    def submit(
        self,
        *,
        tool_name: str,
        task: str,
        channel: str,
        thread_ts: str | None,
        user_id: str,
        requested_workdir: str | None,
        runner,
    ) -> Job:
        acquired = self._queue_gate.acquire(blocking=False)
        if not acquired:
            raise CodeExecutionError(
                "Too many code jobs are already running. Try again after one finishes."
            )

        job = Job(
            job_id=str(uuid.uuid4())[:8],
            tool_name=tool_name,
            task=task,
            channel=channel,
            thread_ts=thread_ts,
            user_id=user_id,
            requested_workdir=requested_workdir,
        )
        with self._lock:
            self._jobs[job.job_id] = job

        def wrapped_runner() -> ExecutionResult:
            with self._lock:
                job.status = "running"
                job.started_at = time.time()
            try:
                result = runner(task=task, working_dir=requested_workdir)
                with self._lock:
                    job.result = result
                    job.status = result.status
                    job.completed_at = time.time()
                return result
            except Exception as exc:
                with self._lock:
                    job.error = str(exc)
                    job.status = "failed"
                    job.completed_at = time.time()
                raise
            finally:
                self._queue_gate.release()

        future = self._executor.submit(wrapped_runner)
        job.future = future
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def elapsed_seconds(self, job_id: str) -> int:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return 0
            start = job.started_at or job.created_at
        return int(time.time() - start)


job_manager = CodeJobManager()
