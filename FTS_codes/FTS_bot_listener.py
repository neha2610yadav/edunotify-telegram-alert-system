"""Telegram long-polling listener for secure student account linking."""

import sys
import threading

from FTS_database import get_student_link_codes, link_student_telegram, setup_database
from FTS_telegram_api import get_updates, send_bot_reply, verify_bot_token

_listener_thread = None
_stop_event = None


def parse_start_command(text):
    """Return a link code from '/start CODE', or None for an incomplete command."""
    parts = (text or "").strip().split(maxsplit=1)
    if not parts or parts[0].split("@", 1)[0].lower() != "/start":
        return None
    if len(parts) == 1:
        return ""
    return parts[1].strip().upper()


class TelegramLinkListener:
    def __init__(self, stop_event=None):
        self.offset = None
        self.stop_event = stop_event or threading.Event()

    def process_update(self, update):
        """Handle one update once, returning the reply text for testability."""
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        if not chat_id:
            return None

        link_code = parse_start_command(text)
        if link_code is None:
            reply = "Please send /start followed by your faculty-provided linking code."
        elif not link_code:
            reply = "Please use /start <link_code>. Ask your faculty for your Telegram linking code."
        else:
            status, _student_name = link_student_telegram(link_code, chat_id)
            if status == "linked":
                reply = "✅ Your Telegram account has been successfully linked with the Faculty–Student Communication System."
            elif status == "already_linked":
                reply = "✅ This Telegram account is already linked to your student record."
            elif status == "code_already_used":
                reply = "❌ This linking code has already been used. Contact your faculty if you need help."
            else:
                reply = "❌ Invalid linking code. Please check it and try again, or contact your faculty."

        send_bot_reply(chat_id, reply)
        return reply

    def run(self):
        """Poll Telegram until the parent application exits or stop() is called."""
        valid, message = verify_bot_token()
        print(message)
        if not valid and ("not configured" in message or "invalid" in message):
            return

        print("Telegram listener is running. Waiting for /start <link_code> messages...")
        while not self.stop_event.is_set():
            ok, message, updates = get_updates(offset=self.offset, timeout=30)
            if not ok:
                print(message)
                self.stop_event.wait(5)
                continue

            for update in updates:
                update_id = update.get("update_id")
                self.process_update(update)
                if isinstance(update_id, int):
                    self.offset = update_id + 1


def start_telegram_listener():
    """Start one daemon listener while the faculty application is open."""
    global _listener_thread, _stop_event
    if _listener_thread is not None and _listener_thread.is_alive():
        return _listener_thread

    _stop_event = threading.Event()
    listener = TelegramLinkListener(_stop_event)
    _listener_thread = threading.Thread(
        target=listener.run,
        name="TelegramLinkListener",
        daemon=True,
    )
    _listener_thread.start()
    return _listener_thread


def check_pending_updates():
    """Debug helper: check whether Telegram has received any unprocessed updates."""
    ok, message, updates = get_updates(timeout=0)
    if ok:
        return True, f"Telegram getUpdates is working; {len(updates)} pending update(s)."
    return False, message


if __name__ == "__main__":
    setup_database()
    if "--verify" in sys.argv:
        print(verify_bot_token()[1])
        print(check_pending_updates()[1])
    elif "--codes" in sys.argv:
        for student_id, name, link_code in get_student_link_codes():
            print(f"{student_id}: {name} — {link_code}")
    else:
        TelegramLinkListener().run()
