import json
import logging
import time
from pathlib import Path
import jwt

from packages.auth.jwt import decode_token
from packages.auth.repository import get_user_by_id
from packages.auth.service import refresh as refresh_service
from modules.core.services.permission_service import derive_permissions

logger = logging.getLogger("mcp.auth")

TOKEN_DIR = Path.home() / ".nova"
TOKEN_FILE = TOKEN_DIR / "mcp-token"
_REFRESH_MARGIN = 300  # refresh if token expires within 5 minutes


def load_token(token_path: str | Path | None = None) -> dict | None:
    path = Path(token_path) if token_path else TOKEN_FILE
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load token from %s: %s", path, e)
        return None


def save_token(data: dict, token_path: str | Path | None = None) -> str:
    path = Path(token_path) if token_path else TOKEN_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return str(path)


def validate_access_token(token_str: str) -> dict:
    try:
        payload = decode_token(token_str)
    except jwt.PyJWTError as e:
        raise PermissionError(f"Invalid or expired access token: {str(e)}") from e

    if payload.get("type") != "access":
        raise PermissionError("Token is not an access token")

    user_id_val = payload.get("sub")
    if not user_id_val:
        raise PermissionError("Token missing subject identifier")

    try:
        user_id = int(user_id_val)
    except (ValueError, TypeError):
        raise PermissionError("Invalid user ID in token")

    user = get_user_by_id(user_id)
    if not user:
        raise PermissionError("User not found for token")
    return _build_user_dict(user)


def refresh_access_token(refresh_token_str: str, save: bool = True, token_path: str | Path | None = None) -> dict:
    """
    Refresh access and refresh token pair using single-use refresh token rotation.
    Persists the rotated tokens (both access_token and rotated refresh_token) to token storage.
    """
    result = refresh_service(refresh_token_str)
    if not result:
        raise PermissionError("Refresh token is invalid or expired")

    expires_at = None
    try:
        payload = decode_token(result["access_token"])
        expires_at = payload.get("exp")
    except Exception:
        pass

    if not expires_at:
        expires_at = int(time.time()) + 240 * 60

    token_data = {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "expires_at": int(expires_at),
    }
    if save:
        save_token(token_data, token_path)
    return token_data


def _token_expires_in(token_data: dict) -> float:
    if "expires_at" in token_data and token_data["expires_at"]:
        return float(token_data["expires_at"]) - time.time()
    if "access_token" in token_data:
        try:
            payload = decode_token(token_data["access_token"], options={"verify_exp": False})
            exp = payload.get("exp")
            if exp:
                return float(exp) - time.time()
        except Exception:
            pass
    return 0.0


def get_valid_user(token_str_or_path: str | None = None) -> dict:
    """Resolve a token to a validated user dict.

    Resolution order:
      1. If token_str_or_path looks like a JWT (starts with eyJ), use it directly
      2. If token_str_or_path is a file path, load from file
      3. Otherwise, load from default ~/.nova/mcp-token
    Auto-refreshes if token is within 5 minutes of expiry.
    """
    if token_str_or_path and token_str_or_path.startswith("eyJ"):
        return validate_access_token(token_str_or_path)
    path = token_str_or_path if token_str_or_path else None
    data = load_token(path)
    if not data:
        raise PermissionError("No token found. Run 'python scripts/mcp-login.py' first.")

    # Auto-refresh if approaching expiration
    if _token_expires_in(data) < _REFRESH_MARGIN and data.get("refresh_token"):
        data = refresh_access_token(data["refresh_token"], save=True, token_path=path)

    try:
        return validate_access_token(data["access_token"])
    except PermissionError:
        # If access token has expired or is invalid, attempt auto-refresh using refresh_token if available
        if data.get("refresh_token"):
            data = refresh_access_token(data["refresh_token"], save=True, token_path=path)
            return validate_access_token(data["access_token"])
        raise


def _build_user_dict(user: dict) -> dict:
    raw_perms = user.get("permissions")
    if raw_perms is None or (isinstance(raw_perms, (list, tuple)) and len(raw_perms) == 0):
        role = user.get("role", "")
        perms = derive_permissions(role)
    elif isinstance(raw_perms, list):
        perms = list(raw_perms)
    elif isinstance(raw_perms, str):
        perms = [raw_perms]
    else:
        perms = list(raw_perms)

    if user.get("role") == "Admin" and "*" not in perms:
        perms = ["*"]
    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "role": user.get("role"),
        "permissions": perms,
        "business_id": user.get("business_id"),
        "customer_id": user.get("customer_id"),
    }
