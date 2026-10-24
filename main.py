import asyncio
import logging
import os
import sqlite3
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
                  (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, joined_at TEXT, downloads INTEGER DEFAULT 0, lang TEXT DEFAULT 'uz')''')
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
    return res[0] if res and res[0] else 'uz'

def set_user_lang(user_id, lang):
    cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()

# ================= TILLAR =================
TEXTS = {
    'uz': {
        'welcome': "✨ <b>Assalomu alaykum, {name}!</b>\n\n🤖 <b>Premium Media Yuklovchi</b> botiga xush kelibsiz.\n\nDavom etish uchun iltimos, avval rasmiy kanalimizga a'zo bo'ling.",
        'btn_sub': "📢 Kanalga a'zo bo'lish",
        'btn_check': "✅ Obunani tekshirish",
        'not_subbed': "❌ Siz hali kanalga a'zo bo'lmadingiz!",
        'sub_ok': "🎉 <b>Obuna muvaffaqiyatli tasdiqlandi!</b>\n\nEndi botning barcha imkoniyatlaridan bemalol foydalanishingiz mumkin.",
        'menu': "👋 <b>Xush kelibsiz, {name}!</b>\n\n👇 Quyidagi xizmatlardan birini tanlang:\n━━━━━━━━━━━━━━━━━━━━━━",
        'btn_music': "🎵 Musiqa yuklash",
        'btn_video': "🎬 Video yuklash",
        'btn_lang': "🌐 Tilni o'zgartirish",
        'btn_stats': "📊 Mening statistikam",
        'btn_back': "⬅️ Orqaga",
        'ask_music': "🎧 <b>Musiqa nomini yoki ijrochi ismini yozing:</b>\n\n<i>Masalan: Shahzoda - Kechalar</i>",
        'ask_video': "🔗 <b>Video havolasini yuboring:</b>\n\n<i>Instagram, YouTube, TikTok va boshqa havolalar.</i>",
        'loading': "⏳ <i>Jarayon boshlandi, iltimos kuting...</i>",
        'dl_error': "❌ <b>Xatolik yuz berdi.</b>\nHavola noto'g'ri yoki video mavjud emas.",
        'file_too_large': "⚠️ <b>Fayl hajmi juda katta!</b>\nTelegram botlari 50MB dan katta fayllarni yubora olmaydi.",
        'nothing_found': "❌ <b>Afsuski, hech narsa topilmadi.</b>",
        'must_sub': "❗️ <b>Botdan foydalanish uchun avval kanalga a'zo bo'ling!</b>",
        'lang_changed': "✅ <b>Til muvaffaqiyatli o'zgartirildi: O'zbekcha</b>",
        'my_stats': "📊 <b>Sizning statistikangiz:</b>\n\n🆔 ID: <code>{id}</code>\n📥 Yuklagan fayllaringiz: <b>{downloads} ta</b>",
    },
    'ru': {
        'welcome': "✨ <b>Здравствуйте, {name}!</b>\n\n🤖 Добро пожаловать в <b>Premium Media Downloader</b>.\n\nЧтобы продолжить, подпишитесь на наш канал.",
        'btn_sub': "📢 Подписаться",
        'btn_check': "✅ Проверить",
        'not_subbed': "❌ Вы еще не подписались на канал!",
        'sub_ok': "🎉 <b>Подписка подтверждена!</b>\n\nТеперь вам доступны все функции бота.",
        'menu': "👋 <b>Добро пожаловать, {name}!</b>\n\n👇 Выберите услугу:\n━━━━━━━━━━━━━━━━━━━━━━",
        'btn_music': "🎵 Скачать музыку",
        'btn_video': "🎬 Скачать видео",
        'btn_lang': "🌐 Сменить язык",
        'btn_stats': "📊 Моя статистика",
        'btn_back': "⬅️ Назад",
        'ask_music': "🎧 <b>Введите название песни или исполнителя:</b>\n\n<i>Например: Imagine Dragons - Believer</i>",
        'ask_video': "🔗 <b>Отправьте ссылку на видео:</b>\n\n<i>Instagram, YouTube, TikTok и др.</i>",
        'loading': "⏳ <i>Загрузка началась, пожалуйста, подождите...</i>",
        'dl_error': "❌ <b>Ошибка.</b>\nНеверная ссылка или видео недоступно.",
        'file_too_large': "⚠️ <b>Файл слишком большой!</b>\nБоты Telegram не могут отправлять файлы больше 50MB.",
        'nothing_found': "❌ <b>К сожалению, ничего не найдено.</b>",
        'must_sub': "❗️ <b>Сначала подпишитесь на канал!</b>",
        'lang_changed': "✅ <b>Язык изменен: Русский</b>",
        'my_stats': "📊 <b>Ваша статистика:</b>\n\n🆔 ID: <code>{id}</code>\n📥 Скачано файлов: <b>{downloads}</b>",
    }
}

# ================= MAJBURIY OBUNA =================
async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception as e:
        logging.error(f"Obuna tekshirishda xato: {e}")
        return False
    return False

# ================= HOLATLAR =================
class BotStates(StatesGroup):
    waiting_for_video = State()
    waiting_for_music = State()
    waiting_for_broadcast = State()

# ================= YUKLASH FUNKSIYALARI =================
def sync_download_video(url, user_id):
    os.makedirs("downloads", exist_ok=True)
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': f'downloads/{user_id}_%(title)s.%(ext)s',
        'restrictfilenames': True,
        'quiet': True,
        'no_warnings': True,
        'max_filesize': 50000000,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return info, filename

def sync_download_music(query, user_id):
    os.makedirs("downloads", exist_ok=True)
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': f'downloads/{user_id}_%(title)s.%(ext)s',
        'restrictfilenames': True,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=True)['entries'][0]
        filename = ydl.prepare_filename(info)
        return info, filename

# ================= HANDLERLAR =================
def register_handlers(dp: Dispatcher, bot: Bot):
    router = Router()
    dp.include_router(router)

    def get_main_menu(user_id, name):
        lang = get_user_lang(user_id)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=TEXTS[lang]['btn_video'], callback_data="video_download"),
             InlineKeyboardButton(text=TEXTS[lang]['btn_music'], callback_data="music_download")],
            [InlineKeyboardButton(text=TEXTS[lang]['btn_stats'], callback_data="my_stats"),
             InlineKeyboardButton(text=TEXTS[lang]['btn_lang'], callback_data="change_lang")],
            [InlineKeyboardButton(text="📢 Kanalimiz", url=CHANNEL_URL)]
        ])

    @router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        await state.clear()
        user_id = message.from_user.id
        first_name = message.from_user.first_name or "Foydalanuvchi"
        add_user(user_id, first_name, message.from_user.username)
        lang = get_user_lang(user_id)
        
        if not await check_subscription(bot, user_id):
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=TEXTS[lang]['btn_sub'], url=CHANNEL_URL)],
                [InlineKeyboardButton(text=TEXTS[lang]['btn_check'], callback_data="check_sub")]
            ])
            await message.answer(TEXTS[lang]['welcome'].format(name=first_name), reply_markup=kb, parse_mode=ParseMode.HTML)
            return

        await message.answer(TEXTS[lang]['menu'].format(name=first_name), reply_markup=get_main_menu(user_id, first_name), parse_mode=ParseMode.HTML)

    @router.message(Command("id"))
    async def get_id(message: Message):
        await message.answer(f"🆔 Sizning Telegram ID'ingiz:\n<code>{message.from_user.id}</code>", parse_mode=ParseMode.HTML)

    @router.callback_query(F.data == "check_sub")
    async def check_sub_callback(callback: CallbackQuery):
        lang = get_user_lang(callback.from_user.id)
        if await check_subscription(bot, callback.from_user.id):
            await callback.message.edit_text(TEXTS[lang]['sub_ok'], reply_markup=get_main_menu(callback.from_user.id, callback.from_user.first_name), parse_mode=ParseMode.HTML)
        else:
            await callback.answer(TEXTS[lang]['not_subbed'], show_alert=True)
        await callback.answer()

    @router.callback_query(F.data == "main_menu")
    async def back_to_menu(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        lang = get_user_lang(callback.from_user.id)
        await callback.message.edit_text(TEXTS[lang]['menu'].format(name=callback.from_user.first_name), reply_markup=get_main_menu(callback.from_user.id, callback.from_user.first_name), parse_mode=ParseMode.HTML)
        await callback.answer()

    @router.callback_query(F.data == "my_stats")
    async def my_stats(callback: CallbackQuery):
        lang = get_user_lang(callback.from_user.id)
        cursor.execute("SELECT downloads FROM users WHERE user_id = ?", (callback.from_user.id,))
        dl = cursor.fetchone()[0]
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=TEXTS[lang]['btn_back'], callback_data="main_menu")]])
        await callback.message.edit_text(TEXTS[lang]['my_stats'].format(id=callback.from_user.id, downloads=dl), reply_markup=kb, parse_mode=ParseMode.HTML)
        await callback.answer()

    @router.callback_query(F.data == "change_lang")
    async def change_lang_menu(callback: CallbackQuery):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
             InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="main_menu")]
        ])
        await callback.message.edit_text("🌐 <b>Tilni tanlang / Выберите язык:</b>", reply_markup=kb, parse_mode=ParseMode.HTML)
        await callback.answer()

    @router.callback_query(F.data.startswith("lang_"))
    async def set_lang_callback(callback: CallbackQuery):
        lang_code = callback.data.split("_")[1]
        set_user_lang(callback.from_user.id, lang_code)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=TEXTS[lang_code]['btn_back'], callback_data="main_menu")]])
        await callback.message.edit_text(TEXTS[lang_code]['lang_changed'], reply_markup=kb, parse_mode=ParseMode.HTML)
        await callback.answer()

    @router.callback_query(F.data == "video_download")
    async def video_download(callback: CallbackQuery, state: FSMContext):
        lang = get_user_lang(callback.from_user.id)
        if not await check_subscription(bot, callback.from_user.id):
            await callback.answer(TEXTS[lang]['must_sub'], show_alert=True)
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=TEXTS[lang]['btn_back'], callback_data="main_menu")]])
        await callback.message.edit_text(TEXTS[lang]['ask_video'], reply_markup=kb, parse_mode=ParseMode.HTML)
        await state.set_state(BotStates.waiting_for_video)
        await callback.answer()

    @router.callback_query(F.data == "music_download")
    async def music_download(callback: CallbackQuery, state: FSMContext):
        lang = get_user_lang(callback.from_user.id)
        if not await check_subscription(bot, callback.from_user.id):
            await callback.answer(TEXTS[lang]['must_sub'], show_alert=True)
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=TEXTS[lang]['btn_back'], callback_data="main_menu")]])
        await callback.message.edit_text(TEXTS[lang]['ask_music'], reply_markup=kb, parse_mode=ParseMode.HTML)
        await state.set_state(BotStates.waiting_for_music)
        await callback.answer()

    @router.message(BotStates.waiting_for_video)
    async def handle_video(message: Message, state: FSMContext):
        text = message.text.strip()
        lang = get_user_lang(message.from_user.id)
        
        if not text.startswith("http"):
            await message.answer("❌ Iltimos, to'g'ri havola yuboring.")
            return

        status_msg = await message.answer(TEXTS[lang]['loading'], parse_mode=ParseMode.HTML)
        await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
        
        filename = None
        try:
            info, filename = await asyncio.to_thread(sync_download_video, text, message.from_user.id)
            
            if os.path.getsize(filename) > 50 * 1024 * 1024:
                await status_msg.edit_text(TEXTS[lang]['file_too_large'], parse_mode=ParseMode.HTML)
            else:
                await message.answer_video(FSInputFile(filename), caption=f"🎬 <b>{info.get('title', 'Video')}</b>", parse_mode=ParseMode.HTML)
                increment_download(message.from_user.id)
                await status_msg.delete()
                
        except Exception as e:
            await status_msg.edit_text(f"{TEXTS[lang]['dl_error']}", parse_mode=ParseMode.HTML)
        finally:
            if filename and os.path.exists(filename):
                try: os.remove(filename)
                except: pass
            await state.clear()

    @router.message(BotStates.waiting_for_music)
    async def handle_music(message: Message, state: FSMContext):
        text = message.text.strip()
        lang = get_user_lang(message.from_user.id)
        
        status_msg = await message.answer(TEXTS[lang]['loading'], parse_mode=ParseMode.HTML)
        await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VOICE)
        
        filename = None
        try:
            info, filename = await asyncio.to_thread(sync_download_music, text, message.from_user.id)
            
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
                increment_download(message.from_user.id)
                await status_msg.delete()
                
        except Exception as e:
            logging.error(f"Musiqa yuklashda xato: {e}")
            await status_msg.edit_text(f"{TEXTS[lang]['nothing_found']}", parse_mode=ParseMode.HTML)
        finally:
            if filename and os.path.exists(filename):
                try: os.remove(filename)
                except: pass
            await state.clear()

    @router.message(Command("admin"))
    async def admin_panel(message: Message, state: FSMContext):
        if message.from_user.id != ADMIN_ID:
            await message.answer("⛔️ Siz admin emassiz.")
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(downloads) FROM users")
        total_downloads = cursor.fetchone()[0] or 0

        stats_text = (
            f"👑 <b>ADMIN PANEL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
            f"📥 Jami yuklamalar: <b>{total_downloads}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 Barcha foydalanuvchilarga xabar yuborish uchun quyidagi tugmani bosing."
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Xabar tarqatish (Broadcast)", callback_data="admin_broadcast")]
        ])
        await message.answer(stats_text, reply_markup=kb, parse_mode=ParseMode.HTML)

    @router.callback_query(F.data == "admin_broadcast", F.from_user.id == ADMIN_ID)
    async def start_broadcast(callback: CallbackQuery, state: FSMContext):
        await callback.message.edit_text("✍️ Tarqatmoqchi bo'lgan xabaringizni yuboring (Rasm, video yoki matn):")
        await state.set_state(BotStates.waiting_for_broadcast)
        await callback.answer()

    @router.message(BotStates.waiting_for_broadcast, F.from_user.id == ADMIN_ID)
    async def process_broadcast(message: Message, state: FSMContext):
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        
        status_msg = await message.answer("⏳ Xabar tarqatilmoqda...")
        success, failed = 0, 0
        
        for user in users:
            try:
                await message.copy_to(chat_id=user[0])
                success += 1
                await asyncio.sleep(0.05)
            except:
                failed += 1
                
        await status_msg.edit_text(f"✅ <b>Tarqatish yakunlandi!</b>\n\nMuvaffaqiyatli: {success}\nXatolik: {failed}", parse_mode=ParseMode.HTML)
        await state.clear()

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
