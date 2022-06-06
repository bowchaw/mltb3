from base64 import b64encode
from requests import utils as rutils
from re import match as re_match, search as re_search, split as re_split
from time import sleep, time
from os import path as ospath, remove as osremove, listdir, walk
from shutil import rmtree
from threading import Thread
from subprocess import run as srun
from pathlib import PurePath
from html import escape
from telegram.ext import CommandHandler
from telegram import InlineKeyboardMarkup

from bot import Interval, INDEX_URL, BUTTON_FOUR_NAME, BUTTON_FOUR_URL, BUTTON_FIVE_NAME, BUTTON_FIVE_URL, \
                BUTTON_SIX_NAME, BUTTON_SIX_URL, VIEW_LINK, aria2, QB_SEED, dispatcher, DOWNLOAD_DIR, \
                download_dict, download_dict_lock, TG_SPLIT_SIZE, LOGGER, MEGA_KEY, DB_URI, INCOMPLETE_TASK_NOTIFIER
from bot.helper.ext_utils.bot_utils import is_url, is_magnet, is_gdtot_link, is_mega_link, is_gdrive_link, get_content_type
from bot.helper.ext_utils.fs_utils import get_base_name, get_path_size, split_file, clean_download
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException, NotSupportedExtractionArchive
from bot.helper.mirror_utils.download_utils.aria2_download import add_aria2c_download
from bot.helper.mirror_utils.download_utils.gd_downloader import add_gd_download
from bot.helper.mirror_utils.download_utils.qbit_downloader import QbDownloader
from bot.helper.mirror_utils.download_utils.mega_downloader import MegaDownloader
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator
from bot.helper.mirror_utils.download_utils.telegram_downloader import TelegramDownloadHelper
from bot.helper.mirror_utils.status_utils.extract_status import ExtractStatus
from bot.helper.mirror_utils.status_utils.zip_status import ZipStatus
from bot.helper.mirror_utils.status_utils.split_status import SplitStatus
from bot.helper.mirror_utils.status_utils.upload_status import UploadStatus
from bot.helper.mirror_utils.status_utils.tg_upload_status import TgUploadStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.upload_utils.pyrogramEngine import TgUploader
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, delete_all_messages, update_all_messages
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import DbManger


class MirrorListener:
    def __init__(self, bot, message, isZip=False, extract=False, isQbit=False, isLeech=False, pswd=None, tag=None):
        self.bot = bot
        self.message = message
        self.uid = self.message.message_id
        self.extract = extract
        self.isZip = isZip
        self.isQbit = isQbit
        self.isLeech = isLeech
        self.pswd = pswd
        self.tag = tag
        self.isPrivate = self.message.chat.type in ['private', 'group']

    def clean(self):
        try:
            aria2.purge()
            Interval[0].cancel()
            del Interval[0]
            delete_all_messages()
        except IndexError:
            pass

    def onDownloadStart(self):
        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().add_incomplete_task(self.message.chat.id, self.message.link, self.tag)



    def onDownloadError(self, error):
        error = error.replace('<', ' ').replace('>', ' ')
        clean_download(f'{DOWNLOAD_DIR}{self.uid}')
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        msg = f"{self.tag} your download has been stopped due to: {error}"
        sendMessage(msg, self.bot, self.message)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().rm_complete_task(self.message.link)

    def onUploadComplete(self, link: str, size, files, folders, typ, name: str):
        if not self.isPrivate and INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
            DbManger().rm_complete_task(self.message.link)
        msg = f"<b>Name: </b><code>{escape(name)}</code>\n\n<b>Size: </b>{size}"
        if self.isLeech:
            msg += f'\n<b>Total Files: </b>{folders}'
            if typ != 0:
                msg += f'\n<b>Corrupted Files: </b>{typ}'
            msg += f'\n<b>cc: </b>{self.tag}\n\n'
            if not files:
                sendMessage(msg, self.bot, self.message)
            else:
                fmsg = ''
                for index, (link, name) in enumerate(files.items(), start=1):
                    fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                    if len(fmsg.encode() + msg.encode()) > 4000:
                        sendMessage(msg + fmsg, self.bot, self.message)
                        sleep(1)
                        fmsg = ''
                if fmsg != '':
                    sendMessage(msg + fmsg, self.bot, self.message)
        else:
            msg += f'\n\n<b>Type: </b>{typ}'
            if ospath.isdir(f'{DOWNLOAD_DIR}{self.uid}/{name}'):
                msg += f'\n<b>SubFolders: </b>{folders}'
                msg += f'\n<b>Files: </b>{files}'
            msg += f'\n\n<b>cc: </b>{self.tag}'
            buttons = ButtonMaker()
            link = short_url(link)
            buttons.buildbutton("☁️ Drive Link", link)
            LOGGER.info(f'Done Uploading {name}')
            if INDEX_URL is not None:
                url_path = rutils.quote(f'{name}')
                share_url = f'{INDEX_URL}/{url_path}'
                if ospath.isdir(f'{DOWNLOAD_DIR}/{self.uid}/{name}'):
                    share_url += '/'
                    share_url = short_url(share_url)
                    buttons.buildbutton("⚡ Index Link", share_url)
                else:
                    share_url = short_url(share_url)
                    buttons.buildbutton("⚡ Index Link", share_url)
                    if VIEW_LINK:
                        share_urls = f'{INDEX_URL}/{url_path}?a=view'
                        share_urls = short_url(share_urls)
                        buttons.buildbutton("🌐 View Link", share_urls)
            if BUTTON_FOUR_NAME is not None and BUTTON_FOUR_URL is not None:
                buttons.buildbutton(f"{BUTTON_FOUR_NAME}", f"{BUTTON_FOUR_URL}")
            if BUTTON_FIVE_NAME is not None and BUTTON_FIVE_URL is not None:
                buttons.buildbutton(f"{BUTTON_FIVE_NAME}", f"{BUTTON_FIVE_URL}")
            if BUTTON_SIX_NAME is not None and BUTTON_SIX_URL is not None:
                buttons.buildbutton(f"{BUTTON_SIX_NAME}", f"{BUTTON_SIX_URL}")
            sendMarkup(msg, self.bot, self.message, InlineKeyboardMarkup(buttons.build_menu(2)))
            if self.isQbit and QB_SEED and not self.extract:
                if self.isZip:
                    try:
                        osremove(f'{DOWNLOAD_DIR}{self.uid}/{name}')
                    except:
                        pass

def _mirror(bot, message, isZip=False, extract=False, isQbit=False, isLeech=False, pswd=None, multi=0):
    mesg = message.text.split('\n')
    message_args = mesg[0].split(' ', maxsplit=1)
    name_args = mesg[0].split('|', maxsplit=1)
    qbitsel = False
    is_gdtot = False
    try:
        link = message_args[1]
        if link.startswith("s ") or link == "s":
            qbitsel = True
            message_args = mesg[0].split(' ', maxsplit=2)
            link = message_args[2].strip()
        elif link.isdigit():
            multi = int(link)
            raise IndexError
        if link.startswith(("|", "pswd: ")):
            raise IndexError
    except:
        link = ''
    try:
        name = name_args[1]
        name = name.split(' pswd: ')[0]
        name = name.strip()
    except:
        name = ''
    link = re_split(r"pswd:| \|", link)[0]
    link = link.strip()
    pswdMsg = mesg[0].split(' pswd: ')
    if len(pswdMsg) > 1:
        pswd = pswdMsg[1]

    if message.from_user.username:
        tag = f"@{message.from_user.username}"
    else:
        tag = message.from_user.mention_html(message.from_user.first_name)

    reply_to = message.reply_to_message
    if reply_to is not None:
        file = None
        media_array = [reply_to.document, reply_to.video, reply_to.audio]
        for i in media_array:
            if i is not None:
                file = i
                break

        if not reply_to.from_user.is_bot:
            if reply_to.from_user.username:
                tag = f"@{reply_to.from_user.username}"
            else:
                tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)

        if (
            not is_url(link)
            and not is_magnet(link)
            or len(link) == 0
        ):

            if file is None:
                reply_text = reply_to.text
                if is_url(reply_text) or is_magnet(reply_text):
                    link = reply_text.strip()
            elif file.mime_type != "application/x-bittorrent" and not isQbit:
                listener = MirrorListener(bot, message, isZip, extract, isQbit, isLeech, pswd, tag)
                Thread(target=TelegramDownloadHelper(listener).add_download, args=(message, f'{DOWNLOAD_DIR}{listener.uid}/', name)).start()
                if multi > 1:
                    sleep(4)
                    nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
                    nextmsg = sendMessage(message_args[0], bot, nextmsg)
                    nextmsg.from_user.id = message.from_user.id
                    multi -= 1
                    sleep(4)
                    Thread(target=_mirror, args=(bot, nextmsg, isZip, extract, isQbit, isLeech, pswd, multi)).start()
                return
            else:
                link = file.get_file().file_path

    if not is_url(link) and not is_magnet(link) and not ospath.exists(link):
        help_msg = "<b>Send link along with command line:</b>"
        help_msg += "\n<code>/command</code> {link} |newname pswd: xx [zip/unzip]"
        help_msg += "\n\n<b>By replying to link or file:</b>"
        help_msg += "\n<code>/command</code> |newname pswd: xx [zip/unzip]"
        help_msg += "\n\n<b>Direct link authorization:</b>"
        help_msg += "\n<code>/command</code> {link} |newname pswd: xx\nusername\npassword"
        help_msg += "\n\n<b>Qbittorrent selection:</b>"
        help_msg += "\n<code>/qbcommand</code> <b>s</b> {link} or by replying to {file/link}"
        help_msg += "\n\n<b>Multi links only by replying to first link or file:</b>"
        help_msg += "\n<code>/command</code> 10(number of links/files)"
        return sendMessage(help_msg, bot, message)

    LOGGER.info(link)

    if not is_mega_link(link) and not isQbit and not is_magnet(link) \
        and not is_gdrive_link(link) and not link.endswith('.torrent'):
        content_type = get_content_type(link)
        if content_type is None or re_match(r'text/html|text/plain', content_type):
            try:
                is_gdtot = is_gdtot_link(link)
                link = direct_link_generator(link)
                LOGGER.info(f"Generated link: {link}")
            except DirectDownloadLinkException as e:
                LOGGER.info(str(e))
                if str(e).startswith('ERROR:'):
                    return sendMessage(str(e), bot, message)

    listener = MirrorListener(bot, message, isZip, extract, isQbit, isLeech, pswd, tag)

    if is_gdrive_link(link):
            Thread(target=add_gd_download, args=(link, listener, is_gdtot)).start()
    elif is_mega_link(link):
        if MEGA_KEY is not None:
            Thread(target=MegaDownloader(listener).add_download, args=(link, f'{DOWNLOAD_DIR}{listener.uid}/')).start()
        else:
            sendMessage('MEGA_API_KEY not Provided!', bot, message)
    elif isQbit:
        Thread(target=QbDownloader(listener).add_qb_torrent, args=(link, f'{DOWNLOAD_DIR}{listener.uid}', qbitsel)).start()
    else:
        if len(mesg) > 1:
            try:
                ussr = mesg[1]
            except:
                ussr = ''
            try:
                pssw = mesg[2]
            except:
                pssw = ''
            auth = f"{ussr}:{pssw}"
            auth = "Basic " + b64encode(auth.encode()).decode('ascii')
        else:
            auth = ''
        Thread(target=add_aria2c_download, args=(link, f'{DOWNLOAD_DIR}{listener.uid}', listener, name, auth)).start()

    if multi > 1:
        sleep(4)
        nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
        msg = message_args[0]
        if len(mesg) > 2:
            msg += '\n' + mesg[1] + '\n' + mesg[2]
        nextmsg = sendMessage(msg, bot, nextmsg)
        nextmsg.from_user.id = message.from_user.id
        multi -= 1
        sleep(4)
        Thread(target=_mirror, args=(bot, nextmsg, isZip, extract, isQbit, isLeech, pswd, multi)).start()


def mirror(update, context):
    _mirror(context.bot, update.message)


mirrors_handler = CommandHandler(BotCommands.MirrorsCommand, mirror,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)

dispatcher.add_handler(mirrors_handler)
