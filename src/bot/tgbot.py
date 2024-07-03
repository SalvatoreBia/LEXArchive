import logging
import asyncio
import os
import threading
import uuid
import re
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent
)
from telegram.ext import (
    ContextTypes, ApplicationBuilder, CommandHandler, MessageHandler,
    filters, CallbackContext, CallbackQueryHandler, InlineQueryHandler
)
from src.datamanagement.database import DbManager as db
from src.utils import text, mythreads

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# _____________________________VARIABLES______________________________________

TOKEN_PATH = 'config/token.txt'
FIELDS_PATH = 'config/fields.txt'
SUB_PATH = 'data/subscribers.txt'
DEF_PATH = 'config/definitions.txt'
search_data = {}
SEARCH_LIMIT = 25
fields_ = {}
definitions = {}
plot_supported = {
    'emass': 'pl_bmasse',
    'jmass': 'pl_bmassj',
    'erad': 'pl_rade',
    'jrad': 'pl_radj',
    'sgrav': 'st_logg',
    'srad': 'st_rad',
    'smass': 'st_mass'
}

htmlLock = asyncio.Lock()
pngLock = asyncio.Lock()
subLock = threading.RLock()
newsLock = threading.RLock()
state_lock = threading.RLock()
executor = ThreadPoolExecutor()
updater = None

# _____________________________FUNCTIONS______________________________________


def reset_search(id):
    search_data[id] = {
        'start': 0,
        'end': SEARCH_LIMIT,
        'last': None,
        'searched': None
    }


def read_subs() -> list:
    with subLock:
        try:
            with open(SUB_PATH, 'r') as file:
                return file.readlines()
        except IOError as e:
            print(f'Error reading subscription file: {e}')
            return []


def write_subs(subs: list) -> bool:
    with subLock:
        try:
            with open(SUB_PATH, 'w') as file:
                file.writelines(subs)
                return True
        except IOError as e:
            print(f'Error reading subscription file: {e}')
            return False


def current_state() -> bool:
    with state_lock:
        return updater.is_sleeping()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat.id
    updater.add_id(chat)
    await context.bot.send_message(
        chat_id=chat,
        text=f'🌌 *Welcome to LEXArchive!* 🚀\n\nHello, {update.effective_chat.effective_name}. '
             'Right here you can easily navigate the NASA\'s \'Planetary Systems\' public database, and I am here '
             f'to provide you easy access to it with my functionalities. You can consult the /cmds output for all the '
             f'available functionalities.\n\n'
             'If you\'re new and you wish to know more about what the database fields mean, you can make inline queries'
             ' that will help you clear your mind.',
        parse_mode='Markdown'
    )
    reset_search(chat)


# count how many rows are in the database
async def count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id not in search_data:
        reset_search(update.effective_chat.id)
        updater.add_id(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='We\'re currently updating the database, all commands are unavailable. We\'ll be back in a '
                 'moment.'
        )
        return
    rows = db.count()
    if rows != -1:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'The archive counts *{rows}* records.',
            parse_mode='Markdown'
        )


# count how many planets were discovered
async def count_pl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id not in search_data:
        reset_search(update.effective_chat.id)
        updater.add_id(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='We\'re currently updating the database, all commands are unavailable. We\'ll be back in a '
                 'moment.'
        )
        return
    rows = db.count_pl()
    if rows != -1:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'The archive counts *{rows}* different exoplanets discovered.',
            parse_mode='Markdown'
        )


# count how many planets were discovered in a certain year
async def disc_in(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id not in search_data:
        reset_search(update.effective_chat.id)
        updater.add_id(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='We\'re currently updating the database, all commands are unavailable. We\'ll be back in a '
                 'moment.'
        )
        return

    if len(context.args) != 1:
        return

    year = int(context.args[0])
    rows = db.disc_in(year)

    if rows != -1:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'The archive counts *{rows}* different exoplanets discovered in {year}.',
            parse_mode='Markdown'
        )


# returns a list of planet with buttons to iterate it
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id not in search_data:
        reset_search(update.effective_chat.id)
        updater.add_id(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='We\'re currently updating the database, all commands are unavailable. We\'ll be back in a '
                 'moment.'
        )
        return

    keyword = None if len(context.args) == 0 else (''.join(context.args)).lower()
    chat = update.effective_chat.id
    if chat in search_data and search_data[chat]['last'] is not None:
        await context.bot.delete_message(
            chat_id=chat,
            message_id=search_data[chat]['last']
        )
    reset_search(chat)

    st, end = search_data[chat]['start'], search_data[chat]['end']
    rows = db.search_pl(st, end, keyword)
    if rows is None:
        return

    string = ''
    index = st + 1
    for row in rows:
        string += f'{index}.   {row}\n'
        index += 1

    keyboard = [
        [
            InlineKeyboardButton("< Previous Page", callback_data='prev_page_btn'),
            InlineKeyboardButton("Next Page >", callback_data='next_page_btn')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = await context.bot.send_message(
        chat_id=chat,
        text='Available Planets:\n\n' + string if string != '' else 'Ops, there\'s nothing here...',
        reply_markup=reply_markup if string != '' else None
    )
    search_data[chat]['last'] = message.message_id
    search_data[chat]['searched'] = keyword


# button listener for the search command
async def button_listener(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id not in search_data:
        reset_search(update.effective_chat.id)
        updater.add_id(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='We\'re currently updating the database, all commands are unavailable. We\'ll be back in a '
                 'moment.'
        )
        return

    query = update.callback_query

    chat = query.message.chat.id
    keyword = search_data[chat]['searched']
    st, end = search_data[chat]['start'], search_data[chat]['end']
    rows = db.count_like(keyword)

    if query.data == 'next_page_btn' and end < rows:
        st, end = st + SEARCH_LIMIT, min(end + SEARCH_LIMIT, rows)
    elif query.data == 'prev_page_btn' and st > 0:
        st, end = st - SEARCH_LIMIT, st
    else:
        return

    search_data[chat]['start'] = st
    search_data[chat]['end'] = end

    rows = db.search_pl(st, end, keyword)
    if rows is None:
        return

    string = ''
    index = st + 1
    for row in rows:
        string += f'{index}.   {row}\n'
        index += 1

    await query.answer()
    await query.message.edit_text(
        text='Available Planets\n\n' + string,
        reply_markup=query.message.reply_markup
    )


# returns an html table retrieving some records of a specific planet
async def table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id not in search_data:
        reset_search(update.effective_chat.id)
        updater.add_id(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='We\'re currently updating the database, all commands are unavailable. We\'ll be back in a '
                 'moment.'
        )
        return

    if len(context.args) == 0:
        return

    keyword = ''.join(context.args).lower()
    rows, exceeds = db.get_pl_by_name(keyword)

    if rows is None:
        return

    for i in range(len(rows)):
        rows[i] = rows[i][1:-1]

    string = text.htable_format([fields_[key] for key in fields_], rows, exceeds)
    filename = f'table-{keyword}.html'
    async with htmlLock:
        with open(filename, 'w') as file:
            file.write(string)

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=filename
        )
        os.remove(filename)


# plot how a field is distributed
async def plot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id not in search_data:
        reset_search(update.effective_chat.id)
        updater.add_id(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='We\'re currently updating the database, all commands are unavailable. We\'ll be back in a '
                 'moment.'
        )
        return

    arg = '' if len(context.args) != 1 else context.args[0]
    if arg == '' or arg not in plot_supported:
        return

    values = sorted(db.get_field_values(plot_supported[arg]))
    if values is None:
        return

    async with pngLock:
        file = 'plot.png'
        plt.plot(values)
        plt.ylabel(arg)
        plt.savefig(file)
        plt.close()

        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=open(file, 'rb')
        )

        os.remove(file)


# returns the list of fields
async def fields(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id not in search_data:
        reset_search(update.effective_chat.id)
        updater.add_id(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='We\'re currently updating the database, all commands are unavailable. We\'ll be back in a '
                 'moment.'
        )
        return

    string = ''
    for key in fields_:
        string += f'_{fields_[key]}_\n'

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=string,
        parse_mode='Markdown'
    )


# inline query to retrieve information about database fields meaning
async def inline_query(update: Update, context: CallbackContext) -> None:
    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='We\'re currently updating the database, all commands are unavailable. We\'ll be back in a '
                 'moment.'
        )
        return

    query = update.inline_query.query
    if not query:
        return

    matches = [val for val in definitions if query.lower() in val.lower()]

    results = [
        InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=key,
            input_message_content=InputTextMessageContent(definitions[key])
        ) for key in matches
    ]
    await update.inline_query.answer(results)


# lets user subscribe to receive news
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id not in search_data:
        reset_search(update.effective_chat.id)
        updater.add_id(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='We\'re currently updating the database, all commands are unavailable. We\'ll be back in a '
                 'moment.'
        )
        return

    id = update.effective_chat.id
    if len(context.args) != 1:
        return

    time = context.args[0]
    regex = r'^([0-9]{2})\:([0-9]{2})$'
    match = re.match(regex, time)
    if not (match and (0 <= int(match.group(1)) < 24) and (0 <= int(match.group(2)) < 60)):
        await context.bot.send_message(
            chat_id=id,
            text='Specified time doesn\'t match the required format.'
        )
        return

    subs = await asyncio.get_event_loop().run_in_executor(executor, read_subs)

    already_sub = False
    for i in range(len(subs)):
        if subs[i].strip().split('-')[0] == str(id):
            subs[i] = f'{id}-{time}\n'
            already_sub = True
            break

    if not already_sub:
        subs.append(f'{id}-{time}')

    await asyncio.get_event_loop().run_in_executor(executor, write_subs, subs)

    await context.bot.send_message(
        chat_id=id,
        text='Your subscription was processed correctly.'
    )


# lets user unsubscribe
async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id not in search_data:
        reset_search(update.effective_chat.id)
        updater.add_id(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='We\'re currently updating the database, all commands are unavailable. We\'ll be back in a '
                 'moment.'
        )
        return

    id = update.effective_chat.id
    subs = await asyncio.get_event_loop().run_in_executor(executor, read_subs)

    orig_len = len(subs)
    filtered = [sub for sub in subs if sub.strip().split('-')[0] != str(id)]

    await asyncio.get_event_loop().run_in_executor(executor, write_subs, filtered)

    if len(filtered) == orig_len:
        await context.bot.send_message(
            chat_id=id,
            text='You\'re not subscribed.'
        )
    else:
        await context.bot.send_message(
            chat_id=id,
            text='Your unsubscription was processed correctly.'
        )


# stock message for unknown commands
async def unknown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id not in search_data:
        reset_search(update.effective_chat.id)
        updater.add_id(update.effective_chat.id)

    await update.message.reply_text('Command not found.')


def _read_token() -> str:
    with open(TOKEN_PATH, 'r') as file:
        return file.readline().strip()


def _load_fields():
    with open(FIELDS_PATH, 'r') as file:
        for line in file:
            pair = line.strip().split(':')
            fields_[pair[0]] = pair[1]


def _load_definitions():
    with open(DEF_PATH, 'r') as file:
        for line in file:
            pair = line.strip().split(':')
            definitions[pair[0]] = pair[1]


def run() -> None:
    global updater
    token = _read_token()
    _load_fields()
    _load_definitions()
    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', start))
    application.add_handler(CommandHandler('count', count))
    application.add_handler(CommandHandler('pcount', count_pl))
    application.add_handler(CommandHandler('discin', disc_in))
    application.add_handler(CommandHandler('search', search))
    application.add_handler(CommandHandler('table', table))
    application.add_handler(CommandHandler('plot', plot))
    application.add_handler(CommandHandler('fields', fields))
    application.add_handler(CommandHandler('sub', subscribe))
    application.add_handler(CommandHandler('unsub', unsubscribe))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_cmd))
    application.add_handler(CallbackQueryHandler(button_listener))
    application.add_handler(InlineQueryHandler(inline_query))

    updater = mythreads.ArchiveUpdater(application.bot, list(search_data.keys()), state_lock)
    news_scheduler = mythreads.NewsScheduler(application.bot, subLock, newsLock)
    news_fetcher = mythreads.NewsFetcher(newsLock)
    updater.daemon = True
    news_fetcher.daemon = True
    news_scheduler.daemon = True
    updater.start()
    news_scheduler.start()
    news_fetcher.start()
    updater.is_alive()

    application.run_polling()
