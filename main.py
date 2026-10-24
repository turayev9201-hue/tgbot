import asyncio
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatAction, ParseMode
from dotenv import load_dotenv
import yt_dlp

# ================= SOZLAMALAR =================
load_dotenv()
TOKEN_1 = os.getenv("TOKEN_1")
TOKEN_2 = os.getenv("TOKEN_2")
TOKEN_3 = os.getenv("TOKEN_3")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_URL = os.getenv("CHANNEL_URL")
ADMIN_ID = 8870374351

logging.basicConfig(level=logging.INFO)

# ================= BAZA =================
conn = sqlite3.connect('bot_stats.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, joined_at TEXT, downloads INTEGER DEFAULT 0, lang TEXT DEFAULT NULL)''')
conn.commit()

def add_user(user_id, first_name, username):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, username, joined_at) VALUES (?, ?, ?, ?)",
                   (user_id, first_name, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

def increment_download(user_id):
    cursor.execute("UPDATE users SET downloads = downloads + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def get_user_lang(user_id):
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    return res[0] if res else None

def set_user_lang(user_id, lang):
    cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()

URL_CACHE = {}

# ================= TILLAR =================
TEXTS = {
    'uz': {
        'choose_lang_first': "🌐 <b>Iltimos, muloqot tilini tanlang:</b>",
        'welcome': "✨ <b>Assalomu alaykum, {name}!</b>\n\n🤖 <b>Premium Media Yuklovchi</b> botiga xush kelibsiz.\n\nDavom etish uchun iltimos, avval rasmiy kanalimizga a'zo bo'ling.",
        'btn_sub': "📢 Kanalga a'zo bo'lish",
        'btn_check': "✅ Obunani tekshirish",
        'not_subbed': "❌ Siz hali kanalga a'zo bo'lmadingiz!",
        'sub_ok': "🎉 <b>Obuna muvaffaqiyatli tasdiqlandi!</b>",
        'about': "ℹ️ <b>Bot haqida ma'lumot</b>\n\nBu bot Instagram, YouTube va TikTok kabi platformalardan video va musiqa yuklab olish uchun xizmat qiladi.\n\n<b>Foydalanish shartlari:</b>\n1. Faqat ruxsat etilgan kontentni yuklang.\n2. Bot 50MB gacha fayllarni qo'llab-quvvatlaydi.",
        'menu': "👋 <b>Xush kelibsiz, {name}!</b>\n\n👇 Quyidagi xizmatlardan birini tanlang:\n━━━━━━━━━━━━━━━━━━━━━━",
        'btn_music': "🎵 Musiqa qidirish",
        'btn_video': "🎬 Video yuklash",
        'btn_lang': "🌐 Tilni o'zgartirish",
        'btn_stats': "📊 Mening statistikam",
        'btn_about': "ℹ️ Bot haqida",
        'btn_back': "⬅️ Orqaga",
        'btn_download_mp3': "🎵 Musiqa (MP3) yuklab olish",
        'ask_music': "🎧 <b>Musiqa nomini yoki ijrochi ismini yozing:</b>\n\n<i>Masalan: Shahzoda - Kechalar</i>",
        'ask_video': "🔗 <b>Video havolasini yuboring:</b>\n\n<i>Instagram, YouTube, TikTok va boshqa havolalar.</i>",
        'catch_all': "🤔 <b>Tushunmadim.</b>\n\nIltimos, video yuklash uchun havola (link) tashlang yoki menyudan kerakli bo'limni tanlang.",
        'choose_quality': "🎞️ <b>Video sifatini tanlang:</b>",
        'loading': "⏳ <i>Yuklanmoqda, iltimos kuting...</i>",
        'dl_error': "❌ <b>Xatolik yuz berdi.</b>\nHavola noto'g'ri, yopiq yoki YouTube tomonidan bloklangan.",
        'file_too_large': "⚠️ <b>Fayl hajmi juda katta!</b>\nTelegram botlari 50MB dan katta fayllarni yubora olmaydi.",
        'nothing_found': "❌ <b>Afsuski, hech narsa topilmadi.</b>",
        'must_sub': "❗️ <b>Botdan foydalanish uchun avval kanalga a'zo bo'ling!</b>",
        'lang_changed': "✅ <b>Til o'zgartirildi: O'zbekcha</b>",
        'my_stats': "📊 <b>Sizning statistikangiz:</b>\n\n🆔 ID: <code>{id}</code>\n📥 Yuklagan fayllaringiz: <b>{downloads} ta</b>",
    },
    'ru': {
        'choose_lang_first': "🌐 <b>Пожалуйста, выберите язык общения:</b>",
        'welcome': "✨ <b>Здравствуйте, {name}!</b>\n\n🤖 Добро пожаловать в <b>Premium Media Downloader</b>.\n\nЧтобы продолжить, подпишитесь на наш канал.",
        'btn_sub': "📢 Подписаться",
        'btn_check': "✅ Проверить",
        'not_subbed': "❌ Вы еще не подписались на канал!",
        'sub_ok': "🎉 <b>Подписка подтверждена!</b>",
        'about': "ℹ️ <b>О боте</b>\n\nЭтот бот скачивает видео и музыку из Instagram, YouTube, TikTok и других платформ.\n\n<b>Условия использования:</b>\n1. Скачивайте только разрешенный контент.\n2. Бот поддерживает файлы до 50MB.",
        'menu': "👋 <b>Добро пожаловать, {name}!</b>\n\n👇 Выберите услугу:\n━━━━━━━━━━━━━━━━━━━━━━",
        'btn_music': "🎵 Поиск музыки",
        'btn_video': "🎬 Скачать видео",
        'btn_lang': "🌐 Сменить язык",
        'btn_stats': "📊 Моя статистика",
        'btn_about': "ℹ️ О боте",
        'btn_back': "⬅️ Назад",
        'btn_download_mp3': "🎵 Скачать музыку (MP3)",
        'ask_music': "🎧 <b>Введите название песни или исполнителя:</b>\n\n<i>Например: Imagine Dragons - Believer</i>",
        'ask_video': "🔗 <b>Отправьте ссылку на видео:</b>\n\n<i>Instagram, YouTube, TikTok и др.</i>",
        'catch_all': "🤔 <b>Я вас не понял.</b>\n\nПожалуйста, отправьте ссылку на видео или выберите раздел в меню.",
        'choose_quality': "🎞️ <b>Выберите качество видео:</b>",
        'loading': "⏳ <i>Загрузка началась, пожалуйста, подождите...</i>",
        'dl_error': "❌ <b>Ошибка.</b>\nНеверная ссылка, приватное видео или заблокировано YouTube.",
        'file_too_large': "⚠️ <b>Файл слишком большой!</b>\nБоты Telegram не могут отправлять файлы больше 50MB.",
        'nothing_found': "❌ <b>К сожалению, ничего не найдено.</b>",
        'must_sub': "❗️ <b>Сначала подпишитесь на канал!</b>",
        'lang_changed': "✅ <b>Язык изменен: Русский</b>",
        'my_stats': "📊 <b>Ваша статистика:</b>\n\n🆔 ID: <code>{id}</code>\n📥 Скачано файлов: <b>{downloads}</b>",
    },
    'en': {
        'choose_lang_first': "🌐 <b>Please choose your language:</b>",
        'welcome': "✨ <b>Hello, {name}!</b>\n\n🤖 Welcome to <b>Premium Media Downloader</b>.\n\nTo continue, please subscribe to our channel.",
        'btn_sub': "📢 Subscribe",
        'btn_check': "✅ Check",
        'not_subbed': "❌ You are not subscribed yet!",
        'sub_ok': "🎉 <b>Subscription confirmed!</b>",
        'about': "ℹ️ <b>About Bot</b>\n\nThis bot downloads videos and music from Instagram, YouTube, TikTok and other platforms.\n\n<b>Terms of Use:</b>\n1. Download only permitted content.\n2. Bot supports files up to 50MB.",
        'menu': "👋 <b>Welcome, {name}!</b>\n\n👇 Choose a service:\n━━━━━━━━━━━━━━━━━━━━━━",
        'btn_music': "🎵 Search Music",
        'btn_video': "🎬 Download Video",
        'btn_lang': "🌐 Change Language",
        'btn_stats': "📊 My Stats",
        'btn_about': "ℹ️ About Bot",
        'btn_back': "⬅️ Back",
        'btn_download_mp3': "🎵 Download Music (MP3)",
        'ask_music': "🎧 <b>Enter song name or artist:</b>\n\n<i>e.g. Imagine Dragons - Believer</i>",
        'ask_video': "🔗 <b>Send video link:</b>\n\n<i>Instagram, YouTube, TikTok etc.</i>",
        'catch_all': "🤔 <b>I didn't understand.</b>\n\nPlease send a video link or choose a section from the menu.",
        'choose_quality': "🎞️ <b>Choose video quality:</b>",
        'loading': "⏳ <i>Loading started, please wait...</i>",
        'dl_error': "❌ <b>Error.</b>\nInvalid link, private video or blocked by YouTube.",
        'file_too_large': "⚠️ <b>File too large!</b>\nTelegram bots cannot send files over 50MB.",
        'nothing_found': "❌ <b>Nothing found.</b>",
        'must_sub': "❗️ <b>Please subscribe to the channel first!</b>",
        'lang_changed': "✅ <b>Language changed: English</b>",
        'my_stats': "📊 <b>Your stats:</b>\n\n🆔 ID: <code>{id}</code>\n📥 Downloads: <b>{downloads}</b>",
    }
}

# ================= HOLATLAR =================
class BotStates(StatesGroup):
    choosing_language = State()
    waiting_for_music = State()
    choosing_quality = State()

# ================= OBUNA TEKSHIRISH =================
async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception as e:
        logging.error(f"Obuna tekshirishda xato: {e}")
        return False
    return False

# ================= YUKLASH SOZLAMALARI (Barcha cheklovlarni chetlab o'tish) =================
# YouTube blokirovkasini chetlab o'tish uchun so'nggi usullar
BASE_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'max_filesize': 50000000,
    'restrictfilenames': True,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios', 'mweb', 'web_safari'], 
            'skip': ['hls', 'dash'] # Ba'zi muammoli formatlarni o'tkazib yuborish
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-us,en;q=0.5',
    }
}

def sync_download_video(url, user_id, quality="720p"):
    os.makedirs("downloads", exist_ok=True)
    
    if quality == "480p":
        fmt = 'b[height<=480][ext=mp4]/b[height<=480]/b'
    elif quality == "1080p":
        fmt = 'b[height<=1080][ext=mp4]/b[height<=1080]/b'
    else:
        fmt = 'b[height<=720][ext=mp4]/b[height<=720]/b'

    ydl_opts = BASE_OPTS.copy()
    ydl_opts.update({
        'format': fmt,
        'outtmpl': f'downloads/{user_id}_%(title)s.%(ext)s',
    })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return info, filename

def sync_extract_audio_from_url(url, user_id):
    os.makedirs("downloads", exist_ok=True)
    ydl_opts = BASE_OPTS.copy()
    ydl_opts.update({
        'format': 'bestaudio/best',
        'outtmpl': f'downloads/{user_id}_audio_%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
        return info, filename

def sync_search_music(query, user_id):
    os.makedirs("downloads", exist_ok=True)
    ydl_opts = BASE_OPTS.copy()
    ydl_opts.update({
        'format': 'bestaudio/best',
        'outtmpl': f'downloads/{user_id}_search_%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    })
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=True)['entries'][0]
        filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
        return info, filename

# ================= HANDLERLAR =================
def register_handlers(dp: Dispatcher, bot: Bot):
    router = Router()
    dp.include_router(router)

    def get_lang_keyboard():
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="setlang_uz")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en")]
        ])

    def get_sub_keyboard(lang):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=TEXTS[lang]['btn_sub'], url=CHANNEL_URL)],
            [InlineKeyboardButton(text=TEXTS[lang]['btn_check'], callback_data="check_sub")]
        ])

    def get_main_menu(user_id, name, lang):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=TEXTS[lang]['btn_video'], callback_data="video_download"),
             InlineKeyboardButton(text=TEXTS[lang]['btn_music'], callback_data="music_search")],
            [InlineKeyboardButton(text=TEXTS[lang]['btn_stats'], callback_data="my_stats"),
             InlineKeyboardButton(text=TEXTS[lang]['btn_lang'], callback_data="change_lang")],
            [InlineKeyboardButton(text=TEXTS[lang]['btn_about'], callback_data="about")],
            [InlineKeyboardButton(text="📢 Kanalimiz", url=CHANNEL_URL)]
        ])

    async def show_menu_or_sub(message: Message, user_id: int, first_name: str, lang: str):
        if not await check_subscription(bot, user_id):
            await message.answer(TEXTS[lang]['welcome'].format(name=first_name), reply_markup=get_sub_keyboard(lang), parse_mode=ParseMode.HTML)
        else:
            await message.answer(TEXTS[lang]['menu'].format(name=first_name), reply_markup=get_main_menu(user_id, first_name, lang), parse_mode=ParseMode.HTML)

    @router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        await state.clear()
        user_id = message.from_user.id
        first_name = message.from_user.first_name or "Foydalanuvchi"
        add_user(user_id, first_name, message.from_user.username)
        
        lang = get_user_lang(user_id)
        if not lang:
            await state.set_state(BotStates.choosing_language)
            await message.answer(TEXTS['uz']['choose_lang_first'], reply_markup=get_lang_keyboard(), parse_mode=ParseMode.HTML)
        else:
            await show_menu_or_sub(message, user_id, first_name, lang)

    @router.callback_query(F.data.startswith("setlang_"))
    async def set_initial_lang(callback: CallbackQuery, state: FSMContext):
        lang = callback.data.split("_")[1]
        user_id = callback.from_user.id
        set_user_lang(user_id, lang)
        await state.clear()
        
        await callback.message.delete()
        await show_menu_or_sub(callback.message, user_id, callback.from_user.first_name, lang)
        await callback.answer(TEXTS[lang]['lang_changed'])

    @router.callback_query(F.data == "check_sub")
    async def check_sub_callback(callback: CallbackQuery):
        user_id = callback.from_user.id
        lang = get_user_lang(user_id) or 'uz'
        if await check_subscription(bot, user_id):
            await callback.message.edit_text(TEXTS[lang]['sub_ok'], reply_markup=get_main_menu(user_id, callback.from_user.first_name, lang), parse_mode=ParseMode.HTML)
        else:
            await callback.answer(TEXTS[lang]['not_subbed'], show_alert=True)
        await callback.answer()

    @router.callback_query(F.data == "main_menu")
    async def back_to_menu(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        lang = get_user_lang(callback.from_user.id) or 'uz'
        await callback.message.edit_text(TEXTS[lang]['menu'].format(name=callback.from_user.first_name), reply_markup=get_main_menu(callback.from_user.id, callback.from_user.first_name, lang), parse_mode=ParseMode.HTML)
        await callback.answer()

    @router.callback_query(F.data == "about")
    async def about_bot(callback: CallbackQuery):
        lang = get_user_lang(callback.from_user.id) or 'uz'
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=TEXTS[lang]['btn_back'], callback_data="main_menu")]])
        await callback.message.edit_text(TEXTS[lang]['about'], reply_markup=kb, parse_mode=ParseMode.HTML)
        await callback.answer()

    @router.callback_query(F.data == "my_stats")
    async def my_stats(callback: CallbackQuery):
        lang = get_user_lang(callback.from_user.id) or 'uz'
        cursor.execute("SELECT downloads FROM users WHERE user_id = ?", (callback.from_user.id,))
        dl = cursor.fetchone()[0]
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=TEXTS[lang]['btn_back'], callback_data="main_menu")]])
        await callback.message.edit_text(TEXTS[lang]['my_stats'].format(id=callback.from_user.id, downloads=dl), reply_markup=kb, parse_mode=ParseMode.HTML)
        await callback.answer()

    @router.callback_query(F.data == "change_lang")
    async def change_lang_menu(callback: CallbackQuery):
        lang = get_user_lang(callback.from_user.id) or 'uz'
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="setlang_uz"),
             InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru"),
             InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en")],
            [InlineKeyboardButton(text=TEXTS[lang]['btn_back'], callback_data="main_menu")]
        ])
        await callback.message.edit_text("🌐 <b>Tilni tanlang / Выберите язык / Choose language:</b>", reply_markup=kb, parse_mode=ParseMode.HTML)
        await callback.answer()

    @router.callback_query(F.data == "video_download")
    async def video_download(callback: CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        lang = get_user_lang(user_id) or 'uz'
        if not await check_subscription(bot, user_id):
            await callback.answer(TEXTS[lang]['must_sub'], show_alert=True)
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=TEXTS[lang]['btn_back'], callback_data="main_menu")]])
        await callback.message.edit_text(TEXTS[lang]['ask_video'], reply_markup=kb, parse_mode=ParseMode.HTML)
        await callback.answer()

    @router.callback_query(F.data == "music_search")
    async def music_search(callback: CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        lang = get_user_lang(user_id) or 'uz'
        if not await check_subscription(bot, user_id):
            await callback.answer(TEXTS[lang]['must_sub'], show_alert=True)
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=TEXTS[lang]['btn_back'], callback_data="main_menu")]])
        await callback.message.edit_text(TEXTS[lang]['ask_music'], reply_markup=kb, parse_mode=ParseMode.HTML)
        await state.set_state(BotStates.waiting_for_music)
        await callback.answer()

    # --- AQLLI HAVOLA QABUL QILISH ---
    @router.message(F.text.startswith("http"))
    async def handle_any_link(message: Message, state: FSMContext):
        user_id = message.from_user.id
        lang = get_user_lang(user_id) or 'uz'
        
        # Obunani tekshirish
        if not await check_subscription(bot, user_id):
            await message.answer(TEXTS[lang]['must_sub'], reply_markup=get_sub_keyboard(lang))
            return

        current_state = await state.get_state()
        if current_state == BotStates.waiting_for_music.state:
            return

        text = message.text.strip()
        await state.update_data(video_url=text)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎬 480p", callback_data="quality_480p"),
             InlineKeyboardButton(text="🎬 720p", callback_data="quality_720p"),
             InlineKeyboardButton(text="🎬 1080p", callback_data="quality_1080p")],
            [InlineKeyboardButton(text=TEXTS[lang]['btn_back'], callback_data="main_menu")]
        ])
        await message.answer(TEXTS[lang]['choose_quality'], reply_markup=kb, parse_mode=ParseMode.HTML)
        await state.set_state(BotStates.choosing_quality)

    # --- SIFATNI TANLASH VA MP3 TUGMASI ---
    @router.callback_query(F.data.startswith("quality_"), BotStates.choosing_quality)
    async def process_quality(callback: CallbackQuery, state: FSMContext):
        quality = callback.data.split("_")[1]
        data = await state.get_data()
        video_url = data.get('video_url')
        user_id = callback.from_user.id
        lang = get_user_lang(user_id) or 'uz'

        await callback.message.delete()
        status_msg = await callback.message.answer(TEXTS[lang]['loading'], parse_mode=ParseMode.HTML)
        await bot.send_chat_action(callback.message.chat.id, ChatAction.UPLOAD_VIDEO)
        
        filename = None
        try:
            info, filename = await asyncio.to_thread(sync_download_video, video_url, user_id, quality)
            
            if os.path.getsize(filename) > 50 * 1024 * 1024:
                await status_msg.edit_text(TEXTS[lang]['file_too_large'], parse_mode=ParseMode.HTML)
            else:
                link_id = str(uuid.uuid4())[:10]
                URL_CACHE[link_id] = video_url

                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=TEXTS[lang]['btn_download_mp3'], callback_data=f"getmp3_{link_id}")]
                ])

                await callback.message.answer_video(
                    FSInputFile(filename), 
                    caption=f"🎬 <b>{info.get('title', 'Video')}</b> [{quality}]", 
                    reply_markup=kb,
                    parse_mode=ParseMode.HTML
                )
                increment_download(user_id)
                await status_msg.delete()
                
        except Exception as e:
            logging.error(f"Video xato: {e}")
            await status_msg.edit_text(TEXTS[lang]['dl_error'], parse_mode=ParseMode.HTML)
        finally:
            if filename and os.path.exists(filename):
                try: os.remove(filename)
                except: pass
            await state.clear()

    # --- VIDEODAN MP3 YUKLASH ---
    @router.callback_query(F.data.startswith("getmp3_"))
    async def download_mp3_from_video(callback: CallbackQuery):
        link_id = callback.data.split("_")[1]
        video_url = URL_CACHE.get(link_id)
        user_id = callback.from_user.id
        lang = get_user_lang(user_id) or 'uz'

        if not video_url:
            await callback.answer("❌ Havola eskirgan. Iltimos, videoni qaytadan yuboring.", show_alert=True)
            return

        await callback.message.edit_reply_markup(reply_markup=None)
        status_msg = await callback.message.answer(TEXTS[lang]['loading'], parse_mode=ParseMode.HTML)
        await bot.send_chat_action(callback.message.chat.id, ChatAction.UPLOAD_VOICE)
        
        filename = None
        try:
            info, filename = await asyncio.to_thread(sync_extract_audio_from_url, video_url, user_id)
            
            if os.path.getsize(filename) > 50 * 1024 * 1024:
                await status_msg.edit_text(TEXTS[lang]['file_too_large'], parse_mode=ParseMode.HTML)
            else:
                await callback.message.answer_audio(
                    FSInputFile(filename), 
                    caption=f"🎵 <b>{info.get('title', 'Musiqa')}</b>", 
                    title=info.get('title', 'Musiqa'), 
                    performer=info.get('uploader', 'Noma\'lum'), 
                    parse_mode=ParseMode.HTML
                )
                increment_download(user_id)
                await status_msg.delete()
                
        except Exception as e:
            logging.error(f"Audio xato: {e}")
            await status_msg.edit_text(TEXTS[lang]['dl_error'], parse_mode=ParseMode.HTML)
        finally:
            if filename and os.path.exists(filename):
                try: os.remove(filename)
                except: pass

    # --- MUSIQA QIDIRISH ---
    @router.message(BotStates.waiting_for_music)
    async def handle_music_search(message: Message, state: FSMContext):
        text = message.text.strip()
        user_id = message.from_user.id
        lang = get_user_lang(user_id) or 'uz'
        
        status_msg = await message.answer(TEXTS[lang]['loading'], parse_mode=ParseMode.HTML)
        await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VOICE)
        
        filename = None
        try:
            info, filename = await asyncio.to_thread(sync_search_music, text, user_id)
            
            if os.path.getsize(filename) > 50 * 1024 * 1024:
                await status_msg.edit_text(TEXTS[lang]['file_too_large'], parse_mode=ParseMode.HTML)
            else:
                await message.answer_audio(
                    FSInputFile(filename), 
                    caption=f"🎵 <b>{info.get('title', 'Musiqa')}</b>", 
                    title=info.get('title', 'Musiqa'), 
                    performer=info.get('uploader', 'Noma\'lum'), 
                    parse_mode=ParseMode.HTML
                )
                increment_download(user_id)
                await status_msg.delete()
                
        except Exception as e:
            logging.error(f"Musiqa xato: {e}")
            await status_msg.edit_text(TEXTS[lang]['nothing_found'], parse_mode=ParseMode.HTML)
        finally:
            if filename and os.path.exists(filename):
                try: os.remove(filename)
                except: pass
            await state.clear()

    # --- HAR QANDAY BOSHQA XABARGA JAVOB (CATCH-ALL) ---
    @router.message(F.text & ~F.text.startswith("http") & ~F.text.startswith("/"))
    async def catch_all_text(message: Message, state: FSMContext):
        user_id = message.from_user.id
        lang = get_user_lang(user_id) or 'uz'
        
        # Majburiy obuna
        if not await check_subscription(bot, user_id):
            await message.answer(TEXTS[lang]['must_sub'], reply_markup=get_sub_keyboard(lang))
            return
            
        # Agar musiqa qidirayotgan bo'lsa, catch-all ishlamaydi (musiqa handleri o'zi javob beradi)
        current_state = await state.get_state()
        if current_state == BotStates.waiting_for_music.state:
            return
            
        await message.answer(TEXTS[lang]['catch_all'])

    # --- ADMIN PANEL ---
    @router.message(Command("admin"))
    async def admin_panel(message: Message):
        if message.from_user.id != ADMIN_ID:
            await message.answer("⛔️ Siz admin emassiz.")
            return
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(downloads) FROM users")
        total_downloads = cursor.fetchone()[0] or 0
        stats_text = f"👑 <b>ADMIN</b>\n━━━━━━━━━━━━━━━━━━━━━━\n👥 Foydalanuvchilar: <b>{total_users}</b>\n📥 Yuklamalar: <b>{total_downloads}</b>"
        await message.answer(stats_text, parse_mode=ParseMode.HTML)

# ================= ISHGA TUSHIRISH =================
async def run_bot(token: str):
    if not token or token == "None":
        return
    bot = Bot(token=token)
    dp = Dispatcher()
    register_handlers(dp, bot)
    print(f"✅ Bot ishga tushdi: {token[:10]}...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Botda xatolik: {e}")

async def main():
    tasks = []
    for token in [TOKEN_1, TOKEN_2, TOKEN_3]:
        if token and len(token) > 10:
            tasks.append(run_bot(token))
    if tasks:
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
