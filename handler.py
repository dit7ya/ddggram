import json
import logging
import os

import ddgr

from uuid import uuid4
from telegram import Update, Bot
from telegram.ext import CommandHandler, Dispatcher, MessageHandler, Filters

from telegram import InlineQueryResultArticle, ParseMode, InputTextMessageContent
from telegram.ext import InlineQueryHandler
from telegram.utils.helpers import escape_markdown

# Initialize the ddgr object. This is an ugly hack as ddgr does not provide the CLI methods in the Python module.

opts = ddgr.parse_args()
opts.keyword = ""  # TODO this is to be updated inside the loop
opts.json = True
colors = None
ddgr.Result.colors = colors
ddgr.Result.urlexpand = opts.expand
ddgr.DdgCmd.colors = colors


# Enable logging
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(level=logging.INFO)

# Define responses
OK_RESPONSE = {
    "statusCode": 200,
    "headers": {"Content-Type": "application/json"},
    "body": json.dumps("ok"),
}
ERROR_RESPONSE = {"statusCode": 400, "body": json.dumps("Oops, something went wrong!")}


def configure_telegram():
    """
    Configures the bot with a Telegram Token.
    Returns a bot instance.
    """

    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TELEGRAM_TOKEN:
        logger.error("The TELEGRAM_TOKEN must be set")
        raise NotImplementedError

    return Bot(TELEGRAM_TOKEN)


def start(update, context):
    """Send a message when the command /start is issued."""
    # update.message.reply_text("Hi!")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Use this bot inline to get DuckDuckGo search results.",
    )


def help_command(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text("Help!")


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def chatquery(update, context):
    """Handle in-chat queries and return search results."""

    search_string = str(update.message.text)

    opts.keywords = search_string
    repl = ddgr.DdgCmd(opts, "ddgr/1.9 (textmode; Linux x86_64; 1024x768)")
    repl.fetch(opts.json)

    results = repl.results
    reply_msg_list = [
        ("{} <b>{}</b> \n \n" "{} \n \n" "{}").format(i, r.title, r.url, r.abstract)
        for i, r in enumerate(results)
    ]
    
    for msg in reply_msg_list:
        update.message.reply_text(msg)

    
    


def inlinequery(update, context):
    """Handle the inline query."""
    query = update.inline_query.query

    if len(query) > 0:

        search_string = str(query)
        opts.keywords = search_string
        repl = ddgr.DdgCmd(opts, "ddgr/1.9 (textmode; Linux x86_64; 1024x768)")
        repl.fetch(opts.json)

        results = repl.results

        trslts = []
        for i, r in enumerate(results):

            input_message = ("<b>{}</b> \n \n" "{} \n \n" "{}").format(
                r.title, r.url, r.abstract
            )
            # print(input_message)

            r2 = InlineQueryResultArticle(
                uuid4(),
                r.title,
                InputTextMessageContent(
                    input_message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False,
                ),
                description=r.abstract,
                url=r.url,
            )

            trslts.append(r2)

        update.inline_query.answer(trslts)


# Initialize bot and dispatcher to register handlers
bot = configure_telegram()
dp = Dispatcher(bot, None, use_context=True)
# on noncommand i.e message - echo the message on Telegram
# dp.add_handler(MessageHandler(Filters.text, echo))
dp.add_handler(MessageHandler(Filters.text, chatquery))
# on different commands - answer in Telegram
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("help", help_command))

dp.add_handler(InlineQueryHandler(inlinequery))


def process_update(event, context):
    """
    Processes the received update and sends it to the dispatcher.
    """
    logger.info(f"Event: {event}")

    try:
        dp.process_update(Update.de_json(json.loads(event.get("body")), bot))
    except Exception as e:
        logger.error(e)
        return ERROR_RESPONSE

    return OK_RESPONSE
