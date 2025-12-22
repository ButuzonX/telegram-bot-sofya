# MVP Telegram bot for Zoom masterclass registration & payment
# Python 3.11 | aiogram 3.x

from db import init_db
from db import get_connection

import asyncio
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

import datetime
from datetime import timedelta

import os
from dotenv import load_dotenv

load_dotenv()


# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS").split(",")}
DB_NAME = os.getenv("DB_NAME", "bot.db")
EVENT_TITLE = "Онлайн мастер-класс"
EVENT_DATETIME = datetime.datetime.strptime(
    os.getenv("EVENT_DATETIME"),
    "%Y-%m-%d %H:%M"
)
last_check = datetime.datetime.now()
ZOOM_LINK = os.getenv("ZOOM_LINK")
GROUP_INVITE_LINK = os.getenv("GROUP_INVITE_LINK")
PAYPAL_LINK = os.getenv("PAYPAL_LINK")
RUB_CARD_TEXT = os.getenv("RUB_CARD_TEXT")
# PAYPAL_LINK = "https://paypal.me/yourname"
# RUB_CARD_TEXT = "Оплата в рублях:\nКарта: XXXX XXXX XXXX XXXX"

# ================== ТЕКСТОВЫЕ БЛОКИ ==================
# Блок 1: пункты 1-2
EVENT_PAGE_1 = """Менопауза 3D. Помогающий взгляд изнутри. 

Программа: 

1. Конечная остановка или переход? Смыслы менопаузы: что она нам приносит, и как нам это использовать. 

2. Предвестники и признаки. Как понять, что менопауза близко, и что стоит делать в ожидании? 
А что может повлиять на срок прихода менопаузы: придет она преждевременно,  или можно отсрочить?"""

# Блок 2: пункт 3
EVENT_PAGE_2 = """3. Физические симптомы.
Приливы,  плохой сон, мигрени, сухость и зуд, и все остальное, чего мы боимся.
Логика, взаимосвязи, сила проявления.
Целесообразность и риски различных подходов с акцентом на качество жизни. 
Разумная достаточность. Если я уже там, и использую разные способы - все ли я делаю, что могу, или можно еще улучшить ситуацию?"""

# Блок 3: пункты 4-7
EVENT_PAGE_3 = """4. Когнитивные изменения.  Концентрация, мышление, "туман в голове". Пройдёт или будет все хуже? 
С чем можно мириться, а что можно и нужно корректировать.

5. Эмоции и настроение.  Как выжить самой и никого не прибить. 

6. Резюмируем: какие есть варианты улучшить свое  состояние на всех этапах, как оценить риски и выбрать свой способ.

7. Ответы на вопросы."""

# Блок 4: об авторе, дата, время, стоимость
EVENT_PAGE_4 = """Об авторе.

Софья Исакова:

- я биолог, нутрициолог, health-ментор, телесный психолог;
- работаю с клиентками в этом периоде, и помогаю им восстановить или выстроить заново свое хорошее самочувствие и взаимоотношения с телом;
- наконец, мне 51, и я на пороге менопаузы, сама прохожу через эти состояния,  наблюдаю и экспериментирую."""

# Блок 5: техническая инфа
EVENT_PAGE_5 = """Мастер-класс пройдёт онлайн, в Zoom
25 января, воскресенье 
В 15.00 СЕТ
16.00 Иерусалим/ Киев/ Ларнака
17.00 Мск
9.00 a.m. Нью-Йорк 

Длительность 2,5 часа.

Стоимость 40 € (оплата в любой валюте) 

Мастер-класс будет записан, доступ к записи получат все, кто оплатил участие."""


# ================== КОНЕЦ ТЕКСТОВЫХ БЛОКОВ ==================

# ================== FSM ==================
class Registration(StatesGroup):
    full_name = State()
    username = State()
    email = State()
    question = State()

# ================== BOT INIT ==================
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ================== КНОПКИ ==================

# Кнопки "Далее" для страниц
next_kb_1 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➡ Далее", callback_data="next_2")]
])

next_kb_2 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➡ Далее", callback_data="next_3")]
])

next_kb_3 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➡ Далее", callback_data="next_4")]
])
next_kb_4 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➡ Далее", callback_data="next_5")]
])


# ================== KEYBOARDS ==================
# кнопка регистрации
def start_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Регистрация на мастер-класс", callback_data="register")]
    ])
    return kb

start_kb_markup = start_kb()

def payment_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 PayPal", callback_data="pay_paypal")
    kb.button(text="🇷🇺 Оплата в рублях", callback_data="pay_rub")
    kb.adjust(1)
    return kb.as_markup()


def paid_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Я оплатил", callback_data="paid")
    return kb.as_markup()


def admin_kb(user_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"confirm_{user_id}")
    kb.button(text="❌ Отклонить", callback_data=f"reject_{user_id}")
    return kb.as_markup()


def save_user(user_id, full_name, username, email, question):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO users
        (telegram_id, full_name, username, email, question)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, full_name, username, email, question))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT full_name, username, email, question
        FROM users WHERE telegram_id=?
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

def set_payment_status(user_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO payments (telegram_id, status)
        VALUES (?, ?)
    """, (user_id, status))
    conn.commit()
    conn.close()

def get_last_check():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key='last_check'")
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        return datetime.datetime.fromisoformat(row[0])
    else:
        return datetime.datetime.now()

def set_last_check(dt):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO settings (key, value)
        VALUES ('last_check', ?)
    """, (dt.isoformat(),))
    conn.commit()
    conn.close()



# ================== HANDLERS ==================

# ================== ОБРАБОТЧИК /start ==================
@dp.message(CommandStart())
async def start(msg: Message):
    await msg.answer(EVENT_PAGE_1, reply_markup=next_kb_1)

# ================== CALLBACK ДЛЯ СТРАНИЦ ==================
@dp.callback_query(F.data == "next_2")
async def show_page_2(cb: CallbackQuery):
    await cb.message.edit_reply_markup(reply_markup=None)  # убираем кнопку с первой страницы
    await cb.message.answer(EVENT_PAGE_2, reply_markup=next_kb_2)

@dp.callback_query(F.data == "next_3")
async def show_page_3(cb: CallbackQuery):
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(EVENT_PAGE_3, reply_markup=next_kb_3)

@dp.callback_query(F.data == "next_4")
async def show_page_4(cb: CallbackQuery):
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(EVENT_PAGE_4, reply_markup=next_kb_4)

# callback для перехода на 5-ю страницу
@dp.callback_query(F.data == "next_5")
async def show_page_5(cb: CallbackQuery):
    await cb.message.edit_reply_markup(reply_markup=None)  # убираем кнопку с предыдущей страницы
    await cb.message.answer(EVENT_PAGE_5, reply_markup=start_kb_markup)

@dp.callback_query(F.data == "register")
async def register(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите Фамилию и Имя:")
    await state.set_state(Registration.full_name)


@dp.message(Registration.full_name)
async def reg_name(msg: Message, state: FSMContext):
    await state.update_data(full_name=msg.text)
    await msg.answer(
        "Введите ваш username в Telegram (без @).\n"
        "Это обязательно."
    )
    await state.set_state(Registration.username)

@dp.message(Registration.username)
async def reg_username(msg: Message, state: FSMContext):
    username = msg.text.strip().lstrip("@")

    if not username:
        await msg.answer("Username не может быть пустым. Введите ещё раз:")
        return

    await state.update_data(username=username)
    await msg.answer(
        "Введите email (или напишите 'нет', чтобы пропустить):"
    )
    await state.set_state(Registration.email)

@dp.message(Registration.email)
async def reg_email(msg: Message, state: FSMContext):
    text = msg.text.strip().lower()

    email = None if text == "нет" else msg.text

    await state.update_data(email=email)
    await msg.answer(
        "Ваш вопрос автору? (или напишите 'нет')"
    )
    await state.set_state(Registration.question)


@dp.message(Registration.question)
async def reg_question(msg: Message, state: FSMContext):
    data = await state.get_data()

    save_user(
        msg.from_user.id,
        data["full_name"],
        data["username"],
        data["email"],
        None if msg.text.lower() == "нет" else msg.text,
    )

    await state.clear()
    await msg.answer("Выберите способ оплаты:", reply_markup=payment_kb())


@dp.callback_query(F.data == "pay_paypal")
async def pay_paypal(cb: CallbackQuery):
    set_payment_status(cb.from_user.id, "pending")
    await cb.message.answer(
        f"Оплатите по ссылке:\n{PAYPAL_LINK}", reply_markup=paid_kb()
    )


@dp.callback_query(F.data == "pay_rub")
async def pay_rub(cb: CallbackQuery):
    set_payment_status(cb.from_user.id, "pending")
    await cb.message.answer(RUB_CARD_TEXT, reply_markup=paid_kb())


@dp.callback_query(F.data == "paid")
async def paid(cb: CallbackQuery):
    await cb.answer()

    user = get_user(cb.from_user.id)
    if not user:
        await cb.message.answer(
            "Ошибка: анкета не найдена.\n"
            "Пожалуйста, пройдите регистрацию заново через /start"
        )
        return

    full_name, username, email, _ = user
    email_text = email if email else "не указан"

    for admin_id in ADMIN_IDS:
        await bot.send_message(
            admin_id,
            f"Новая оплата\n"
            f"{full_name}\n"
            f"@{username}\n"
            f"Email: {email_text}",
            reply_markup=admin_kb(cb.from_user.id),
        )

    await cb.message.answer("Оплата отправлена на проверку.")



@dp.callback_query(F.data.startswith("confirm_"))
async def confirm(cb: CallbackQuery):
    await cb.answer()

    user_id = int(cb.data.split("_")[1])

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE payments
        SET status='confirmed',
            reminder_24h_sent=0,
            reminder_1h_sent=0
        WHERE telegram_id=?
    """, (user_id,))
    conn.commit()
    conn.close()


    await bot.send_message(
        user_id,
        "✅ Оплата подтверждена!\n\n"
        "Вы приглашены в закрытую группу мастер-класса.\n"
        "Пожалуйста, вступите в неё по ссылке ниже:\n\n"
        f"{GROUP_INVITE_LINK}\n\n"
        "⏰ Ссылка на Zoom придёт автоматически:\n"
        "— за 24 часа\n"
        "— за 1 час до начала",
    )

    await cb.message.edit_text("Подтверждено")


@dp.callback_query(F.data.startswith("reject_"))
async def reject(cb: CallbackQuery):
    user_id = int(cb.data.split("_")[1])  # ← ВАЖНО

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE payments SET status='rejected' WHERE telegram_id=?",
        (user_id,)
    )
    conn.commit()
    conn.close()

    await bot.send_message(
        user_id,
        "❌ Оплата не подтверждена.\nСвяжитесь с администратором."
    )

    await cb.message.edit_text("Отклонено")



# ================== REMINDERS ==================
async def reminders():
    last_check = get_last_check()  # уже datetime

    while True:
        now = datetime.datetime.now()

        # Получаем всех подтверждённых пользователей
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            SELECT telegram_id, reminder_24h_sent, reminder_1h_sent
            FROM payments
            WHERE status='confirmed'
        """)
        rows = cur.fetchall()
        conn.close()

        for user_id, reminder_24h_sent, reminder_1h_sent in rows:
            # 24 часа до события
            t24 = EVENT_DATETIME - timedelta(hours=24)
            #t24 = EVENT_DATETIME - timedelta(minutes=7)
            if not reminder_24h_sent and last_check < t24 <= now:
                await bot.send_message(
                    user_id,
                    f"⏰ Напоминание: мастер-класс завтра!\nZoom-ссылка:\n{ZOOM_LINK}"
                )
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("UPDATE payments SET reminder_24h_sent=1 WHERE telegram_id=?", (user_id,))
                conn.commit()
                conn.close()

            # 1 час до события
            t1 = EVENT_DATETIME - timedelta(hours=1)
            # t1 = EVENT_DATETIME - timedelta(minutes=3)
            if not reminder_1h_sent and last_check < t1 <= now:
                await bot.send_message(
                    user_id,
                    f"🚀 Начинаем через 1 час!\nZoom-ссылка:\n{ZOOM_LINK}"
                )
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("UPDATE payments SET reminder_1h_sent=1 WHERE telegram_id=?", (user_id,))
                conn.commit()
                conn.close()

        # Обновляем last_check в БД
        set_last_check(now)
        last_check = now
        await asyncio.sleep(60)





async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(reminders())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

