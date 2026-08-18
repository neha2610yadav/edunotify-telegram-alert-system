"""Backward-compatible Telegram channel sender."""

from FTS_telegram_api import send_to_chat


def send_to_telegram_channel(channel_id, message):
    """Keep legacy calls working while using the shared chat-ID sender."""
    return send_to_chat(channel_id, message)
