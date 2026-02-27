"""Feature flags for monocle.

Provides decorators to mark commands as requiring specific feature flags.

Usage:
    from monocle.features import experimental, feature_flag

    @app.command()
    @experimental
    def my_experimental_cmd():
        '''[experimental] An experimental feature.'''
        ...

    @app.command()
    @feature_flag("beta")
    def my_beta_cmd():
        '''[beta] A beta feature.'''
        ...

Configuration:
    YAML:
        features:
          experimental: true

    Environment:
        MONOCLE_FEATURE_EXPERIMENTAL=true
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import ParamSpec
from typing import TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

P = ParamSpec("P")
T = TypeVar("T")

FEATURE_FLAG_ATTR = "__monocle_feature_flag__"


def experimental(func: Callable[P, T]) -> Callable[P, T]:
    """Mark a command as requiring the experimental feature flag."""
    setattr(func, FEATURE_FLAG_ATTR, "experimental")
    return func


def feature_flag(name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Mark a command as requiring a specific feature flag.

    Args:
        name: The feature flag name (e.g., "experimental", "beta")
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        setattr(func, FEATURE_FLAG_ATTR, name)
        return func

    return decorator


def get_feature_flag(func: Callable[..., Any]) -> str | None:
    """Get the feature flag required by a function, if any.

    Args:
        func: The function to check

    Returns:
        The feature flag name, or None if no flag is set
    """
    return getattr(func, FEATURE_FLAG_ATTR, None)


def is_feature_enabled(flag: str) -> bool:
    """Check if a feature flag is enabled.

    Args:
        flag: The feature flag name

    Returns:
        True if the flag is enabled, False otherwise
    """
    from monocle.config import get_config

    config = get_config()
    if flag == "experimental":
        return config.experimental_features
    return False
