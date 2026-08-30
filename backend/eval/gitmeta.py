"""Git provenance for a run: the HEAD commit and working-tree cleanliness.

Shared by both scoring harnesses (extraction and explanation).
"""

import subprocess

from eval._layout import REPO_ROOT


class GitUnavailableError(RuntimeError):
    """``git`` is missing, or this tree is not a git repository."""


def head_commit() -> str:
    """Return the full 40-character SHA of ``HEAD``."""
    return _git("rev-parse", "HEAD")


def is_dirty() -> bool:
    """Return whether ``git status --porcelain`` reports any change."""
    return bool(_git("status", "--porcelain"))


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
    except OSError as exc:  # git binary missing, cwd gone, ...
        raise GitUnavailableError(f"could not run git: {exc}") from exc
    if result.returncode != 0:
        raise GitUnavailableError(
            f"git {' '.join(args)} exited {result.returncode}: {result.stderr.strip()}"
        )
    return result.stdout.strip()
