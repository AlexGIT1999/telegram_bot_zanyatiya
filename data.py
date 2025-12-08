import json
import os
from datetime import datetime

# Имена файлов для хранения данных
SLOTS_FILE = 'slots.json'
BOOKINGS_FILE = 'bookings.json'
USERS_FILE = 'users.json'

def init_files():
    """Создает файлы данных, если их нет"""
    if not os.path.exists(SLOTS_FILE):
        with open(SLOTS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    
    if not os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def save_slots(slots):
    """Сохраняет слоты в файл"""
    with open(SLOTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(slots, f, ensure_ascii=False, indent=2)

def load_slots():
    """Загружает слоты из файла"""
    try:
        with open(SLOTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_booking(booking):
    """Сохраняет запись в файл"""
    bookings = load_bookings()
    bookings.append(booking)
    with open(BOOKINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(bookings, f, ensure_ascii=False, indent=2)

def load_bookings():
    """Загружает записи из файла"""
    try:
        with open(BOOKINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_user(user_id, user_data):
    """Сохраняет данные пользователя"""
    users = load_users()
    users[str(user_id)] = user_data
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_users():
    """Загружает данные пользователей"""
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Инициализируем файлы при запуске
init_files()
