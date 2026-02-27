"""Keyring utilities for secure token storage.

This module provides functions to store and retrieve API tokens using
the system's keyring/credential manager (Keychain, Secret Service, etc.).

Supported backends (via the 'keyring' package):
- macOS: Keychain Access
- Linux: Secret Service (libsecret) or kwallet
- Windows: Credential Manager
- Fallback: Encrypted file storage
"""

from __future__ import annotations

from monokl import get_logger

logger = get_logger(__name__)

try:
    import keyring
except ImportError:
    logger.warning(
        "keyring package not installed. Install with: uv add keyring",
        install_pkg="keyring",
    )
    keyring = None  # type: ignore[assignment]


# Keyring service name for monokl
SERVICE_NAME = "monokl"


def make_keyring_key(path: str) -> str:
    """Create keyring key from config path.

    Args:
        path: Dot-notation config path (e.g., "adapters.gitlab.api.token")

    Returns:
        Full keyring key (e.g., "monokl:adapters.gitlab.api.token")
    """
    return f"{SERVICE_NAME}:{path}"


def get_username(service: str) -> str:
    """Get username for storing credentials.

    Args:
        service: Service name (e.g., "gitlab", "jira", "todoist")

    Returns:
        Username string for keyring
    """
    return f"{service}-token"


def set_token(service: str, token: str | None, username: str | None = None) -> bool:
    """Store a token in the system keyring.

    Args:
        service: Service name (e.g., "gitlab", "jira", "todoist")
        token: Token string to store (None to delete)
        username: Optional username for keyring (defaults to {service}-token)

    Returns:
        True if successful, False otherwise

    Raises:
        ImportError: If keyring package is not installed
    """
    if keyring is None:
        raise ImportError(
            "keyring package is required for secure token storage. Install it with: uv add keyring"
        )

    if username is None:
        username = get_username(service)

    try:
        if token is None:
            # Delete the token
            try:
                keyring.delete_password(SERVICE_NAME, username)
                logger.info(f"Deleted {service} token from keyring")
                return True
            except keyring.errors.KeyringError:
                # Token doesn't exist, that's fine
                logger.debug(f"No {service} token found in keyring")
                return True
        else:
            keyring.set_password(SERVICE_NAME, username, token)
            logger.info(f"Stored {service} token in keyring")
        return True
    except keyring.errors.KeyringError as e:
        logger.error(f"Failed to access keyring: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error storing {service} token: {e}")
        return False


def get_token(service: str, username: str | None = None) -> str | None:
    """Retrieve a token from the system keyring.

    Args:
        service: Service name (e.g., "gitlab", "jira", "todoist")
        username: Optional username for keyring (defaults to {service}-token)

    Returns:
        Token string if found, None otherwise

    Raises:
        ImportError: If keyring package is not installed
    """
    if keyring is None:
        raise ImportError(
            "keyring package is required for secure token storage. Install it with: uv add keyring"
        )

    if username is None:
        username = get_username(service)

    try:
        token = keyring.get_password(SERVICE_NAME, username)
        if token:
            logger.debug(f"Retrieved {service} token from keyring")
            return token
        logger.debug(f"No {service} token found in keyring")
        return None
    except keyring.errors.KeyringError:
        logger.debug(f"No {service} token found in keyring")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving {service} token: {e}")
        return None


def is_available() -> bool:
    """Check if keyring is available.

    Returns:
        True if keyring package is installed and working, False otherwise
    """
    if keyring is None:
        return False

    try:
        # Try to access keyring to verify it's working
        keyring.get_keyring()
        return True
    except Exception:
        return False


def prompt_and_store_token(service: str, username: str | None = None) -> bool:
    """Prompt user for token and store it in keyring.

    Args:
        service: Service name (e.g., "gitlab", "jira", "todoist")
        username: Optional username for keyring (defaults to {service}-token)

    Returns:
        True if token was stored successfully, False otherwise
    """
    print(f"\n{service.upper()} Token Setup")
    print(f"Enter your {service} API token (or press Enter to skip): ", end="", flush=True)
    token = input().strip()

    if not token:
        print(f"No {service} token provided")
        return False

    if set_token(service, token, username):
        print(f"✓ {service.upper()} token stored securely in keyring")
        return True
    print(f"✗ Failed to store {service} token")
    return False


def get_secret(path: str) -> str | None:
    """Retrieve a secret using config path notation.

    Args:
        path: Dot-notation config path (e.g., "adapters.gitlab.api.token")

    Returns:
        Secret string if found, None otherwise
    """
    keyring_key = make_keyring_key(path)
    try:
        if keyring is None:
            return None
        return keyring.get_password(SERVICE_NAME, keyring_key)
    except Exception:
        return None


def set_secret(path: str, value: str | None) -> bool:
    """Store or delete a secret using config path notation.

    Args:
        path: Dot-notation config path (e.g., "adapters.gitlab.api.token")
        value: Secret value to store, or None to delete

    Returns:
        True if successful, False otherwise
    """
    keyring_key = make_keyring_key(path)
    try:
        if keyring is None:
            return False
        if value is None:
            try:
                keyring.delete_password(SERVICE_NAME, keyring_key)
            except keyring.errors.KeyringError:
                pass
            return True
        keyring.set_password(SERVICE_NAME, keyring_key, value)
        return True
    except Exception as e:
        logger.error(f"Failed to store secret at {path}: {e}")
        return False


def delete_secret(path: str) -> bool:
    """Delete a secret using config path notation.

    Args:
        path: Dot-notation config path (e.g., "adapters.gitlab.api.token")

    Returns:
        True if successful (or didn't exist), False on error
    """
    return set_secret(path, None)
