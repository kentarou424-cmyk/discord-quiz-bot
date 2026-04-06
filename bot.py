import discord
import anthropic
import os
from datetime import datetime
import pytz
from discord.ext import tasks

# ===== 設定 =====
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CHANNEL_ID = 1490180329347219657

SUBJECTS = ["健康保険法", "労働基準法", "労働安全衛生法"]
JST = pytz.timezone("Asia/Tokyo")

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

today_questions = None
today_answers = None

def get_today_subject():
    day = datetime.now(JST).weekday()
    return SUBJECTS[day % len(SUBJECTS)]

def generate_questions(subject):
    message = claude.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""社労士試験の{subject}から○×問題を3問作ってください。

以下の形式で出力してください：

【問題】
Q1. （問題文）
Q2. （問題文）
Q3. （問題文）

【解答・解説】
A1. ○or× 　（解説文）
A2. ○or× 　（解説文）
A3. ○or× 　（解説文）

問題文と解答解説は必ず分けて書いてください。
難易度は本試験レベルでお願いします。"""
        }]
    )
    full_text = message.content[0].text
    if "【解答・解説】" in full_text:
        parts = full_text.split("【解答・解説】")
        questions_part = parts[0].replace("【問題】", "").strip()
        answers_part = parts[1].strip()
    else:
        questions_part = full_text
        answers_part = "解説を生成できませんでした。"
    return questions_part, answers_part

@client.event
async def on_ready():
    print(f"✅ {client.user} としてログインしました")
    quiz_loop.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content == "!テスト":
        await send_questions(message.channel)

async def send_questions(channel=None):
    global today_questions, today_answers
    if channel is None:
        channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print("❌ チャンネルが見つかりません")
        return
    subject = get_today_subject()
    print(f"📝 {subject}の問題を生成中...")
    try:
        questions, answers = generate_questions(subject)
        today_questions = questions
        today_answers = answers
        await channel.send(
            f"🌅 **おはようございます！今日の社労士○×問題です**\n"
            f"📚 科目：**{subject}**\n\n"
            f"{questions}\n\n"
            f"⏰ *10分後に解答・解説を送ります！*"
        )
        print("✅ 問題を送信しました")
    except Exception as e:
        print(f"❌ エラー: {e}")
        await channel.send("問題の生成に失敗しました。しばらくお待ちください。")

async def send_answers(channel=None):
    global today_answers
    if channel is None:
        channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        return
    if today_answers:
        await channel.send(
            f"✅ **解答・解説です！**\n\n"
            f"{today_answers}\n\n"
            f"💪 今日もお疲れ様でした！明日もがんばりましょう！"
        )
        print("✅ 解説を送信しました")

@tasks.loop(seconds=30)
async def quiz_loop():
    now = datetime.now(JST)
    if not hasattr(quiz_loop, 'sent_question'):
        quiz_loop.sent_question = False
    if not hasattr(quiz_loop, 'sent_answer'):
        quiz_loop.sent_answer = False
    if not hasattr(quiz_loop, 'last_date'):
        quiz_loop.last_date = now.date()
    if quiz_loop.last_date != now.date():
        quiz_loop.sent_question = False
        quiz_loop.sent_answer = False
        quiz_loop.last_date = now.date()
    if now.weekday() >= 5:
        return
    if now.hour == 7 and now.minute == 45 and not quiz_loop.sent_question:
        await send_questions()
        quiz_loop.sent_question = True
    if now.hour == 7 and now.minute == 55 and not quiz_loop.sent_answer:
        await send_answers()
        quiz_loop.sent_answer = True

client.run(DISCORD_TOKEN)
