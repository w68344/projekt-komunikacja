from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

TOKEN = "8055838402:AAE6PASMcqUbDmWd0Q6yMqNYPwHerbcCj1E"

# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Сказать привет", callback_data="say_hello")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Нажми кнопку:", reply_markup=reply_markup)

# Обработка нажатия кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "say_hello":
        await query.edit_message_text("Привет!")

# Запуск бота



if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()
