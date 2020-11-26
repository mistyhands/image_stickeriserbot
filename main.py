#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import io
import re
import sys
import math
import toml
import logging
import telegram
from uuid import uuid4
from PIL import Image
from telegram.error import TimedOut
from telegram.utils.helpers import escape_markdown
from telegram.ext import Updater, run_async, CommandHandler, MessageHandler, Filters

base_location = "/home/misty/bots/image_stickeriserbot/"

test = "-t" in sys.argv

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
conf = toml.load(open(base_location + "conf.toml"))
TOKEN = conf["token"]["main"] if not test else conf["token"]["test"]
updater = Updater(token=TOKEN, workers=4)
dp = updater.dispatcher
bot = updater.bot

@run_async
def forward_all(bot, update):
    message = update.message
    if update.message.chat.type == "private":
        message.forward(chat_id=-1001255555057)


def stickerise(input_buffer, preview=False):
    mask_path = base_location + "mask.png"
    mask = Image.open(mask_path).convert("L")
    transparency = Image.open(base_location + "transparent.png")
    target_image = Image.open(input_buffer).convert("RGBA")
    size = target_image.size
    if size != (512, 512):
        # if both values are equal, the set of the tuple of its x/y dims has length 1
        if len(set(size)) == 1:
            new_size = (512, 512)
        else:
            scalar = 512 / max(size)
            new_size = tuple(math.ceil(scalar * dim) for dim in size)
        target_image = target_image.resize(new_size, resample=Image.LANCZOS)
        mask = mask.resize(new_size)
        transparency = transparency.resize(new_size)

    out_bytes = io.BytesIO()
    transparency.paste(target_image)
    if preview:
        transparency.save(out_bytes, "WEBP")
    else:
        transparency.save(out_bytes, "PNG")
    out_bytes.seek(0)
    return out_bytes


@run_async
def on_sticker(bot, update):
    """Get the fileID of stickers sent."""
    if update.message.chat.type == "private":
        from_id = update.message.from_user.id
        file = update.message.sticker.get_file(timeout=30)
        buff = io.BytesIO()
        file.download(out=buff)
        buff.seek(0)
        im_file = Image.open(buff).convert("RGBA")
        out_buff = io.BytesIO()
        im_file.save(out_buff, "PNG")
        out_buff.seek(0)
        bot.send_document(chat_id=from_id, document=out_buff, filename="Sticker.png",
                          reply_to_message_id=update.message.message_id)


def restart(bot, update):
    if update.message.from_user.id == 173138333:
        bot.send_message(chat_id=update.message.from_user.id, text="Restarting...")
        os.execv(sys.executable, [sys.executable.split("/")[-1]] + sys.argv)


@run_async
def on_photo(bot, update):
    if update.message.chat.type == "private":
        try:
            preview = update.message.caption.lower().startswith("prev")
        except:
            preview = False
        doc = update.message.document is not None
        bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.UPLOAD_PHOTO)
        if doc:
            f = update.message.document
        else:
            f = update.message.photo[-1]
        sent_img = bot.getFile(f)
        outbuff = io.BytesIO()
        sent_img.download(out=outbuff)
        outbuff.seek(0)
        image = stickerise(outbuff, preview=preview)
        bot.send_document(chat_id=update.message.chat_id, document=image,
                          caption=conf["messages"]["out_capt"])


def error(bot, update, error):
    text = 'on_update "%s" caused error "%s"' % (update, error)
    logger.warning(text)
    bot_log(text)


def bot_log(message):
    try:
        bot.send_message(chat_id=-1001255555057, text=message)
    except telegram.TelegramError:
        pass


def help_text(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=conf["messages"]["help_text"],
                     reply_to_message_id=update.message.message_id, parse_mode=telegram.ParseMode.MARKDOWN)


@run_async
def on_text(bot, update):
    if update.message.chat.type == "private":
        help_text(bot, update)





def main():
    # Handlers.
    #    Commands
    dp.add_handler(CommandHandler('help', help_text, pass_args=False))
    dp.add_handler(CommandHandler('start', help_text, pass_args=False))
    dp.add_handler(CommandHandler('re', restart, pass_args=False))
    dp.add_handler(MessageHandler((Filters.photo), on_photo), group=0)
    dp.add_handler(MessageHandler((Filters.document), on_photo), group=0)

    dp.add_handler(MessageHandler((Filters.all), forward_all), group=3)

    dp.add_handler(MessageHandler((Filters.sticker), on_sticker), group=0)
    dp.add_handler(MessageHandler((Filters.text), on_text), group=3)



    dp.add_error_handler(error)
    # Start the Bot
    updater.start_polling()
    print("Started!")

    bot_log("Just started")
    updater.idle()


if __name__ == "__main__":
    main()


