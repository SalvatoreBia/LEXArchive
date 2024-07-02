import threading
import time
import asyncio
import os
from datetime import datetime


class NewsScheduler(threading.Thread):
    _FILE = 'data/subscribers.txt'

    def __init__(self, bot, lock: threading.RLock):
        super().__init__(daemon=True)
        self._lock = lock
        self._bot = bot
        self._subs = {}
        self._last_mtime = 0
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def _read(self):
        try:
            with self._lock:
                current_mtime = os.path.getmtime(self._FILE)
                if current_mtime != self._last_mtime:
                    with open(self._FILE, 'r') as file:
                        self._subs = {line.strip().split('-')[0]: line.strip().split('-')[1] for line in file}
                    self._last_mtime = current_mtime
        except IOError as e:
            print(f'Error trying to open subscribers file: {e}')

    def run(self):
        while True:
            self._read()
            current_time = datetime.now().strftime('%H:%M')
            to_notify = [chat_id for chat_id in self._subs if self._subs[chat_id] == current_time]

            for user in to_notify:
                self.loop.call_soon_threadsafe(asyncio.create_task, self._bot.send_message(
                    chat_id=user,
                    text='notificus'
                ))
            time.sleep(60)
