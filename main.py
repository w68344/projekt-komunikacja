from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# db.py
import sqlite3

def amdin_db():
    conn = sqlite3.connect("admin_data.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    # Dodajemy testowego admina (jeśli go nie ma)
    c.execute("INSERT OR IGNORE INTO admins (username, password) VALUES (?, ?)", ("admin", "1234"))
    conn.commit()
    conn.close()

def events_db():
    conn = sqlite3.connect("events_db.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            max_participants INTEGER NOT NULL,
            event_time DATETIME NOT NULL,
            registered_participants INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)
    conn.commit()
    conn.close()

from datetime import datetime, timedelta

def create_sample_events():
    conn = sqlite3.connect("events_db.db")
    c = conn.cursor()

    # Sprawdzenie, czy są już wydarzenia
    c.execute("SELECT COUNT(*) FROM events")
    count = c.fetchone()[0]

    if count > 0:
        conn.close()
        return  # Jeśli są już wpisy – wychodzimy

    # Przykłady koncertów
    events = [
        ("Noc Rocka", 200, datetime.now() + timedelta(days=1, hours=18)),
        ("Klasyka Wieczorem", 100, datetime.now() + timedelta(days=2, hours=19)),
        ("Jazz i Wino", 150, datetime.now() + timedelta(days=3, hours=20)),
        ("Festiwal Elektroniki", 500, datetime.now() + timedelta(days=4, hours=21)),
        ("Akustyczny Poranek", 80, datetime.now() + timedelta(days=5, hours=10)),
    ]

    for name, max_participants, event_time in events:
        c.execute("""
            INSERT INTO events (name, max_participants, event_time, registered_participants)
            VALUES (?, ?, ?, 0)
        """, (name, max_participants, event_time.strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

def get_all_events():
    conn = sqlite3.connect("events_db.db")
    c = conn.cursor()
    c.execute("SELECT id, name, max_participants, event_time, registered_participants FROM events ORDER BY event_time")
    events = c.fetchall()
    conn.close()
    return events
def register_user_for_event(event_id):
    conn = sqlite3.connect("events_db.db")
    c = conn.cursor()

    # Sprawdź limit
    c.execute("SELECT max_participants, registered_participants FROM events WHERE id = ?", (event_id,))
    row = c.fetchone()

    if not row:
        conn.close()
        return False, "Wydarzenie nie znalezione."

    max_p, reg_p = row
    if reg_p >= max_p:
        conn.close()
        return False, "Brak wolnych miejsc."

    # Aktualizujemy liczbę zapisanych uczestników
    c.execute("UPDATE events SET registered_participants = registered_participants + 1 WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    return True, "Pomyślnie zapisano!"

def validate_admin(username, password):
    conn = sqlite3.connect("admin_data.db")
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE username = ? AND password = ?", (username, password))
    result = c.fetchone()
    conn.close()
    return result is not None


TOKEN = "8055838402:AAE6PASMcqUbDmWd0Q6yMqNYPwHerbcCj1E"

user_states = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Widz", callback_data="role_viewer")],
        [InlineKeyboardButton("Administrator", callback_data="role_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Wybierz rolę:", reply_markup=reply_markup)
    user_states[update.effective_user.id] = "start"

# Obsługa przycisków
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "role_viewer":
        user_states[user_id] = "viewer"
        events = get_all_events()

        if not events:
            await query.edit_message_text("Brak wydarzeń.")
            return

        context.user_data["events"] = events

        message = "🎫 *Dostępne wydarzenia:*\n\n"
        for idx, (event_id, name, max_participants, event_time, registered) in enumerate(events, start=1):
            message += f"{idx}. *{name}*\n   Miejsca: {max_participants}\n   🕒 {event_time}\n\n"

        message += "Wpisz numer wydarzenia, aby je wybrać."
        await query.edit_message_text(message, parse_mode="Markdown")

    elif query.data == "admin_menu":
        keyboard = [
            [InlineKeyboardButton("📋 Pokaż wydarzenia", callback_data="admin_show_events")],
            [InlineKeyboardButton("➕ Dodaj wydarzenie", callback_data="admin_add_event")],
            [InlineKeyboardButton("✏️ Edytuj wydarzenie", callback_data="admin_edit_event")],
            [InlineKeyboardButton("🗑️ Usuń zapis uczestnika", callback_data="admin_delete_participant")],
            [InlineKeyboardButton("🔐 Otwórz/Zamknij zapisy", callback_data="admin_toggle_event")],
            [InlineKeyboardButton("🚪 Wyloguj", callback_data="logout")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Menu administratora:", reply_markup=reply_markup)

    elif query.data == "admin_show_events":
        events = get_all_events()
        if not events:
            await query.edit_message_text("Brak wydarzeń.")
            return

        message = "📋 *Lista wydarzeń:*\n\n"
        for idx, (event_id, name, max_participants, event_time, registered) in enumerate(events, start=1):
            message += (
                f"{idx}. *{name}*\n"
                f"   Czas: {event_time}\n"
                f"   Miejsc łącznie: {max_participants}\n"
                f"   Zapisanych: {registered}\n\n"
            )

        keyboard = [
            [InlineKeyboardButton("Wstecz", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)

    elif query.data == "role_admin":
        user_states[user_id] = "awaiting_login"
        await query.edit_message_text(
            "Wpisz login i hasło oddzielone spacją (np.: `admin 1234`):",
            parse_mode="Markdown"
        )

    elif query.data == "logout":
        user_states[user_id] = "start"
        keyboard = [
            [InlineKeyboardButton("Widz", callback_data="role_viewer")],
            [InlineKeyboardButton("Administrator", callback_data="role_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Wylogowano. Wybierz rolę:", reply_markup=reply_markup)

    elif query.data == "back_to_main":
        user_states[user_id] = "start"
        keyboard = [
            [InlineKeyboardButton("Widz", callback_data="role_viewer")],
            [InlineKeyboardButton("Administrator", callback_data="role_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Wybierz rolę:", reply_markup=reply_markup)
    elif query.data == "show_participants":
        event_id = context.user_data.get("admin_selected_event_id")
        event_name = context.user_data.get("admin_selected_event_name")

        conn = sqlite3.connect("events_db.db")
        c = conn.cursor()
        c.execute("SELECT name FROM participants WHERE event_id = ?", (event_id,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            await query.edit_message_text(f"👥 Brak zapisanych uczestników na *{event_name}*.", parse_mode="Markdown")
            return

        names_list = "\n".join([f"{idx+1}. {name[0]}" for idx, name in enumerate(rows)])
        keyboard = [
            [InlineKeyboardButton("🔙 Wróć do menu administratora", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"👥 Lista uczestników dla *{event_name}*:\n\n{names_list}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    elif query.data == "admin_add_event":
        user_states[user_id] = "awaiting_event_name"
        await query.edit_message_text(
            "📝 Wpisz nazwę nowego wydarzenia:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Wróć", callback_data="admin_menu")]])
        )


# Obsługa tekstu (login/hasło)
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_states.get(user_id) == "awaiting_login":

        try:
            login, password = text.split()
        except ValueError:
            await update.message.reply_text(
                "❌ Niepoprawny format. Wpisz login i hasło oddzielone spacją, np.: `admin 1234`"
            )
            return

        if validate_admin(login, password):
            user_states[user_id] = "authenticated_admin"
            keyboard = [
                [InlineKeyboardButton("📋 Pokaż wydarzenia", callback_data="admin_show_events")],
                [InlineKeyboardButton("➕ Dodaj wydarzenie", callback_data="admin_add_event")],
                [InlineKeyboardButton("✏️ Edytuj wydarzenie", callback_data="admin_edit_event")],
                [InlineKeyboardButton("🗑️ Usuń zapis uczestnika", callback_data="admin_delete_participant")],
                [InlineKeyboardButton("🔐 Otwórz/Zamknij zapisy", callback_data="admin_toggle_event")],
                [InlineKeyboardButton("🚪 Wyloguj", callback_data="logout")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("✅ Zalogowano. Witaj, administratorze!", reply_markup=reply_markup)
        else:
            await update.message.reply_text("❌ Niepoprawny login lub hasło. Spróbuj ponownie.")
    elif user_states.get(user_id) == "authenticated_admin":
        if text.isdigit():
            event_index = int(text) - 1
            events = get_all_events()

            if 0 <= event_index < len(events):
                event_id, name, max_participants, event_time, registered = events[event_index]
                context.user_data["admin_selected_event_id"] = event_id
                context.user_data["admin_selected_event_name"] = name

                keyboard = [
                    [InlineKeyboardButton("👥 Pokaż uczestników", callback_data="show_participants")],
                    [InlineKeyboardButton("🔙 Wróć", callback_data="admin_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    f"✅ Wybrane wydarzenie:\n\n"
                    f"*{name}*\n🕒 {event_time}\n👥 Zapisanych: {registered}/{max_participants}",
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("❌ Niepoprawny numer wydarzenia.")
        else:
            await update.message.reply_text("❌ Wpisz numer wydarzenia.")


    elif user_states.get(user_id) == "viewer":

        if text.isdigit():

            event_index = int(text) - 1

            events = context.user_data.get("events", [])

            if 0 <= event_index < len(events):

                event_id, name, max_participants, event_time, reg_p = events[event_index]

                context.user_data["selected_event_id"] = event_id

                context.user_data["selected_event_name"] = name

                context.user_data["selected_event_time"] = event_time

                context.user_data["selected_max"] = max_participants

                context.user_data["selected_registered"] = reg_p

                user_states[user_id] = "awaiting_name"

                await update.message.reply_text("📝 Wpisz swoje imię, aby się zapisać:")

            else:

                await update.message.reply_text("❌ Niepoprawny numer wydarzenia. Spróbuj ponownie.")

        else:

            await update.message.reply_text("❌ Wpisz poprawny numer wydarzenia.")

    elif user_states.get(user_id) == "awaiting_name":
        name = text
        event_id = context.user_data.get("selected_event_id")
        event_name = context.user_data.get("selected_event_name")
        event_time = context.user_data.get("selected_event_time")
        max_p = context.user_data.get("selected_max")
        reg_p = context.user_data.get("selected_registered")

        # Zarejestruj użytkownika
        success, message = register_user_for_event(event_id)
        if success:
            conn = sqlite3.connect("events_db.db")
            c = conn.cursor()
            c.execute("INSERT INTO participants (event_id, user_id, name) VALUES (?, ?, ?)",
                      (event_id, user_id, name))
            conn.commit()
            conn.close()

            keyboard = [
                [InlineKeyboardButton("🔙 Wstecz do menu głównego", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ {message}\n\n"
                f"*{event_name}*\n"
                f"🕒 Czas: {event_time}\n"
                f"👤 Uczestnik: {name}\n"
                f"👥 Miejsc łącznie: {max_p}, zajętych: {reg_p + 1}",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(f"❌ {message}")

        user_states[user_id] = "viewer"  # wracamy do trybu widza
    elif user_states.get(user_id) == "awaiting_event_name":
        context.user_data["new_event_name"] = text
        user_states[user_id] = "awaiting_event_capacity"
        await update.message.reply_text(
            "👥 Wpisz maksymalną liczbę uczestników:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Wróć", callback_data="admin_menu")]])
        )

    elif user_states.get(user_id) == "awaiting_event_capacity":
        if not text.isdigit() or int(text) <= 0:
            await update.message.reply_text("❌ Podaj poprawną liczbę.")
            return
        context.user_data["new_event_capacity"] = int(text)
        user_states[user_id] = "awaiting_event_time"
        await update.message.reply_text(
            "⏰ Podaj datę i czas w formacie `YYYY-MM-DD HH:MM`:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Wróć", callback_data="admin_menu")]])
        )

    elif user_states.get(user_id) == "awaiting_event_time":
        try:
            dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        except ValueError:
            await update.message.reply_text("❌ Błędny format. Spróbuj ponownie (np. `2025-08-01 19:30`).")
            return

        name = context.user_data["new_event_name"]
        max_p = context.user_data["new_event_capacity"]
        event_time = dt.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect("events_db.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO events (name, max_participants, event_time, registered_participants)
            VALUES (?, ?, ?, 0)
        """, (name, max_p, event_time))
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"✅ Dodano wydarzenie:\n\n*{name}*\n🕒 {event_time}\n👥 Maks: {max_p}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Wróć do menu", callback_data="admin_menu")]])
        )
        user_states[user_id] = "authenticated_admin"

    else:
        await update.message.reply_text("❗ Użyj /start, aby zacząć.")




# Uruchomienie
if __name__ == "__main__":
    amdin_db()  # Tworzenie bazy przy starcie
    events_db()
    create_sample_events()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    app.run_polling()
