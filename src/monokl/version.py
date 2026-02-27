"""Version resolution for Monokl."""

from __future__ import annotations

import re
import shutil
import subprocess
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path

_DESCRIBE_PATTERN = re.compile(
    r"^(?P<tag>.+)-(?P<distance>\d+)-g(?P<commit>[0-9a-f]+)(?P<dirty>-dirty)?$"
)
_HASH_PATTERN = re.compile(r"^g?(?P<commit>[0-9a-f]{7,})(?P<dirty>-dirty)?$")


def _repo_root() -> Path:
    """Return repository root when running from source checkout."""
    return Path(__file__).resolve().parents[2]


def _format_describe_output(describe_output: str) -> str | None:
    """Convert `git describe` output to a PEP 440 compatible version."""
    output = describe_output.strip()
    if not output:
        return None

    describe_match = _DESCRIBE_PATTERN.match(output)
    if describe_match:
        tag = describe_match.group("tag")
        distance = int(describe_match.group("distance"))
        commit = describe_match.group("commit")
        is_dirty = describe_match.group("dirty") is not None

        normalized_tag = tag[1:] if tag.startswith(("v", "V")) else tag
        if distance == 0 and not is_dirty:
            return normalized_tag

        local_parts = [f"g{commit}"]
        if distance > 0:
            local_parts.insert(0, str(distance))
        if is_dirty:
            local_parts.append("dirty")
        return f"{normalized_tag}+{'.'.join(local_parts)}"

    hash_match = _HASH_PATTERN.match(output)
    if hash_match:
        commit = hash_match.group("commit")
        is_dirty = hash_match.group("dirty") is not None
        suffix = f"g{commit}.dirty" if is_dirty else f"g{commit}"
        return f"0.0.0+{suffix}"

    return None


def _version_from_git() -> str | None:
    """Resolve version from git tags and commits."""
    git_executable = shutil.which("git")
    if git_executable is None:
        return None

    try:
        result = subprocess.run(  # noqa: S603 - executable path and args are controlled
            [
                git_executable,
                "-C",
                str(_repo_root()),
                "describe",
                "--tags",
                "--long",
                "--dirty",
                "--always",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return None

    if result.returncode != 0:
        return None

    return _format_describe_output(result.stdout)


@lru_cache(maxsize=1)
def get_version() -> str:
    """Return the Monokl version.

    Priority:
    1. Git-based version from tags/commits (source checkouts).
    2. Installed package metadata version (sdist/wheel installs).
    3. Static fallback.
    """
    git_version = _version_from_git()
    if git_version:
        return git_version

    try:
        return package_version("monokl")
    except PackageNotFoundError:
        return "0.0.0+unknown"
