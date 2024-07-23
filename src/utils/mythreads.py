import threading
import time
import asyncio
import os
from datetime import datetime
from src.utils import research, lex_dtypes, img3d
from src.datamanagement.tap import TapClient

LOOP = asyncio.get_event_loop()


class NewsScheduler(threading.Thread):
    _FILE = 'resources/data/subscribers.txt'

    def __init__(self, bot, sub_lock: threading.RLock, news_lock: threading.RLock):
        super().__init__()
        self._sub_lock = sub_lock
        self._news_lock = news_lock
        self._bot = bot
        self._subs = {}
        self._last_mtime = 0

    def _read(self):
        try:
            with self._sub_lock:
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
            if len(to_notify) > 0:
                with self._news_lock:
                    link = research.get_rand_news()
            for user in to_notify:
                LOOP.call_soon_threadsafe(asyncio.create_task, self._bot.send_message(
                    chat_id=user,
                    text=link
                ))
            time.sleep(60)


class NewsFetcher(threading.Thread):
    _FILE = 'resources/data/news.txt'

    def __init__(self, lock: threading.RLock):
        super().__init__()
        self._lock = lock

    def run(self):
        while True:
            news = research.fetch_news()
            if news != '':
                with self._lock:
                    try:
                        with open(NewsFetcher._FILE, 'w') as file:
                            file.write(news)
                    except IOError as e:
                        print(f'Error trying to open news file: {e}')
            time.sleep(86400)


class ArchiveUpdater(threading.Thread):

    def __init__(self, bot=None, ids=None , lock=None):
        super().__init__()
        self._bot = bot
        self._ids = ids
        self._sleeping = False
        self._sleep_lock = lock

    def set_bot(self, bot):
        self._bot = bot

    def set_ids(self, ids):
        self._ids = ids

    def set_lock(self, lock):
        self._sleep_lock = lock

    def add_id(self, id: int):
        self._ids.append(id)

    def is_sleeping(self):
        with self._sleep_lock:
            return self._sleeping

    def _set_sleeping(self, b: bool):
        with self._sleep_lock:
            self._sleeping = b

    # TODO la lettura degli id non penso sia thread-safe
    def run(self):
        TapClient.load_fields()
        while True:
            for chat_id in self._ids:
                LOOP.call_soon_threadsafe(asyncio.create_task, self._bot.send_message(
                    chat_id=chat_id,
                    text='We\'re currently updating the database, all commands are unavailable. We\'ll be back in a '
                         'moment.'
                ))
            TapClient.update()
            for chat_id in self._ids:
                LOOP.call_soon_threadsafe(asyncio.create_task, self._bot.send_message(
                    chat_id=chat_id,
                    text='We\'ve updated the database, all commands are now available.'
                ))

            self._set_sleeping(True)
            time.sleep(86400)
            self._set_sleeping(False)


class Img3dSubprocessExecutor(threading.Thread):

    def __init__(self, limit):
        super().__init__()
        self.limit = limit
        self.queue = lex_dtypes.BlockingQueue(self.limit)

    def run(self):
        while True:
            call = self.queue.get()
            img3d.run_blender_script(call)
