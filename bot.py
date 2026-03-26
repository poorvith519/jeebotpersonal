import os
import json
import asyncio
from datetime import datetime, time
import pytz
from groq import Groq
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY   = os.environ["GROQ_API_KEY"]
IST            = pytz.timezone("Asia/Kolkata")
DATA_FILE      = "data.json"

groq_client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are JEE Sensei — a sharp, no-nonsense AI tutor exclusively for JEE Main & Advanced preparation.

Your personality:
- Concise and direct. Never waffle.
- Encouraging but brutally honest about weak areas.
- Use LaTeX-style notation where needed (e.g., x² not x^2).
- Break problems step-by-step when asked.

Your scope:
- Physics, Chemistry, Mathematics at JEE level ONLY.
- Mock test analysis, score tracking, weak area identification.
- Study planning and time management for JEE.
- Concept explanations, formula derivations, shortcuts/tricks.

When analysing mock scores:
- Calculate %ile estimate if total marks given.
- Identify subject-wise weak areas from the data.
- Give 2-3 concrete next steps, not vague advice.

Refuse to discuss anything unrelated to JEE prep politely but firmly.
Keep responses under 300 words unless solving a detailed problem."""

# ── Data persistence (JSON file) ──────────────────────────────────────────────
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}

def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user(data: dict, uid: str) -> dict:
    if uid not in data:
        data[uid] = {
            "name": "",
            "conversation": [],
            "mocks": [],
            "reminder_time": "07:00",
            "reminder_enabled": False
        }
    return data[uid]

# ── Groq AI call ──────────────────────────────────────────────────────────────
def ask_groq(conversation: list) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation[-20:]  # last 20 turns
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=600,
        temperature=0.6
    )
    return response.choices[0].message.content.strip()

# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid  = str(update.effective_user.id)
    user = get_user(data, uid)
    user["name"] = update.effective_user.first_name or "Aspirant"
    save_data(data)

    text = (
        f"🎯 *JEE Sensei activated, {user['name']}!*\n\n"
        "I'm your personal JEE prep agent. Here's what I can do:\n\n"
        "📚 `/ask` — Ask any JEE concept/problem\n"
        "📊 `/log` — Log a mock test score\n"
        "📈 `/analyse` — Analyse your mock performance\n"
        "⏰ `/reminder` — Set daily study reminder\n"
        "📋 `/mocks` — View all logged mocks\n"
        "🗑 `/clear` — Clear chat history\n"
        "❓ `/help` — Show this menu\n\n"
        "_Or just type anything — I'm always listening!_"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ── /help ─────────────────────────────────────────────────────────────────────
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, ctx)

# ── /log — Log mock score ─────────────────────────────────────────────────────
async def cmd_log(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    usage = (
        "📊 *Log a Mock Test*\n\n"
        "Format:\n"
        "`/log <mock_number> <phy_score> <chem_score> <math_score> <total_marks>`\n\n"
        "Example:\n"
        "`/log 15 68 82 54 300`\n\n"
        "_All scores are marks obtained. Total marks = max possible._"
    )
    args = ctx.args
    if len(args) != 5:
        await update.message.reply_text(usage, parse_mode="Markdown")
        return

    try:
        mock_no, phy, chem, math_, total = int(args[0]), int(args[1]), int(args[2]), int(args[3]), int(args[4])
    except ValueError:
        await update.message.reply_text("❌ All values must be numbers.\n\n" + usage, parse_mode="Markdown")
        return

    scored = phy + chem + math_
    pct    = round(scored / total * 100, 1)

    data = load_data()
    uid  = str(update.effective_user.id)
    user = get_user(data, uid)
    user["mocks"].append({
        "mock": mock_no,
        "date": datetime.now(IST).strftime("%d %b %Y"),
        "phy": phy, "chem": chem, "math": math_,
        "total_scored": scored, "total_max": total, "pct": pct
    })
    save_data(data)

    msg = (
        f"✅ *Mock {mock_no} logged!*\n\n"
        f"Physics : {phy}\n"
        f"Chemistry: {chem}\n"
        f"Maths   : {math_}\n"
        f"─────────────────\n"
        f"Total   : {scored}/{total} ({pct}%)\n\n"
        f"_Type /analyse for full performance breakdown._"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /mocks — View all mocks ───────────────────────────────────────────────────
async def cmd_mocks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid  = str(update.effective_user.id)
    user = get_user(data, uid)
    mocks = user["mocks"]

    if not mocks:
        await update.message.reply_text("No mocks logged yet. Use `/log` to add one.", parse_mode="Markdown")
        return

    lines = ["📋 *All Mock Scores*\n"]
    for m in mocks:
        lines.append(
            f"Mock {m['mock']} ({m['date']}): "
            f"P={m['phy']} C={m['chem']} M={m['math']} → "
            f"{m['total_scored']}/{m['total_max']} ({m['pct']}%)"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ── /analyse — AI-powered analysis ───────────────────────────────────────────
async def cmd_analyse(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid  = str(update.effective_user.id)
    user = get_user(data, uid)
    mocks = user["mocks"]

    if len(mocks) < 2:
        await update.message.reply_text(
            "Log at least 2 mocks first using `/log` to get a meaningful analysis.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("🔍 Analysing your mock data...", parse_mode="Markdown")

    # Build analysis prompt
    mock_summary = "\n".join([
        f"Mock {m['mock']} ({m['date']}): Phy={m['phy']}, Chem={m['chem']}, Math={m['math']}, "
        f"Total={m['total_scored']}/{m['total_max']} ({m['pct']}%)"
        for m in mocks
    ])

    prompt = (
        f"Analyse these JEE mock test results for the student:\n\n{mock_summary}\n\n"
        "Provide:\n"
        "1. Overall trend (improving/declining/stagnant)\n"
        "2. Subject-wise strengths and weaknesses\n"
        "3. Consistency analysis\n"
        "4. Top 3 concrete action items for the next week\n"
        "Be specific, concise and brutally honest."
    )

    user["conversation"].append({"role": "user", "content": prompt})
    reply = ask_groq(user["conversation"])
    user["conversation"].append({"role": "assistant", "content": reply})
    save_data(data)

    await update.message.reply_text(f"📈 *Performance Analysis*\n\n{reply}", parse_mode="Markdown")

# ── /reminder — Set daily reminder ───────────────────────────────────────────
async def cmd_reminder(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("5:00 AM", callback_data="rem_05:00"),
         InlineKeyboardButton("6:00 AM", callback_data="rem_06:00"),
         InlineKeyboardButton("7:00 AM", callback_data="rem_07:00")],
        [InlineKeyboardButton("8:00 AM", callback_data="rem_08:00"),
         InlineKeyboardButton("9:00 AM", callback_data="rem_09:00"),
         InlineKeyboardButton("10:00 AM", callback_data="rem_10:00")],
        [InlineKeyboardButton("❌ Disable Reminder", callback_data="rem_disable")]
    ]
    await update.message.reply_text(
        "⏰ *Set Daily Reminder*\n\nChoose your morning reminder time (IST):",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_reminder_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    uid  = str(query.from_user.id)
    user = get_user(data, uid)

    if query.data == "rem_disable":
        user["reminder_enabled"] = False
        save_data(data)
        await query.edit_message_text("❌ Daily reminder disabled.")
        return

    t = query.data.replace("rem_", "")
    user["reminder_time"]    = t
    user["reminder_enabled"] = True
    user["chat_id"]          = query.message.chat_id
    save_data(data)

    await query.edit_message_text(
        f"✅ Daily reminder set for *{t} IST*!\n\nI'll motivate you every morning. 🔥",
        parse_mode="Markdown"
    )

    # Schedule the job
    _schedule_reminder(ctx.application, uid, t, query.message.chat_id)

def _schedule_reminder(app, uid: str, t: str, chat_id: int):
    hour, minute = map(int, t.split(":"))
    job_name = f"reminder_{uid}"
    # Remove existing job if any
    current_jobs = app.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()
    # Add new daily job
    app.job_queue.run_daily(
        _send_reminder,
        time=time(hour=hour, minute=minute, tzinfo=IST),
        name=job_name,
        data={"uid": uid, "chat_id": chat_id}
    )

async def _send_reminder(ctx: ContextTypes.DEFAULT_TYPE):
    job  = ctx.job
    uid  = job.data["uid"]
    chat_id = job.data["chat_id"]

    data = load_data()
    user = get_user(data, uid)
    mocks = user["mocks"]

    if mocks:
        last = mocks[-1]
        context_line = f"Your last mock was Mock {last['mock']} — {last['total_scored']}/{last['total_max']} ({last['pct']}%)."
    else:
        context_line = "You haven't logged any mocks yet."

    prompt = (
        f"Generate a short, punchy JEE morning motivation message (max 4 lines). "
        f"Student context: {context_line} JEE 2026 is approaching. "
        f"Make it feel personal and urgent, not generic. No emojis overload."
    )
    motivation = ask_groq([{"role": "user", "content": prompt}])

    await ctx.bot.send_message(
        chat_id=chat_id,
        text=f"🌅 *Good Morning, {user['name']}!*\n\n{motivation}",
        parse_mode="Markdown"
    )

# ── /clear ────────────────────────────────────────────────────────────────────
async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid  = str(update.effective_user.id)
    user = get_user(data, uid)
    user["conversation"] = []
    save_data(data)
    await update.message.reply_text("🗑 Chat history cleared. Fresh start!")

# ── General message handler (AI chat) ────────────────────────────────────────
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    if not user_text:
        return

    data = load_data()
    uid  = str(update.effective_user.id)
    user = get_user(data, uid)

    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    user["conversation"].append({"role": "user", "content": user_text})
    reply = ask_groq(user["conversation"])
    user["conversation"].append({"role": "assistant", "content": reply})

    # Keep conversation history manageable
    if len(user["conversation"]) > 40:
        user["conversation"] = user["conversation"][-40:]

    save_data(data)
    await update.message.reply_text(reply, parse_mode="Markdown")

# ── Restore reminders on startup ─────────────────────────────────────────────
async def restore_reminders(app: Application):
    data = load_data()
    for uid, user in data.items():
        if user.get("reminder_enabled") and user.get("chat_id"):
            _schedule_reminder(app, uid, user["reminder_time"], user["chat_id"])

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("log",      cmd_log))
    app.add_handler(CommandHandler("mocks",    cmd_mocks))
    app.add_handler(CommandHandler("analyse",  cmd_analyse))
    app.add_handler(CommandHandler("reminder", cmd_reminder))
    app.add_handler(CommandHandler("clear",    cmd_clear))
    app.add_handler(CallbackQueryHandler(handle_reminder_callback, pattern="^rem_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Restore reminders after startup
    app.job_queue.run_once(lambda ctx: asyncio.create_task(restore_reminders(app)), when=2)

    print("🤖 JEE Sensei bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
