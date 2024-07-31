import logging
import asyncio
import os
import threading
import uuid
import re
import matplotlib.pyplot as plt
from logging.handlers import RotatingFileHandler
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
from src.utils import text, mythreads, research, img3d, lex_dtypes

# _____________________________LOGGING________________________________________

report_logger = logging.getLogger('report_logger')
report_logger.setLevel(logging.INFO)

log_handler = RotatingFileHandler(
    'logs/bot.log',
    maxBytes=5*1024*1024,
    backupCount=3
)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler.setFormatter(formatter)
report_logger.addHandler(log_handler)
logging.basicConfig(level=logging.INFO)

# _____________________________VARIABLES______________________________________

TOKEN_PATH = 'resources/config/token.txt'
FIELDS_PATH = 'resources/config/fields.txt'
SUB_PATH = 'resources/data/subscribers.txt'
DEF_PATH = 'resources/config/definitions.txt'
INFO_PATH = 'resources/config/commands_info.txt'
IMG_DIR = 'resources/img/'
search_data = {}
SEARCH_LIMIT = 25
fields_ = {}
definitions = {}
comm_infos = {}
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
updater_ids_lock = threading.RLock()
executor = ThreadPoolExecutor()
updater = mythreads.ArchiveUpdater()

MAX_SUBPROCESSES = 5
subprocess_queue = lex_dtypes.BlockingQueue(MAX_SUBPROCESSES)

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


async def register_user(chat_id):
    if chat_id not in search_data:
        reset_search(chat_id)
        await asyncio.get_event_loop().run_in_executor(executor, updater.add_id, chat_id)


async def send(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str, parsing: bool) -> None:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg,
        parse_mode='Markdown' if parsing else None
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    msg = (
        '🌌 *Welcome to LEXArchive!* 🚀\n\n'
        f'Hello, {update.effective_chat.effective_name}. '
        'Right here you can easily navigate the NASA\'s \'Planetary Systems\' public database, and I am here '
        'to provide you easy access to it with my functionalities. You can use /help to look at the available commands.\n\n'
        'If you\'re new and you don\'t know what kind of data is being managed, you can use /fields to display all of the '
        'info each record has, also you can make an inline query about these fields if you don\'t know what do they mean.'
    )
    await send(update, context, msg, True)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    msg = (
        "Here are the available commands:\n\n"
        "/start - Welcome message\n"
        "/info <command_name> - Get details about one or more commands and how to use them\n"
        "/count - Count total records in the database\n"
        "/pcount - Count total discovered exoplanets\n"
        "/discin <year> - Count exoplanets discovered in a specific year\n"
        "/search <keyword> - Search for exoplanets by keyword\n"
        "/table <planet_name> - Get detailed table of a specific planet\n"
        "/plot <field> - Plot distribution of a specific field\n"
        "/fields - List all available fields\n"
        "/locate <planet_name> - Get photo pointing where the planet is located and the costellation where it resides\n"
        "/show <name> <option> - Get 3D image representing a celestial body\n"
        "/random - Test your luck\n"
        "/near - Get the nearest planets to earth\n"
        "/far - Get the farthest planets to earth\n"
        "/hab <planet_name> <option> - Get an habitability index of a specific planet.\n"
        "/habzone <star_name> - Get infos about a star\'s habitable zone\n"
        "/shwz <name> - Get the schwarzschild radius for a given star or planet\n"
        "/sub <HH:MM> - Subscribe for daily updates at a specific time\n"
        "/unsub - Unsubscribe from daily updates\n"
        "/report <message> - Submit a message to report any problem using the bot\n"
    )
    await send(update, context, msg, False)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    if len(context.args) == 0:
        await send(update, context, '*Invalid Syntax*: You need to search for one or more commands.', True)

    for comm in context.args:
        if comm in comm_infos:
            await send(update, context, f'*{comm}*' + '\n\n' + comm_infos[comm], True)
        else:
            await send(update, context, f'*Error*: Command \'{comm}\' not found. Check if the name is correct, if so, it means that there are no more infos about it.', True)


# count how many rows are in the database
async def count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
        return

    rows = db.count('ps')
    if rows != -1:
        msg = f'The archive counts *{rows}* records.'
        await send(update, context, msg, True)


# count how many planets were discovered
async def count_pl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
        return

    rows = db.count('pscomppars')
    if rows != -1:
        msg = f'The archive counts *{rows}* different exoplanets discovered.'
        await send(update, context, msg, True)


# count how many planets were discovered in a certain year
async def disc_in(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
        return

    if len(context.args) != 1:
        return

    year = int(context.args[0])
    rows = db.disc_in(year)

    if rows != -1:
        msg = f'The archive counts *{rows}* different exoplanets discovered in {year}.'
        await send(update, context, msg, True)


# returns a list of planet with buttons to iterate it
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
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
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
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
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
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
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
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
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
        return

    string = ''
    for key in fields_:
        string += f'_{fields_[key]}_\n'

    await send(update, context, string, True)


async def locate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
        return

    if len(context.args) == 0:
        return

    planet = ''.join(context.args).lower()
    coord = db.get_coordinates(planet)
    if coord == (None, None):
        return

    buffer = research.fetch_sky_image(coord)
    buffer.seek(0)
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=buffer.read()
    )


async def rand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
        return

    planet = db.get_random_planet()
    keys = (
        fields_['pl_name'],
        fields_['pl_eqt'],
        fields_['pl_insol'],
        fields_['pl_bmasse'],
        fields_['pl_orbper'],
        fields_['pl_orbeccen'],
        fields_['st_teff'],
        fields_['pl_refname']
    )
    data = dict(zip(keys, planet))
    msg = text.planet_spec_format(data)
    await send(update, context, msg, True)


async def distance_endpoint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
        return

    if len(context.args) != 0:
        return

    command_called = update.message.text
    if command_called == '/near':
        top3 = db.get_nearest_planets()
    else:
        top3 = db.get_farthest_planets()

    if top3 is None:
        return

    msg = f'*According to the data, the {'nearest' if command_called == '/near' else 'farthest'} planets are:*\n\n'
    index = 1
    for p in top3:
        msg += f'*{index}.* {p[0]}, ~{p[1]} parsecs distant.\n'
        index += 1

    await send(update, context, msg, True)


# function that returns an image representing the planetary system
async def show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
        return

    if len(context.args) == 0 or ('-s' in context.args and (context.args.index('-s') != len(context.args) - 1 or context.args.count('-s') > 1)):
        return

    is_planet = False if context.args[-1] == '-s' else True
    if not is_planet:
        is_planet = False
        args = context.args[:-1]
    else:
        args = context.args
    name = ''.join(args).lower()

    celestial_body = db.get_celestial_body_info(name) if is_planet else db.get_celestial_body_info(name, is_planet=False)
    if celestial_body is not None:
        await asyncio.get_event_loop().run_in_executor(None, subprocess_queue.put, update.effective_chat.id)
        if is_planet:
            img3d.run_blender_planet_script(update.effective_chat.id, celestial_body)
        else:
            img3d.run_blender_star_script(update.effective_chat.id, celestial_body)
    else:
        return

    await asyncio.get_event_loop().run_in_executor(None, subprocess_queue.get)

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open(f'{IMG_DIR}{update.effective_chat.id}.png', 'rb'),
        caption=f'3d representation for the {'planet' if is_planet else 'star'} \"{name}\".'
    )

    img3d.delete_render_png(update.effective_chat.id)


async def hab(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
        return

    if len(context.args) == 0 or ('-m' in context.args and (context.args.index('-m') != len(context.args) - 1 or context.args.count('-m') > 1)):
        return

    multiple = True if context.args[-1] == '-m' else False
    if multiple:
        args = context.args[:-1]
    else:
        args = context.args

    planet = ''.join(args).lower()
    h_info = db.get_habitability_info(planet, multiple)
    if h_info is None:
        await send(update, context, 'Ops... Nothing found.', False)
        return

    msg = research.calculate_habitability(h_info, multiple)
    if not multiple:
        msg_chunks = [msg[i:i+4096] for i in range(0, len(msg), 4096)]
        for chunk in msg_chunks:
            await send(update, context, chunk, True)
        return

    for m in msg:
        await send(update, context, m, True)


async def hab_zone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
        return

    if len(context.args) == 0:
        await send(update, context, '*Invalid Syntax*: You need to search for a star name.', True)
        return

    name = ' '.join(context.args).lower()
    data = db.get_habitable_zone_data(''.join(context.args).lower())
    if data is None:
        await send(update, context, f'Star \'*{name}*\' not found or data needed to conduct the calculations currently unavailable.', True)
        return

    rad, teff = data
    luminosity = research.calculate_luminosity(rad, teff)
    inner, outer = research.calculate_habitable_zone_edges(luminosity)
    await send(update, context, f'The habitable zone for the star \'*{name}*\' falls approximately between {inner} and {outer}, measured in Astronomical Units.', True)


async def schwarzschild(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
        return

    if len(context.args) == 0:
        await send(update, context, '*Invalid Syntax*: You need to search for a planet or star name.', True)
        return

    name = ' '.join(context.args)
    mass, is_planet = db.mass(''.join(context.args).lower())
    if mass is None:
        if is_planet is None:
            await send(update, context, f'There\'s no planet or star named \'*{name}*\' here.', True)
        else:
            await send(update, context, f'The {'planet' if is_planet else 'star'} \'*{name}*\' was found, but its mass is not available.', True)
        return

    radius = research.calculate_schwarzschild_radius(mass, is_planet)
    await send(update, context, f'The schwarzschild radius for the {'planet' if is_planet else 'star'} \'*{name}*\' is *{radius}* meters.', True)


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    if len(context.args) == 0:
        return

    report_text = ' '.join(context.args)
    report_logger.info(f"Report received from {update.message.from_user.id}: {report_text}")
    msg = 'Thanks for the report, it will help us fix the bot and provide a better experience to all users.'
    await send(update, context, msg, False)


# inline query to retrieve information about database fields meaning
async def inline_query(update: Update, context: CallbackContext) -> None:
    await register_user(update.effective_chat.id)

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
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
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

    msg = 'Your subscription was processed correctly.'
    await send(update, context, msg, False)


# lets user unsubscribe
async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)

    sleeping = await asyncio.get_event_loop().run_in_executor(executor, current_state)
    if not sleeping:
        msg = 'We\'re currently updating the database, all commands are unavailable. We\'ll be back in a moment.'
        await send(update, context, msg, False)
        return

    id = update.effective_chat.id
    subs = await asyncio.get_event_loop().run_in_executor(executor, read_subs)

    orig_len = len(subs)
    filtered = [sub for sub in subs if sub.strip().split('-')[0] != str(id)]

    await asyncio.get_event_loop().run_in_executor(executor, write_subs, filtered)

    msg = 'Your unsubscription was processed correctly.'
    if len(filtered) == orig_len:
        msg = 'You\'re not subscribed.'

    await send(update, context, msg, False)


# stock message for unknown commands
async def unknown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update.effective_chat.id)
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


def _load_infos():
    with open(INFO_PATH, 'r') as file:
        for line in file:
            pair = line.strip().split(':', maxsplit=1)
            comm_infos[pair[0]] = pair[1]


def run() -> None:
    global updater

    _load_fields()
    _load_definitions()
    _load_infos()

    token = _read_token()
    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('info', info))
    application.add_handler(CommandHandler('count', count))
    application.add_handler(CommandHandler('pcount', count_pl))
    application.add_handler(CommandHandler('discin', disc_in))
    application.add_handler(CommandHandler('search', search))
    application.add_handler(CommandHandler('table', table))
    application.add_handler(CommandHandler('plot', plot))
    application.add_handler(CommandHandler('fields', fields))
    application.add_handler(CommandHandler('locate', locate))
    application.add_handler(CommandHandler('random', rand))
    application.add_handler(CommandHandler('near', distance_endpoint))
    application.add_handler(CommandHandler('far', distance_endpoint))
    application.add_handler(CommandHandler('show', show))
    application.add_handler(CommandHandler('hab', hab))
    application.add_handler(CommandHandler('habzone', hab_zone))
    application.add_handler(CommandHandler('shwz', schwarzschild))
    application.add_handler(CommandHandler('report', report))
    application.add_handler(CommandHandler('sub', subscribe))
    application.add_handler(CommandHandler('unsub', unsubscribe))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_cmd))
    application.add_handler(CallbackQueryHandler(button_listener))
    application.add_handler(InlineQueryHandler(inline_query))

    updater.set_bot(application.bot)
    updater.set_ids(list(search_data.keys()))
    updater.set_sleep_lock(state_lock)
    updater.set_ids_lock(updater_ids_lock)
    news_scheduler = mythreads.NewsScheduler(application.bot, subLock, newsLock)
    news_fetcher = mythreads.NewsFetcher(newsLock)
    updater.daemon = True
    news_fetcher.daemon = True
    news_scheduler.daemon = True
    updater.start()
    news_scheduler.start()
    news_fetcher.start()

    application.run_polling()
