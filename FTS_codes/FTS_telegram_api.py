"""Small Telegram Bot API client shared by sending and incoming updates."""

import requests

from FTS_config import get_config_value, get_telegram_bot_token

API_ROOT = "https://api.telegram.org"


def build_telegram_deep_link(link_code):
    """Build a safe student link containing only the opaque linking code."""
    username = get_config_value("TELEGRAM_BOT_USERNAME").lstrip("@").strip()
    code = (link_code or "").strip()
    if not username or not code:
        return None
    return f"https://t.me/{username}?start={code}"


def _api_url(method):
    token = get_telegram_bot_token()
    if not token:
        return None
    return f"{API_ROOT}/bot{token}/{method}"


def _response_message(response):
    try:
        data = response.json()
    except ValueError:
        data = {}
    return data.get("description", "Telegram returned an unexpected response")


def send_to_chat(chat_id, message):
    """Send a message and return a dashboard-friendly result string."""
    if not chat_id:
        return "Failed: Student has not linked Telegram yet"

    url = _api_url("sendMessage")
    if not url:
        return "Failed: TELEGRAM_BOT_TOKEN is not configured"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": str(chat_id),
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
    except requests.exceptions.Timeout:
        return "Failed: Telegram request timed out"
    except requests.exceptions.RequestException:
        return "Failed: Telegram API is unavailable or the network is offline"

    if response.status_code == 200:
        try:
            if response.json().get("ok"):
                return "Sent via Telegram"
        except ValueError:
            pass

    description = _response_message(response)
    if response.status_code == 400:
        return f"Failed: Telegram rejected the message (400: {description})"
    if response.status_code == 401:
        return "Failed: Telegram bot token is invalid (401)"
    if response.status_code == 403:
        return "Failed: Student blocked the bot or cannot be messaged (403)"
    return f"Failed: Telegram API error ({response.status_code}: {description})"


def send_bot_reply(chat_id, message):
    """Send a listener reply; failures are returned for console diagnostics."""
    return send_to_chat(chat_id, message)


def verify_bot_token():
    """Call getMe and return a clear result for the listener debug command."""
    url = _api_url("getMe")
    if not url:
        return False, "TELEGRAM_BOT_TOKEN is not configured"

    try:
        response = requests.get(url, timeout=15)
    except requests.exceptions.Timeout:
        return False, "Telegram getMe request timed out"
    except requests.exceptions.RequestException:
        return False, "Telegram API is unavailable or the network is offline"

    if response.status_code == 200:
        try:
            data = response.json()
        except ValueError:
            data = {}
        if data.get("ok"):
            username = data.get("result", {}).get("username", "unknown")
            return True, f"Telegram bot token is valid (@{username})"

    if response.status_code == 401:
        return False, "Telegram bot token is invalid (401)"
    return False, f"Telegram getMe failed ({response.status_code}: {_response_message(response)})"


def get_updates(offset=None, timeout=30):
    """Retrieve Telegram updates. The caller persists the offset during its run."""
    url = _api_url("getUpdates")
    if not url:
        return False, "TELEGRAM_BOT_TOKEN is not configured", []

    params = {"timeout": timeout, "allowed_updates": '["message"]'}
    if offset is not None:
        params["offset"] = offset

    try:
        response = requests.get(url, params=params, timeout=timeout + 10)
    except requests.exceptions.Timeout:
        return False, "Telegram getUpdates request timed out", []
    except requests.exceptions.RequestException:
        return False, "Telegram API is unavailable or the network is offline", []

    if response.status_code != 200:
        if response.status_code == 401:
            return False, "Telegram bot token is invalid (401)", []
        if response.status_code == 409:
            return False, "Another Telegram listener is already using this bot (409)", []
        return False, f"Telegram getUpdates failed ({response.status_code}: {_response_message(response)})", []

    try:
        data = response.json()
    except ValueError:
        return False, "Telegram returned invalid JSON for getUpdates", []
    if not data.get("ok"):
        return False, data.get("description", "Telegram getUpdates failed"), []
    return True, "Updates retrieved", data.get("result", [])
