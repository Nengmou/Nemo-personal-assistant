"""Wrapper for running Claude Code in a controlled subprocess."""

from nemo.services.code_execution import resolve_working_directory, run_command


def run_claude_code(task: str, working_dir: str | None = None):
    resolved_dir = resolve_working_directory(working_dir)
    command = ["claude", "--print", task]
    return run_command(command, resolved_dir)
