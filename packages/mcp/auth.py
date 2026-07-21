import json
import time
from pathlib import Path

from packages.auth.jwt import decode_token
from packages.auth.repository import get_user_by_id
from packages.auth.service import refresh as refresh_service


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
    except (json.JSONDecodeError, OSError):
        return None


def save_token(data: dict, token_path: str | Path | None = None) -> str:
    path = Path(token_path) if token_path else TOKEN_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return str(path)


def validate_access_token(token_str: str) -> dict:
    payload = decode_token(token_str)
    if payload.get("type") != "access":
        raise PermissionError("Token is not an access token")
    user = get_user_by_id(int(payload["sub"]))
    if not user:
        raise PermissionError("User not found for token")
    return _build_user_dict(user)


def refresh_access_token(refresh_token_str: str, save: bool = True, token_path: str | Path | None = None) -> dict:
    result = refresh_service(refresh_token_str)
    if not result:
        raise PermissionError("Refresh token is invalid or expired")
    expires_at = int(time.time()) + 240 * 60
    token_data = {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "expires_at": expires_at,
    }
    if save:
        save_token(token_data, token_path)
    return token_data


def _token_expires_in(token_data: dict) -> float:
    return token_data.get("expires_at", 0) - time.time()


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
    if _token_expires_in(data) < _REFRESH_MARGIN:
        data = refresh_access_token(data["refresh_token"], save=True, token_path=path)
    return validate_access_token(data["access_token"])


def _build_user_dict(user: dict) -> dict:
    perms = user.get("permissions") or []
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
    }
