import telebot
from datetime import datetime, timedelta
import data

# Словарь для хранения временных данных пользователей
user_data = {}

def register_client_handlers(bot):
    """Регистрирует обработчики для клиентов"""
    
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_id = message.from_user.id
        if not is_admin(bot, user_id):  # Проверяем, что это не админ
            user_data[user_id] = {}  # Создаем временное хранилище для пользователя
            bot.reply_to(message, "Привет! Я бот для записи на занятия.\nДля начала представьтесь, пожалуйста.")
            msg = bot.send_message(message.chat.id, "Введите вашу фамилию и имя:")
            bot.register_next_step_handler(msg, process_parent_name_step)

    def is_admin(bot, user_id):
        """Проверяет, является ли пользователь администратором"""
        try:
            admin_id = bot.get_me().id  # Это временно, позже заменим на реальный ID
            return False  # Пока всегда False, позже исправим
        except:
            return False

    def process_parent_name_step(message):
        user_id = message.from_user.id
        user_data[user_id] = {'parent_name': message.text}
        
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
        slots = data.load_slots()
        available_dates = list(slots.keys()) if slots else []
        
        if not available_dates:
            bot.send_message(message.chat.id, "К сожалению, пока нет доступных дат для записи.", reply_markup=telebot.types.ReplyKeyboardRemove())
            return
        
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for date in available_dates[:7]:  # Показываем максимум 7 дат
            markup.add(date)
        
        msg = bot.send_message(message.chat.id, "Выберите дату для записи:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_date_selection)

    def process_date_selection(message):
        """Обрабатывает выбор даты"""
        user_id = message.from_user.id
        selected_date = message.text
        user_data[user_id]['selected_date'] = selected_date
        
        # Загружаем доступные слоты для выбранной даты
        slots = data.load_slots()
        available_slots = []
        
        if selected_date in slots:
            for slot in slots[selected_date]:
                if slot.get('available', True):  # Если слот доступен
                    available_slots.append(slot['time'])
        
        if not available_slots:
            bot.send_message(message.chat.id, "К сожалению, на эту дату нет доступных слотов.", reply_markup=telebot.types.ReplyKeyboardRemove())
            return
        
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for slot in available_slots:
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
            # Отмечаем слот как занятый
            slots = data.load_slots()
            date = user_data[user_id]['selected_date']
            time = user_data[user_id]['selected_time']
            
            if date in slots:
                for slot in slots[date]:
                    if slot['time'] == time:
                        slot['available'] = False
                        break
            
            data.save_slots(slots)
            
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
