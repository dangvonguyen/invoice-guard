"""Derive API metadata from pyproject.toml."""

import logging
import tomllib
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Return the full path of the project root."""
    return (Path(str(resources.files("app"))) / "..").resolve()


def get_toml_path() -> Path:
    """Return the full path of the pyproject.toml."""
    return get_project_root() / "pyproject.toml"


def get_api_title() -> str:
    """Return the API title from the pyproject.toml file."""
    return cast(str, _project_data()["title"])


def get_api_version() -> str:
    """Return the API version from the pyproject.toml file."""
    return cast(str, _project_data()["version"])


def get_api_description() -> str:
    """Return the API description from the pyproject.toml file."""
    return cast(str, _project_data()["description"])


@lru_cache
def _project_data() -> dict[str, Any]:
    """Return the ``[project]`` data from pyproject.toml."""
    try:
        with get_toml_path().open("rb") as f:
            data: dict[str, Any] = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        logger.exception("Cannot read pyproject.toml; using metadata defaults")
        return {}

    return cast(dict[str, Any], data["project"])
