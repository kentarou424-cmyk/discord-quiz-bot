import discord
import anthropic
import asyncio
from datetime import datetime
import pytz

# ===== 設定 =====
DISCORD_TOKEN = "ここにDiscordのBotトークンを貼り付ける"
ANTHROPIC_API_KEY = "ここにAnthropicのAPIキーを貼り付ける"
CHANNEL_ID = 1490180329347219657

# 科目ローテーション
SUBJECTS = ["健康保険法", "労働基準法", "労働安全衛生法"]

# タイムゾーン（日本時間）
JST = pytz.timezone("Asia/Tokyo")

# ===== Anthropic クライアント =====
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ===== Discord クライアント =====
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 今日の問題を保存する変数
today_questions = None
today_answers = None

def get_today_subject():
    """今日の曜日に合わせて科目を返す"""
    day = datetime.now(JST).weekday()  # 0=月, 1=火, 2=水...
    return SUBJECTS[day % len(SUBJECTS)]

def generate_questions(subject):
    """Claude APIで問題を生成する"""
    message = claude.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        messages=[
            {
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
            }
        ]
    )
    
    full_text = message.content[0].text
    
    # 【問題】と【解答・解説】で分割
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
    
    # テスト用コマンド（「!テスト」と送ると即座に問題が出る）
    if message.content == "!テスト":
        await send_questions(message.channel)

async def send_questions(channel=None):
    """問題を送信する"""
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
    """解説を送信する"""
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

import threading

def quiz_loop_thread():
    """毎日8:00と8:10に問題・解説を送信するループ"""
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    
    sent_question_today = False
    sent_answer_today = False
    
    while True:
        now = datetime.now(JST)
        
        # 日付が変わったらリセット
        if now.hour == 0 and now.minute == 0:
            sent_question_today = False
            sent_answer_today = False
        
        # 8:00に問題送信
        if now.hour == 8 and now.minute == 0 and not sent_question_today:
            loop.run_until_complete(send_questions())
            sent_question_today = True
        
        # 8:10に解説送信
        if now.hour == 8 and now.minute == 10 and not sent_answer_today:
            loop.run_until_complete(send_answers())
            sent_answer_today = True
        
        asyncio.sleep(30)  # 30秒ごとにチェック

from discord.ext import tasks

@tasks.loop(seconds=30)
async def quiz_loop():
    """毎日8:00と8:10に問題・解説を送信"""
    global sent_question_today, sent_answer_today
    
    now = datetime.now(JST)
    
    # 日付が変わったらリセット
    if now.hour == 0 and now.minute == 0:
        quiz_loop.sent_question = False
        quiz_loop.sent_answer = False
    
    # 属性がなければ初期化
    if not hasattr(quiz_loop, 'sent_question'):
        quiz_loop.sent_question = False
    if not hasattr(quiz_loop, 'sent_answer'):
        quiz_loop.sent_answer = False
    if not hasattr(quiz_loop, 'last_date'):
        quiz_loop.last_date = now.date()
    
    # 日付変わりでリセット
    if quiz_loop.last_date != now.date():
        quiz_loop.sent_question = False
        quiz_loop.sent_answer = False
        quiz_loop.last_date = now.date()
    
    # 平日のみ（0=月曜〜4=金曜）
    if now.weekday() >= 5:
        return

    # 7:45に問題送信
    if now.hour == 7 and now.minute == 45 and not quiz_loop.sent_question:
        await send_questions()
        quiz_loop.sent_question = True
    
    # 7:55に解説送信
    if now.hour == 7 and now.minute == 55 and not quiz_loop.sent_answer:
        await send_answers()
        quiz_loop.sent_answer = True

client.run(DISCORD_TOKEN)
