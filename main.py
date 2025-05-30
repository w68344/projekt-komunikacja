from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = "8055838402:AAE6PASMcqUbDmWd0Q6yMqNYPwHerbcCj1E"

# Логины и пароли (можно заменить на базу)
ADMIN_CREDENTIALS = {
    "admin": "1234"
}

# Хранилище состояний
user_states = {}

# Главное меню (выбор роли)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Зритель", callback_data="role_viewer")],
        [InlineKeyboardButton("Администратор", callback_data="role_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери роль:", reply_markup=reply_markup)
    user_states[update.effective_user.id] = "start"

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    # Выбор роли
    if query.data == "role_viewer":
        await query.edit_message_text("Привет, зритель!")
        user_states[user_id] = "viewer"

    elif query.data == "role_admin":
        user_states[user_id] = "awaiting_login"
        await query.edit_message_text(
            "Введите логин и пароль через пробел (например: `admin 1234`):",
            parse_mode="Markdown"
        )

    elif query.data == "logout":
        user_states[user_id] = "start"
        keyboard = [
            [InlineKeyboardButton("Зритель", callback_data="role_viewer")],
            [InlineKeyboardButton("Администратор", callback_data="role_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Вы вышли. Выбери роль:", reply_markup=reply_markup)

# Обработка текстовых сообщений (логин/пароль)
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Ожидание логина/пароля
    if user_states.get(user_id) == "awaiting_login":
        try:
            login, password = text.split()
        except ValueError:
            await update.message.reply_text("Неверный формат. Введите: логин пробел пароль")
            return

        if ADMIN_CREDENTIALS.get(login) == password:
            user_states[user_id] = "authenticated_admin"
            keyboard = [
                [InlineKeyboardButton("Выйти", callback_data="logout")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("✅ Вход выполнен. Привет, администратор!", reply_markup=reply_markup)
        else:
            await update.message.reply_text("❌ Неверный логин или пароль. Попробуйте снова.")

    else:
        await update.message.reply_text("Используйте /start для начала.")

# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    app.run_polling()

