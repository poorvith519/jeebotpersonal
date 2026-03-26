# 🎯 JEE Sensei — Telegram AI Bot

Your personal JEE 2026 prep agent. Free forever.

## Features
- 🤖 AI chat for JEE concepts, problems, shortcuts (Groq LLaMA 3)
- 📊 Log mock test scores (Physics / Chemistry / Maths)
- 📈 AI-powered performance analysis & weak area detection
- ⏰ Daily morning motivational reminders (IST)
- 📋 View full mock history anytime

---

## Setup Guide (Step by Step)

### Step 1 — Get your Telegram Bot Token
1. Open Telegram → search `@BotFather`
2. Send `/newbot`
3. Give it a name (e.g. `JEE Sensei`) and username (e.g. `jeesensei_bot`)
4. Copy the **token** BotFather gives you

### Step 2 — Get your FREE Groq API Key
1. Go to https://console.groq.com
2. Sign up (free, no credit card)
3. Go to **API Keys** → Create new key
4. Copy the key

### Step 3 — Deploy to Railway (Free)
1. Go to https://railway.app → Sign up with GitHub (free)
2. Click **New Project** → **Deploy from GitHub repo**
3. Push this folder to a GitHub repo first:
   ```bash
   git init
   git add .
   git commit -m "JEE Sensei bot"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/jee-sensei-bot.git
   git push -u origin main
   ```
4. In Railway, select your repo
5. Go to **Variables** tab → Add:
   - `TELEGRAM_TOKEN` = your token from Step 1
   - `GROQ_API_KEY` = your key from Step 2
6. Railway auto-deploys. Done! 🎉

---

## Commands
| Command | Description |
|---------|-------------|
| `/start` | Welcome + menu |
| `/log 15 68 82 54 300` | Log Mock 15 scores |
| `/mocks` | View all logged mocks |
| `/analyse` | AI analysis of performance |
| `/reminder` | Set daily reminder time |
| `/clear` | Clear conversation history |
| Just type anything | Chat with JEE Sensei |

## Log Format
`/log <mock_number> <physics> <chemistry> <maths> <max_marks>`

Example: `/log 15 68 82 54 300`
- Mock 15, Physics=68, Chemistry=82, Maths=54, out of 300 total

---

## Notes
- Data saved in `data.json` locally. On Railway, data resets on redeploy.
- For persistent storage, upgrade to Railway's free Postgres or use a free MongoDB Atlas cluster.
- Groq free tier: 14,400 requests/day — more than enough for personal use.
