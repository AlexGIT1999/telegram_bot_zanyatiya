import telebot
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import data

# Загружаем переменные из .env файла
load_dotenv()

# Получаем токен из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("Не найден токен бота. Проверь файл .env")

bot = telebot.TeleBot(BOT_TOKEN)

# Словарь для хранения временных данных пользователей
user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_data[user_id] = {}  # Создаем временное хранилище для пользователя
    
    bot.reply_to(message, "Привет! Я бот для записи на занятия.\nДля начала представьтесь, пожалуйста.")
    msg = bot.send_message(message.chat.id, "Введите вашу фамилию и имя:")
    bot.register_next_step_handler(msg, process_parent_name_step)

def process_parent_name_step(message):
    user_id = message.from_user.id
    user_data[user_id]['parent_name'] = message.text
    
    msg = bot.send_message(message.chat.id, "Введите фамилию и имя ребенка:")
    bot.register_next_step_handler(msg, process_child_name_step)

def process_child_name_step(message):
    user_id = message.from_user.id
    user_data[user_id]['child_name'] = message.text
    
    msg = bot.send_message(message.chat.id, "Введите ваш номер телефона:")
    bot.register_next_step_handler(msg, process_phone_step)

def process_phone_step(message):
    user_id = message.from_user.id
    user_data[user_id]['phone'] = message.text
    
    # Сохраняем данные пользователя
    data.save_user(user_id, user_data[user_id])
    
    # Показываем введенные данные для подтверждения
    confirmation_text = f"Проверьте введенные данные:\n\n"
    confirmation_text += f"Ваше имя: {user_data[user_id]['parent_name']}\n"
    confirmation_text += f"Имя ребенка: {user_data[user_id]['child_name']}\n"
    confirmation_text += f"Телефон: {user_data[user_id]['phone']}\n\n"
    confirmation_text += "Всё верно?"
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да, всё верно", "Нет, начать заново")
    msg = bot.send_message(message.chat.id, confirmation_text, reply_markup=markup)
    bot.register_next_step_handler(msg, process_confirmation_step)

def process_confirmation_step(message):
    user_id = message.from_user.id
    
    if message.text == "Да, всё верно":
        bot.send_message(message.chat.id, "Отлично! Теперь вы можете записаться на занятие.", reply_markup=telebot.types.ReplyKeyboardRemove())
        show_available_dates(message)  # Показываем доступные даты
    else:
        # Начинаем регистрацию заново
        msg = bot.send_message(message.chat.id, "Хорошо, давайте начнем заново.\nВведите вашу фамилию и имя:", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_parent_name_step)

def show_available_dates(message):
    """Показывает доступные даты для записи"""
    # Пока показываем следующие 7 дней
    dates = []
    today = datetime.now()
    for i in range(7):
        date = today + timedelta(days=i)
        dates.append(date.strftime("%d.%m.%Y"))
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for date in dates:
        markup.add(date)
    
    msg = bot.send_message(message.chat.id, "Выберите дату для записи:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_date_selection)

def process_date_selection(message):
    """Обрабатывает выбор даты"""
    user_id = message.from_user.id
    selected_date = message.text
    user_data[user_id]['selected_date'] = selected_date
    
    # Пока показываем фиксированное время (позже будет из базы)
    time_slots = ["09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00", "13:00-14:00"]
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for slot in time_slots:
        markup.add(slot)
    
    msg = bot.send_message(message.chat.id, "Выберите время для записи:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_time_selection)

def process_time_selection(message):
    """Обрабатывает выбор времени"""
    user_id = message.from_user.id
    selected_time = message.text
    user_data[user_id]['selected_time'] = selected_time
    
    # Формируем подтверждение записи
    confirmation_text = f"Подтвердите запись:\n\n"
    confirmation_text += f"Дата: {user_data[user_id]['selected_date']}\n"
    confirmation_text += f"Время: {selected_time}\n"
    confirmation_text += f"Ребенок: {user_data[user_id]['child_name']}\n"
    confirmation_text += f"Родитель: {user_data[user_id]['parent_name']}\n"
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Подтвердить запись", "Отмена")
    msg = bot.send_message(message.chat.id, confirmation_text, reply_markup=markup)
    bot.register_next_step_handler(msg, process_booking_confirmation)

def process_booking_confirmation(message):
    """Обрабатывает подтверждение записи"""
    user_id = message.from_user.id
    
    if message.text == "Подтвердить запись":
        # Сохраняем запись
        booking = {
            "user_id": user_id,
            "parent_name": user_data[user_id]['parent_name'],
            "child_name": user_data[user_id]['child_name'],
            "phone": user_data[user_id]['phone'],
            "date": user_data[user_id]['selected_date'],
            "time": user_data[user_id]['selected_time'],
            "timestamp": datetime.now().isoformat()
        }
        
        data.save_booking(booking)
        
        bot.send_message(
            message.chat.id, 
            f"✅ Вы успешно записаны!\n\n"
            f"Дата: {user_data[user_id]['selected_date']}\n"
            f"Время: {user_data[user_id]['selected_time']}\n\n"
            f"Напоминание придет за день до занятия.",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
    else:
        bot.send_message(
            message.chat.id, 
            "Запись отменена.", 
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)
