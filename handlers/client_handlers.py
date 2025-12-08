import telebot
from datetime import datetime, timedelta
import data

# Словарь для хранения временных данных пользователей
user_data = {}

def register_client_handlers(bot, admin_ids_list):
    """Регистрирует обработчики для клиентов"""
    # Сохраняем список админов
    admin_ids = admin_ids_list
    
    def is_admin(user_id):
        """Проверяет, является ли пользователь администратором"""
        return str(user_id) in admin_ids
    
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_id = message.from_user.id
        
        # Всегда показываем полное меню
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📝 Записаться на занятие")
        markup.add("📅 Мои записи")
        markup.add("❌ Отменить запись")
        markup.add("📖 Помощь")
        markup.add("📱 Меню")
        
        bot.reply_to(
            message, 
            "Привет! Я бот для записи на занятия.\nВыберите действие:",
            reply_markup=markup
        )
    
    @bot.message_handler(commands=['help', 'client_help'])
    def client_help_handler(message):
        """Помощь для клиентов"""
        client_help(message)
    
    def client_help(message):
        """Помощь для клиентов"""
        help_text = """
📖 Доступные команды для клиентов:

/start - Главное меню
/help - Помощь по командам

📝 Как записаться на занятие:
1. Нажмите "📝 Записаться на занятие"
2. Введите свои данные
3. Выберите дату и время
4. Подтвердите запись

❌ Как отменить запись:
1. Нажмите "❌ Отменить запись"
2. Выберите запись из списка
3. Подтвердите отмену

📅 Мои записи - просмотр ваших активных записей

Напоминание придет за день до занятия.
"""
        bot.send_message(message.chat.id, help_text)
    
    @bot.message_handler(func=lambda message: message.text == "📖 Помощь")
    def client_help_button(message):
        """Помощь через кнопку"""
        client_help(message)
    
    @bot.message_handler(func=lambda message: message.text == "📱 Меню")
    def show_menu(message):
        """Показать главное меню"""
        send_welcome(message)
    
    @bot.message_handler(func=lambda message: message.text == "📝 Записаться на занятие")
    def start_booking(message):
        user_id = message.from_user.id
        user_data[user_id] = {}  # Создаем временное хранилище для пользователя
        
        # Проверяем наличие свободных слотов
        slots = data.load_slots()
        has_available_slots = False
        
        for date, date_slots in slots.items():
            available_slots = [slot for slot in date_slots if slot.get('available', True)]
            if available_slots:
                has_available_slots = True
                break
        
        if not has_available_slots:
            bot.send_message(
                message.chat.id, 
                "К сожалению, пока нет свободных слотов для записи.\nПожалуйста, попробуйте позже.",
                reply_markup=telebot.types.ReplyKeyboardRemove()
            )
            return
        
        msg = bot.send_message(
            message.chat.id, 
            "Для записи на занятие, пожалуйста, представьтесь.\nВведите вашу фамилию и имя:",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_parent_name_step)
    
    def process_parent_name_step(message):
        user_id = message.from_user.id
        user_data[user_id] = {'parent_name': message.text}
        
        msg = bot.send_message(message.chat.id, "Введите фамилию и имя ребенка:")
        bot.register_next_step_handler(msg, process_child_name_step)

    def process_child_name_step(message):
        user_id = message.from_user.id
        user_data[user_id]['child_name'] = message.text
        
        # Предлагаем ввести номер телефона или поделиться контактом
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        phone_button = telebot.types.KeyboardButton("📱 Поделиться номером", request_contact=True)
        markup.add(phone_button)
        markup.add("Ввести вручную")
        
        msg = bot.send_message(message.chat.id, "Введите ваш номер телефона или поделитесь контактом:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_phone_input)

    def process_phone_input(message):
        user_id = message.from_user.id
        if message.contact:  # Если пользователь поделился контактом
            user_data[user_id]['phone'] = message.contact.phone_number
            # Переходим к подтверждению данных
            show_confirmation(message)
        elif message.text == "Ввести вручную":
            msg = bot.send_message(message.chat.id, "Введите ваш номер телефона:", reply_markup=telebot.types.ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, process_manual_phone_input)
        else:
            user_data[user_id]['phone'] = message.text
            # Переходим к подтверждению данных
            show_confirmation(message)
    
    def process_manual_phone_input(message):
        user_id = message.from_user.id
        user_data[user_id]['phone'] = message.text
        # Переходим к подтверждению данных
        show_confirmation(message)
    
    def show_confirmation(message):
        user_id = message.from_user.id
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
        """Обрабатывает подтверждение записи"""
        user_id = message.from_user.id
        
        if message.text == "Да, всё верно":
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
            
            # Сохраняем запись с полем подтверждения
            booking = {
                "user_id": user_id,
                "parent_name": user_data[user_id]['parent_name'],
                "child_name": user_data[user_id]['child_name'],
                "phone": user_data[user_id]['phone'],
                "date": user_data[user_id]['selected_date'],
                "time": user_data[user_id]['selected_time'],
                "timestamp": datetime.now().isoformat(),
                "confirmed": False  # По умолчанию не подтверждена
            }
            
            data.save_booking(booking)
            
            bot.send_message(
                message.chat.id, 
                f"✅ Вы успешно записаны!\n\n"
                f"Дата: {user_data[user_id]['selected_date']}\n"
                f"Время: {user_data[user_id]['selected_time']}\n\n"
                f"Напоминание придет за день до занятия. "
                f"Пожалуйста, подтвердите участие по кнопке в напоминании.",
                reply_markup=telebot.types.ReplyKeyboardRemove()
            )
        else:
            bot.send_message(
                message.chat.id, 
                "Запись отменена.", 
                reply_markup=telebot.types.ReplyKeyboardRemove()
            )
    
    def show_available_dates(message):
        """Показывает доступные даты для записи"""
        slots = data.load_slots()
        available_dates = []
        
        # Фильтруем даты, оставляя только те, где есть доступные слоты
        for date, date_slots in slots.items():
            # Проверяем, есть ли доступные слоты (available = True)
            available_slots = [slot for slot in date_slots if slot.get('available', True)]
            if available_slots:  # Если есть хотя бы один доступный слот
                available_dates.append(date)
        
        if not available_dates:
            bot.send_message(message.chat.id, "К сожалению, пока нет доступных дат для записи.", reply_markup=telebot.types.ReplyKeyboardRemove())
            return
        
        # Сортируем даты
        try:
            available_dates.sort(key=lambda x: datetime.strptime(x, "%d.%m.%Y"))
        except:
            pass  # Если не удалось отсортировать, оставляем как есть
        
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
        
        # Сортируем слоты по времени
        def time_sort_key(time_str):
            try:
                hour = int(time_str.split(':')[0])
                return hour
            except:
                return 99  # Если не удалось распарсить, ставим в конец
        
        available_slots.sort(key=time_sort_key)
        
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
        bot.register_next_step_handler(msg, process_confirmation_step)
    
    @bot.message_handler(func=lambda message: message.text == "📅 Мои записи")
    def view_my_bookings(message):
        """Просмотр записей клиента"""
        user_id = message.from_user.id
        bookings = data.load_bookings()
        
        # Находим записи пользователя
        user_bookings = [b for b in bookings if b['user_id'] == user_id and not b.get('cancelled_by_user', False)]
        
        if not user_bookings:
            bot.send_message(
                message.chat.id, 
                "У вас нет активных записей.", 
                reply_markup=telebot.types.ReplyKeyboardRemove()
            )
            return
        
        response = "📅 Ваши записи на занятия:\n\n"
        for booking in user_bookings:
            # Проверяем, не был ли слот удален администратором
            slots = data.load_slots()
            slot_exists = False
            slot_available = True
            
            if booking['date'] in slots:
                for slot in slots[booking['date']]:
                    if slot['time'] == booking['time']:
                        slot_exists = True
                        slot_available = slot.get('available', True)
                        break
            
            status = ""
            if not slot_exists:
                status = " (⚠️ Слот удален администратором)"
            elif not slot_available:
                if booking.get('confirmed', False):
                    status = " (✅ Подтверждена)"
                else:
                    status = " (⏰ Ожидает подтверждения)"
            else:
                status = " (❓ Статус неопределен)"
            
            response += f"📅 {booking['date']} {booking['time']}\n"
            response += f"👶 {booking['child_name']}\n"
            response += f"{status}\n"
            response += "➖➖➖➖➖\n"
        
        bot.send_message(message.chat.id, response, reply_markup=telebot.types.ReplyKeyboardRemove())
    
    @bot.message_handler(func=lambda message: message.text == "❌ Отменить запись")
    def cancel_booking(message):
        """Отмена записи"""
        user_id = message.from_user.id
        bookings = data.load_bookings()
        
        # Находим записи пользователя (только не отмененные)
        user_bookings = [b for b in bookings if b['user_id'] == user_id and not b.get('cancelled_by_user', False)]
        
        if not user_bookings:
            bot.send_message(
                message.chat.id, 
                "У вас нет активных записей.", 
                reply_markup=telebot.types.ReplyKeyboardRemove()
            )
            return
        
        # Создаем inline клавиатуру с записями пользователя
        markup = telebot.types.InlineKeyboardMarkup()
        for i, booking in enumerate(user_bookings):
            button_text = f"{booking['date']} {booking['time']} - {booking['child_name']}"
            callback_data = f"cancel_{i}_{user_id}"  # Добавляем user_id для безопасности
            markup.add(telebot.types.InlineKeyboardButton(button_text, callback_data=callback_data))
        
        bot.send_message(
            message.chat.id, 
            "Выберите запись для отмены:", 
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
    def process_cancel_callback(call):
        """Обработка нажатия на кнопку отмены записи"""
        try:
            parts = call.data.split('_')
            if len(parts) >= 3:
                index = int(parts[1])
                booking_user_id = int(parts[2])
                
                # Проверяем, что пользователь пытается отменить свою запись
                if call.from_user.id != booking_user_id:
                    bot.answer_callback_query(call.id, "Ошибка: вы можете отменять только свои записи")
                    return
                
                bookings = data.load_bookings()
                user_bookings = [b for b in bookings if b['user_id'] == booking_user_id and not b.get('cancelled_by_user', False)]
                
                if index < len(user_bookings):
                    booking_to_cancel = user_bookings[index]
                    
                    # Отмечаем слот как доступный
                    slots = data.load_slots()
                    date = booking_to_cancel['date']
                    time = booking_to_cancel['time']
                    
                    if date in slots:
                        for slot in slots[date]:
                            if slot['time'] == time:
                                slot['available'] = True
                                break
                    
                    data.save_slots(slots)
                    
                    # Помечаем запись как отмененную пользователем
                    for booking in bookings:
                        if (booking['user_id'] == booking_user_id and 
                            booking['date'] == booking_to_cancel['date'] and 
                            booking['time'] == booking_to_cancel['time']):
                            booking['cancelled_by_user'] = True
                            break
                    
                    data.save_bookings(bookings)
                    
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f"✅ Запись отменена:\n{booking_to_cancel['date']} {booking_to_cancel['time']}\n{booking_to_cancel['child_name']}"
                    )
                else:
                    bot.answer_callback_query(call.id, "Ошибка: запись не найдена")
            else:
                bot.answer_callback_query(call.id, "Ошибка: некорректные данные")
                    
        except Exception as e:
            bot.answer_callback_query(call.id, "Ошибка при отмене записи")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_') or call.data.startswith('cancel_reminder_'))
    def process_reminder_callback(call):
        """Обработка нажатий на кнопки подтверждения в напоминаниях"""
        try:
            if call.data.startswith('confirm_'):
                # Разбираем данные подтверждения
                parts = call.data.split('_')
                if len(parts) >= 4:
                    user_id = int(parts[1])
                    date = parts[2]
                    time_slot = '_'.join(parts[3:])  # Объединяем оставшиеся части
                    
                    # Проверяем, что пользователь подтверждает свою запись
                    if call.from_user.id != user_id:
                        bot.answer_callback_query(call.id, "Ошибка: вы можете подтверждать только свои записи")
                        return
                    
                    # Обновляем статус записи (добавляем подтверждение)
                    bookings = data.load_bookings()
                    booking_found = False
                    
                    for booking in bookings:
                        if (booking['user_id'] == user_id and 
                            booking['date'] == date and 
                            booking['time'] == time_slot):
                            booking['confirmed'] = True
                            booking_found = True
                            break
                    
                    if booking_found:
                        data.save_bookings(bookings)
                        bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=f"✅ Запись подтверждена!\n\n"
                                 f"Дата: {date}\n"
                                 f"Время: {time_slot}\n\n"
                                 f"Спасибо за подтверждение!"
                        )
                    else:
                        bot.answer_callback_query(call.id, "Ошибка: запись не найдена")
                else:
                    bot.answer_callback_query(call.id, "Ошибка: некорректные данные")
            
            elif call.data.startswith('cancel_reminder_'):
                # Разбираем данные отмены
                parts = call.data.split('_')
                if len(parts) >= 4:
                    user_id = int(parts[2])
                    date = parts[3]
                    time_slot = '_'.join(parts[4:])  # Объединяем оставшиеся части
                    
                    # Проверяем, что пользователь отменяет свою запись
                    if call.from_user.id != user_id:
                        bot.answer_callback_query(call.id, "Ошибка: вы можете отменять только свои записи")
                        return
                    
                    # Отмечаем слот как доступный
                    slots = data.load_slots()
                    slot_found = False
                    if date in slots:
                        for slot in slots[date]:
                            if slot['time'] == time_slot:
                                slot['available'] = True
                                slot_found = True
                                break
                    
                    if slot_found:
                        data.save_slots(slots)
                    
                    # Помечаем запись как отмененную пользователем
                    bookings = data.load_bookings()
                    booking_found = False
                    for booking in bookings:
                        if (booking['user_id'] == user_id and 
                            booking['date'] == date and 
                            booking['time'] == time_slot):
                            booking['cancelled_by_user'] = True
                            booking_found = True
                            break
                    
                    if booking_found:
                        data.save_bookings(bookings)
                        bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=f"❌ Запись отменена по вашему запросу:\n\n"
                                 f"Дата: {date}\n"
                                 f"Время: {time_slot}"
                        )
                    else:
                        bot.answer_callback_query(call.id, "Ошибка: запись не найдена")
                else:
                    bot.answer_callback_query(call.id, "Ошибка: некорректные данные")
                    
        except Exception as e:
            bot.answer_callback_query(call.id, f"Ошибка при обработке: {str(e)}")
