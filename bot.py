import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes, CallbackQueryHandler

# --- SOZLAMALAR ---
BOT_TOKEN = "8912386359:AAGLyUp8NKXsY6Cw9Gt1q6exiwDkUBmg1Q4"
KANAL_ID = -1003986913337
ADMIN_IDS = [5572567608]
DB_FILE = "kinolar.db"
MAJBURIY_KANALLAR = ["@pocoyo_gaming", "@pocoyo_pubg"]

KINO_NOMI, KINO_KOD, KINO_MSG_ID, KINO_TAVSIF, KINO_JANR, KINO_YIL = range(6)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MA'LUMOTLAR BAZASI BILAN ISHLASH ---
def db_init():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kinolar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT UNIQUE NOT NULL,
            nomi TEXT NOT NULL,
            tavsif TEXT,
            janr TEXT,
            yil TEXT,
            message_id INTEGER NOT NULL,
            ko_rishlar INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def kino_qoshish(kod, nomi, tavsif, janr, yil, message_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO kinolar (kod, nomi, tavsif, janr, yil, message_id) VALUES (?,?,?,?,?,?)",
                    (kod.upper(), nomi, tavsif, janr, yil, message_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def kino_topish(kod):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM kinolar WHERE kod = ?", (kod.upper(),))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE kinolar SET ko_rishlar = ko_rishlar + 1 WHERE kod = ?", (kod.upper(),))
        conn.commit()
    conn.close()
    if row:
        return {"id": row[0], "kod": row[1], "nomi": row[2], "tavsif": row[3],
                "janr": row[4], "yil": row[5], "message_id": row[6], "ko_rishlar": row[7]}
    return None

def kino_ochirish(kod):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM kinolar WHERE kod = ?", (kod.upper(),))
    ta = cur.rowcount
    conn.commit()
    conn.close()
    return ta > 0

def barcha_kinolar():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT kod, nomi, janr, yil, ko_rishlar FROM kinolar ORDER BY id DESC LIMIT 20")
    rows = cur.fetchall()
    conn.close()
    return rows

def kino_izlash(qidiruv):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT kod, nomi, janr, yil FROM kinolar WHERE nomi LIKE ? LIMIT 10", (f"%{qidiruv}%",))
    rows = cur.fetchall()
    conn.close()
    return rows

# --- OBUNANI TEKSHIRISH FUNKSIYASI ---
async def obuna_tekshir(bot, user_id):
    obuna_yok = []
    for kanal in MAJBURIY_KANALLAR:
        try:
            member = await bot.get_chat_member(kanal, user_id)
            if member.status in ["left", "kicked", "banned"]:
                obuna_yok.append(kanal)
        except Exception:
            obuna_yok.append(kanal)
    return obuna_yok

# --- START BUYRUG'I ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    obuna_yok = await obuna_tekshir(context.bot, user_id)
    
    if obuna_yok:
        tugmalar = []
        for kanal in obuna_yok:
            kanal_link = f"https://t.me/{kanal[1:]}"
            tugmalar.append([InlineKeyboardButton(f"📢 {kanal} ga obuna bo'ling", url=kanal_link)])
        tugmalar.append([InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="tekshir")])
        markup = InlineKeyboardMarkup(tugmalar)
        await update.message.reply_text(
            "⛔ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=markup
        )
        return
    
    await update.message.reply_text("🍿 <b>Iltimos, kino kodini kiriting:</b>", parse_mode="HTML")

# --- OBUNA BO'LDIM TUGMASI BOSILGANDA ---
async def tekshir_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    obuna_yok = await obuna_tekshir(context.bot, user_id)
    
    if obuna_yok:
        tugmalar = []
        for kanal in obuna_yok:
            kanal_link = f"https://t.me/{kanal[1:]}"
            tugmalar.append([InlineKeyboardButton(f"📢 {kanal} ga obuna bo'ling", url=kanal_link)])
        tugmalar.append([InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="tekshir")])
        markup = InlineKeyboardMarkup(tugmalar)
        await query.edit_message_text(
            "⛔ Hali barcha kanallarga obuna bo'lmadingiz! Iltimos, ro'yxatdan o'ting:",
            reply_markup=markup
        )
    else:
        # Aynan siz aytgan matn: obuna tasdiqlansa kod so'raydi
        await query.edit_message_text("✅ Obuna tasdiqlandi!\n\n🍿 <b>Iltimos, kino kodini kiriting:</b>", parse_mode="HTML")

# --- HELP BUYRUG'I ---
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>Yordam</b>\n\nKino kodini yuboring — video keladi.\n\n"
        "/kinolar — ro'yxat\n/search nom — qidirish", parse_mode="HTML")

# --- KINOLAR RO'YXATI ---
async def kinolar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    obuna_yok = await obuna_tekshir(context.bot, user_id)
    if obuna_yok:
        tugmalar = []
        for kanal in obuna_yok:
            kanal_link = f"https://t.me/{kanal[1:]}"
            tugmalar.append([InlineKeyboardButton(f"📢 {kanal} ga obuna bo'ling", url=kanal_link)])
        tugmalar.append([InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="tekshir")])
        await update.message.reply_text("⛔ Avval kanallarga obuna bo'ling:", reply_markup=InlineKeyboardMarkup(tugmalar))
        return
        
    kinolar = barcha_kinolar()
    if not kinolar:
        await update.message.reply_text("📭 Hozircha kinolar yo'q.")
        return
    xabar = "🎬 <b>Kinolar ro'yxati:</b>\n\n"
    for k in kinolar:
        xabar += f"🎥 <code>{k[0]}</code> — <b>{k[1]}</b>"
        if k[3]: xabar += f" ({k[3]})"
        if k[2]: xabar += f"\n   🎭 {k[2]}"
        xabar += f"\n   👁 {k[4]} marta\n\n"
    xabar += "👆 Kodni yuboring — kino keladi!"
    await update.message.reply_text(xabar, parse_mode="HTML")

# --- KINO QIDIRISH ---
async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Masalan: /search Inception")
        return
    natijalar = kino_izlash(" ".join(context.args))
    if not natijalar:
        await update.message.reply_text("🔍 Topilmadi.")
        return
    xabar = "🔍 <b>Natijalar:</b>\n\n"
    for k in natijalar:
        xabar += f"• <code>{k[0]}</code> — <b>{k[1]}</b>\n"
    await update.message.reply_text(xabar, parse_mode="HTML")

# --- KOD KUBUL QILISH VA KINONI KANALIDAN FORWARD QILISH ---
async def kino_kod_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    obuna_yok = await obuna_tekshir(context.bot, user_id)
    if obuna_yok:
        tugmalar = []
        for kanal in obuna_yok:
            kanal_link = f"https://t.me/{kanal[1:]}"
            tugmalar.append([InlineKeyboardButton(f"📢 {kanal} ga obuna bo'ling", url=kanal_link)])
        tugmalar.append([InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="tekshir")])
        await update.message.reply_text("⛔ Avval kanallarga obuna bo'ling:", reply_markup=InlineKeyboardMarkup(tugmalar))
        return
        
    matn = update.message.text.strip()
    kino = kino_topish(matn)
    if kino:
        caption = f"🎬 <b>{kino['nomi']}</b>"
        if kino['yil']: caption += f" ({kino['yil']})"
        if kino['janr']: caption += f"\n🎭 {kino['janr']}"
        if kino['tavsif']: caption += f"\n\n📖 {kino['tavsif']}"
        caption += f"\n\n🔢 Kod: <code>{kino['kod']}</code>"
        try:
            # Kanaldan kinoni foydalanuvchiga uzatish (Forward)
            await context.bot.forward_message(chat_id=update.effective_chat.id,
                                             from_chat_id=KANAL_ID, message_id=kino["message_id"])
            await update.message.reply_text(caption, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Forward xatosi: {e}")
            await update.message.reply_text(f"⚠️ Video yuklanmadi.\n\n{caption}", parse_mode="HTML")
    else:
        await update.message.reply_text(
            f"❌ <b>'{matn}'</b> kodi topilmadi.\n\n/kinolar — ro'yxatni ko'ring", parse_mode="HTML")

# --- ADMIN: KINO QO'SHISH (CONVERSATION) ---
async def add_kino_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Faqat adminlar uchun.")
        return ConversationHandler.END
    await update.message.reply_text("➕ <b>Yangi kino qo'shish</b>\n\nKino <b>nomini</b> yuboring:", parse_mode="HTML")
    return KINO_NOMI

async def add_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nomi"] = update.message.text.strip()
    await update.message.reply_text("Kino <b>kodini</b> yuboring (masalan: F001):", parse_mode="HTML")
    return KINO_KOD

async def add_kod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["kod"] = update.message.text.strip().upper()
    await update.message.reply_text("Kanal <b>message_id</b> sini yuboring:", parse_mode="HTML")
    return KINO_MSG_ID

async def add_msgid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["message_id"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Raqam kiriting!")
        return KINO_MSG_ID
    await update.message.reply_text("Janrini yuboring yoki /skip:")
    return KINO_JANR

async def add_janr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["janr"] = "" if update.message.text == "/skip" else update.message.text.strip()
    await update.message.reply_text("Yilini yuboring yoki /skip:")
    return KINO_YIL

async def add_yil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["yil"] = "" if update.message.text == "/skip" else update.message.text.strip()
    await update.message.reply_text("Tavsif yuboring yoki /skip:")
    return KINO_TAVSIF

async def add_tavsif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tavsif"] = "" if update.message.text == "/skip" else update.message.text.strip()
    d = context.user_data
    if kino_qoshish(d["kod"], d["nomi"], d["tavsif"], d["janr"], d["yil"], d["message_id"]):
        await update.message.reply_text(f"✅ <b>{d['nomi']}</b> qo'shildi!\nKod: <code>{d['kod']}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ <b>{d['kod']}</b> kodi allaqachon mavjud!", parse_mode="HTML")
    context.user_data.clear()
    return ConversationHandler.END

async def add_bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END

# --- ADMIN: KINONI O'CHIRISH ---
async def del_kino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Faqat adminlar uchun.")
        return
    if not context.args:
        await update.message.reply_text("Ishlatish: /del_kino KOD")
        return
    if kino_ochirish(context.args[0]):
        await update.message.reply_text(f"✅ {context.args[0]} o'chirildi.")
    else:
        await update.message.reply_text(f"❌ {context.args[0]} topilmadi.")

# --- ASOSIY ISHGA TUSHIRISH (WEBHOOK) ---
def main():
    db_init()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add_kino", add_kino_start)],
        states={
            KINO_NOMI:   [MessageHandler(filters.TEXT & ~filters.COMMAND, add_nomi)],
            KINO_KOD:    [MessageHandler(filters.TEXT & ~filters.COMMAND, add_kod)],
            KINO_MSG_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_msgid)],
            KINO_JANR:   [MessageHandler(filters.TEXT, add_janr)],
            KINO_YIL:    [MessageHandler(filters.TEXT, add_yil)],
            KINO_TAVSIF: [MessageHandler(filters.TEXT, add_tavsif)],
        },
        fallbacks=[CommandHandler("bekor", add_bekor)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("kinolar", kinolar_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("del_kino", del_kino))
    app.add_handler(CallbackQueryHandler(tekshir_callback, pattern="tekshir"))
    app.add_handler(add_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kino_kod_qabul))
    
    # PythonAnywhere uchun Webhook sozlamalari
    URL_PATH = f"bot/{BOT_TOKEN}"
    app.run_webhook(
        listen="127.0.0.1",
        port=8000,
        url_path=URL_PATH,
        webhook_url=f"https://davronov.pythonanywhere.com/{URL_PATH}"
    )

if __name__ == "__main__":
    main()
