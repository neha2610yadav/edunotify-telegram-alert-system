"""Student Telegram notification sender."""

from FTS_telegram_api import send_to_chat


def send_to_student(chat_id, message):
    return send_to_chat(chat_id, message)
