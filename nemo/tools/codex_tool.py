"""Wrapper for running the Codex CLI in a controlled subprocess."""

from nemo.services.code_execution import resolve_working_directory, run_command


def run_codex(task: str, working_dir: str | None = None):
    resolved_dir = resolve_working_directory(working_dir)
    command = ["codex", "--approval-mode", "full-auto", "-q", task]
    return run_command(command, resolved_dir)
