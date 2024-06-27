import src.bot.tgbot as bot
import src.datamanagement.tap.TapClient as tap
from utils import research
import threading
import time


def update_db():
    while True:
        tap.update()
        time.sleep(86400)


def fetch_news():
    while True:
        research.fetch_news()
        time.sleep(86400)


if __name__ == '__main__':
    updater_thread = threading.Thread(target=update_db)
    news_fetcher_thread = threading.Thread(target=fetch_news)
    updater_thread.daemon = True
    news_fetcher_thread.daemon = True
    updater_thread.start()
    news_fetcher_thread.start()

    bot.run()
