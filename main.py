import os
import logging
import random
import json
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

ASK_PIN, ASK_LUCKY_NUMBER, ASK_REPLAY = range(3)

user_data = {}
revenue_data = {"total_revenue": 0, "reward_pool": 0, "players": []}

def load_data():
    global user_data, revenue_data
    if os.path.exists("user_data.json"):
        with open("user_data.json", "r") as f:
            user_data = json.load(f)
    if os.path.exists("revenue_data.json"):
        with open("revenue_data.json", "r") as f:
            revenue_data = json.load(f)

def save_data():
    with open("user_data.json", "w") as f:
        json.dump(user_data, f)
    with open("revenue_data.json", "w") as f:
        json.dump(revenue_data, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data[user_id] = {"paid": False}
    await update.message.reply_text("Welcome to the Game of Chance! Please enter your PIN to pay KES 50.")
    return ASK_PIN

async def handle_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data[user_id]["paid"] = True
    revenue_data["total_revenue"] += 50
    revenue_data["reward_pool"] += 50
    revenue_data["players"].append(user_id)
    save_data()
    await update.message.reply_text("Payment received! Choose your lucky number (1, 2, or 3):")
    return ASK_LUCKY_NUMBER

async def handle_lucky_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    try:
        chosen_number = int(update.message.text)
        if chosen_number not in [1, 2, 3]:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Invalid number. Please choose 1, 2, or 3.")
        return ASK_LUCKY_NUMBER

    winning_number = random.randint(1, 3)
    if chosen_number == winning_number:
        await update.message.reply_text("🎉 Congratulations! You won!")
    else:
        await update.message.reply_text("Sorry, you didn't win. Do you want to play again? (yes/no)")
        return ASK_REPLAY

    await check_rewards(update)
    return ConversationHandler.END

async def handle_replay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "yes":
        await update.message.reply_text("Please enter your PIN to pay KES 50.")
        return ASK_PIN
    else:
        await update.message.reply_text("Thanks for playing!")
        return ConversationHandler.END

async def check_rewards(update: Update):
    if revenue_data["reward_pool"] >= 5000:
        recipients = random.sample(revenue_data["players"], min(len(revenue_data["players"]), random.randint(2, 10)))
        total_reward = 0
        for user_id in recipients:
            reward = random.choice([200, 400, 500, 1000])
            if total_reward + reward <= 2000:
                total_reward += reward
                await update.message.reply_text(f"User {user_id} receives KES {reward} as a reward!")
        revenue_data["reward_pool"] -= 2000
        revenue_data["players"] = []
        save_data()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Game cancelled.")
    return ConversationHandler.END

async def run_bot():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    load_data()

    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN environment variable not set.")

    app = ApplicationBuilder().token(bot_token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pin)],
            ASK_LUCKY_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_lucky_number)],
            ASK_REPLAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_replay)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(run_bot())
