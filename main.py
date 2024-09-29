import asyncio
import os
import re
import json
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup

# Получение токена бота и идентификатора группы из Secret переменных
API_TOKEN = os.environ['API_TOKEN']
GROUP_ID = int(os.environ.get('GROUP_ID', '0'))  # Инициализируем GROUP_ID из файла данных или 0 по умолчанию

# Список ID администраторов
ADMIN_IDS = [103497276]  # Замените на реальные ID администраторов

# Функция для проверки, является ли пользователь администратором
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Определение состояний
class Form(StatesGroup):
    industry = State()
    bot_type = State()
    display_name = State()
    bot_username = State()
    rating = State()
    admin_action = State()
    new_industry = State()
    remove_industry = State()
    new_bot_type = State()
    remove_bot_type = State()
    set_group_id = State()

# Инициализация переменных
industries = []
bot_types = []
ratings = []

# Функции для загрузки и сохранения данных
def load_data():
    global industries, bot_types, ratings, GROUP_ID
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            industries = data.get('industries', [])
            bot_types = data.get('bot_types', [])
            ratings = data.get('ratings', [])
            GROUP_ID = int(data.get('GROUP_ID', GROUP_ID))
    except FileNotFoundError:
        industries = ['Парикмахерская', 'Розничный магазин', 'Оптовая торговля', 'Ресторан', 'Фитнес-центр']
        bot_types = ['Бот для продаж', 'Бот для онлайн-заказов', 'Бот для поддержки клиентов', 'Бот для бронирования']
        ratings = []
        save_data()

def save_data():
    data = {
        'industries': industries,
        'bot_types': bot_types,
        'ratings': ratings,
        'GROUP_ID': GROUP_ID
    }
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализируем бота и диспетчер
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Обработчики без декораторов

# Обработчик команды /start
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(Form.industry)
    # Создаем клавиатуру с вариантами отраслей
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=item)] for item in industries],
        resize_keyboard=True
    )
    await message.answer(
        f"{message.from_user.first_name}, привет! Я умный чат-бот, который умеет делать таких же умных чат-ботов для разных компаний.\n"
        "Выбери, чем занимается твоя компания:",
        reply_markup=keyboard
    )

# Обработчик выбора отрасли
async def process_industry(message: Message, state: FSMContext):
    if message.text not in industries:
        await message.answer("Пожалуйста, выберите отрасль из предложенных вариантов.")
        return
    await state.update_data(industry=message.text)
    await state.set_state(Form.bot_type)
    # Создаем клавиатуру с вариантами типов ботов
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=item)] for item in bot_types],
        resize_keyboard=True
    )
    await message.answer(
        "Выбери тип бота, который необходим для вашего бизнеса:",
        reply_markup=keyboard
    )

# Обработчик выбора типа бота
async def process_bot_type(message: Message, state: FSMContext):
    if message.text not in bot_types:
        await message.answer("Пожалуйста, выберите тип бота из предложенных вариантов.")
        return
    await state.update_data(bot_type=message.text)
    await state.set_state(Form.display_name)
    # Убираем клавиатуру
    await message.answer(
        "Придумайте название вашего бота — оно будет отображаться в диалогах пользователей и может быть любым.",
        reply_markup=types.ReplyKeyboardRemove()
    )

# Обработчик ввода названия бота
async def process_display_name(message: Message, state: FSMContext):
    await state.update_data(display_name=message.text)
    await state.set_state(Form.bot_username)
    await message.answer(
        "Придумайте уникальное имя пользователя бота, написанное латиницей и содержащее слово 'bot'. Минимальная длина — 5 символов, максимальная — 32."
    )

# Обработчик ввода имени пользователя бота
async def process_bot_username(message: Message, state: FSMContext):
    bot_username = message.text
    # Проверяем соответствие требованиям
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{3,30}bot$', bot_username):
        await message.answer("Имя пользователя не соответствует требованиям. Пожалуйста, попробуйте снова.")
        return
    await state.update_data(bot_username=bot_username)
    data = await state.get_data()
    await state.set_state(Form.rating)
    await message.answer(
        f"Ваша заявка на создание умного бота для {data['bot_type']} успешно создана!\n"
        "Оцените, пожалуйста, насколько было удобно работать с заявкой (от 1 до 5)."
    )

# Обработчик оценки
async def process_rating(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) not in range(1, 6):
        await message.answer("Пожалуйста, введите число от 1 до 5.")
        return
    await state.update_data(rating=message.text)
    data = await state.get_data()

    # Сохраняем оценку
    ratings.append(int(data['rating']))
    save_data()

    # Формирование сообщения для группы
    result_message = (
        f"Новая заявка от @{message.from_user.username} ({message.from_user.full_name}):\n"
        f"Отрасль: {data['industry']}\n"
        f"Тип бота: {data['bot_type']}\n"
        f"Название бота: {data['display_name']}\n"
        f"Имя пользователя бота: {data['bot_username']}\n"
        f"Оценка пользователя: {data['rating']}"
    )

    # Отправка сообщения в группу, если GROUP_ID задан
    if GROUP_ID != 0:
        await bot.send_message(chat_id=GROUP_ID, text=result_message)

    await message.answer("Спасибо за вашу оценку! Мы свяжемся с вами в ближайшее время.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

# Админ-панель
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав доступа к админ-панели.")
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить отрасль"), KeyboardButton(text="Удалить отрасль")],
            [KeyboardButton(text="Добавить тип бота"), KeyboardButton(text="Удалить тип бота")],
            [KeyboardButton(text="Изменить GROUP_ID"), KeyboardButton(text="Средняя оценка")],
            [KeyboardButton(text="Выйти из админ-панели")]
        ],
        resize_keyboard=True
    )
    await message.answer("Добро пожаловать в админ-панель. Выберите действие:", reply_markup=keyboard)
    await state.set_state(Form.admin_action)

# Обработка действий админа
async def process_admin_action(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав доступа к админ-панели.")
        await state.finish()
        return

    if message.text == "Добавить отрасль":
        await message.answer("Введите название новой отрасли:")
        await state.set_state(Form.new_industry)
    elif message.text == "Удалить отрасль":
        if not industries:
            await message.answer("Список отраслей пуст.")
            await admin_panel(message, state)
            return
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=industry)] for industry in industries] + [[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        )
        await message.answer("Выберите отрасль для удаления:", reply_markup=keyboard)
        await state.set_state(Form.remove_industry)
    elif message.text == "Добавить тип бота":
        await message.answer("Введите название нового типа бота:")
        await state.set_state(Form.new_bot_type)
    elif message.text == "Удалить тип бота":
        if not bot_types:
            await message.answer("Список типов ботов пуст.")
            await admin_panel(message, state)
            return
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=bot_type)] for bot_type in bot_types] + [[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        )
        await message.answer("Выберите тип бота для удаления:", reply_markup=keyboard)
        await state.set_state(Form.remove_bot_type)
    elif message.text == "Изменить GROUP_ID":
        await message.answer("Введите новый GROUP_ID (целое число):")
        await state.set_state(Form.set_group_id)
    elif message.text == "Средняя оценка":
        if ratings:
            average = sum(ratings) / len(ratings)
            await message.answer(f"Средняя оценка пользователей: {average:.2f}")
        else:
            await message.answer("Оценок пока нет.")
        await admin_panel(message, state)
    elif message.text == "Выйти из админ-панели":
        await message.answer("Вы вышли из админ-панели.", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
    else:
        await message.answer("Пожалуйста, выберите действие из меню.")

# Добавление новой отрасли
async def process_new_industry(message: Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await message.answer("Действие отменено.", reply_markup=types.ReplyKeyboardRemove())
        await admin_panel(message, state)
        return
    industries.append(message.text)
    save_data()
    await message.answer(f"Отрасль '{message.text}' добавлена.", reply_markup=types.ReplyKeyboardRemove())
    await admin_panel(message, state)

# Удаление отрасли
async def process_remove_industry(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer("Действие отменено.", reply_markup=types.ReplyKeyboardRemove())
        await admin_panel(message, state)
        return
    if message.text in industries:
        industries.remove(message.text)
        save_data()
        await message.answer(f"Отрасль '{message.text}' удалена.", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("Отрасль не найдена.")
    await admin_panel(message, state)

# Добавление нового типа бота
async def process_new_bot_type(message: Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await message.answer("Действие отменено.", reply_markup=types.ReplyKeyboardRemove())
        await admin_panel(message, state)
        return
    bot_types.append(message.text)
    save_data()
    await message.answer(f"Тип бота '{message.text}' добавлен.", reply_markup=types.ReplyKeyboardRemove())
    await admin_panel(message, state)

# Удаление типа бота
async def process_remove_bot_type(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer("Действие отменено.", reply_markup=types.ReplyKeyboardRemove())
        await admin_panel(message, state)
        return
    if message.text in bot_types:
        bot_types.remove(message.text)
        save_data()
        await message.answer(f"Тип бота '{message.text}' удален.", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("Тип бота не найден.")
    await admin_panel(message, state)

# Изменение GROUP_ID
async def process_set_group_id(message: Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await message.answer("Действие отменено.", reply_markup=types.ReplyKeyboardRemove())
        await admin_panel(message, state)
        return
    global GROUP_ID
    try:
        GROUP_ID = int(message.text)
        save_data()
        await message.answer(f"GROUP_ID успешно изменен на {GROUP_ID}.", reply_markup=types.ReplyKeyboardRemove())
    except ValueError:
        await message.answer("Пожалуйста, введите корректный числовой GROUP_ID.")
    await admin_panel(message, state)

# Основная функция
async def main():
    load_data()

    # Регистрация обработчиков с использованием StateFilter
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(admin_panel, Command(commands=["admin"]))
    dp.message.register(process_industry, StateFilter(Form.industry))
    dp.message.register(process_bot_type, StateFilter(Form.bot_type))
    dp.message.register(process_display_name, StateFilter(Form.display_name))
    dp.message.register(process_bot_username, StateFilter(Form.bot_username))
    dp.message.register(process_rating, StateFilter(Form.rating))
    dp.message.register(process_admin_action, StateFilter(Form.admin_action))
    dp.message.register(process_new_industry, StateFilter(Form.new_industry))
    dp.message.register(process_remove_industry, StateFilter(Form.remove_industry))
    dp.message.register(process_new_bot_type, StateFilter(Form.new_bot_type))
    dp.message.register(process_remove_bot_type, StateFilter(Form.remove_bot_type))
    dp.message.register(process_set_group_id, StateFilter(Form.set_group_id))

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())