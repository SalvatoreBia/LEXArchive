import logging
import asyncio
import os
import matplotlib.pyplot as plt
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, \
    CallbackQueryHandler
from src.datamanagement.database import DbManager as db
from src.utils import text, research

TOKEN_PATH = 'config/token.txt'
FIELDS_PATH = 'config/fields.txt'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

search_data = {}
SEARCH_LIMIT = 25
fields = {}

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


def reset_search(id):
    search_data[id] = {
        'start': 0,
        'end': SEARCH_LIMIT,
        'last': None,
        'searched': None
    }


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat.id
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


async def count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = db.count()
    if rows != -1:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'The archive counts *{rows}* records.',
            parse_mode='Markdown'
        )


async def count_pl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = db.count_pl()
    if rows != -1:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'The archive counts *{rows}* different exoplanets discovered.',
            parse_mode='Markdown'
        )


async def disc_in(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def button_listener(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    chat = query.message.chat.id
    keyword = search_data[chat]['searched']
    st, end = search_data[chat]['start'], search_data[chat]['end']
    rows = db.count_like(keyword)
    print(rows)

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


async def table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        return

    keyword = ''.join(context.args).lower()
    rows = db.get_pl_by_name(keyword)
    if rows is None:
        return

    for i in range(len(rows)):
        rows[i] = rows[i][1:-1]

    string = text.htable_format([fields[key] for key in fields], rows)
    filename = f'table-{keyword}.html'
    async with htmlLock:
        with open(filename, 'w') as file:
            file.write(string)

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=filename
        )
        os.remove(filename)


async def plot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    link = research.get_rand_news()
    if link is None:
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'{link}'
    )


async def unknown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Command not found.')


def _read_token() -> str:
    with open(TOKEN_PATH, 'r') as file:
        return file.readline().strip()


def _load_fields():
    with open(FIELDS_PATH, 'r') as file:
        for line in file:
            pair = line.strip().split(':')
            fields[pair[0]] = pair[1]


def run() -> None:
    token = _read_token()
    _load_fields()
    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', start))
    application.add_handler(CommandHandler('count', count))
    application.add_handler(CommandHandler('pcount', count_pl))
    application.add_handler(CommandHandler('discin', disc_in))
    application.add_handler(CommandHandler('search', search))
    application.add_handler(CommandHandler('table', table))
    application.add_handler(CommandHandler('plot', plot))
    application.add_handler(CommandHandler('news', news))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_cmd))
    application.add_handler(CallbackQueryHandler(button_listener))
    application.run_polling()
