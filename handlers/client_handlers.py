import telebot
from datetime import datetime, date, timedelta
import data
import json
import re  # Для проверки номера телефона

# Хранилище временных данных пользователей
temp_user_data = {}

def set_temp_data(user_id, key, value):
    """Установка временных данных пользователя"""
    if user_id not in temp_user_data:
        temp_user_data[user_id] = {}
    temp_user_data[user_id][key] = value

def get_temp_data(user_id, key, default=None):
    """Получение временных данных пользователя"""
    if user_id in temp_user_data and key in temp_user_data[user_id]:
        return temp_user_data[user_id][key]
    return default

def clear_temp_data(user_id):
    """Очистка временных данных пользователя"""
    if user_id in temp_user_data:
        del temp_user_data[user_id]

def register_client_handlers(bot, admin_ids_list):
    """Регистрирует обработчики для клиентов"""
    admin_ids = admin_ids_list
    
    def is_admin(user_id):
        """Проверяет, является ли пользователь администратором"""
        return str(user_id) in admin_ids

    def get_chat_and_message_id_from_call_or_msg(call=None, message=None):
        """Возвращает chat_id и message_id из callback или message"""
        if call:
            return call.message.chat.id, call.message.message_id
        elif message:
            return message.chat.id, None
        return None, None

    def send_or_edit_message(chat_id, message_id, text, reply_markup=None, call=None, message=None):
        """Отправляет или редактирует сообщение в зависимости от типа вызова"""
        try:
            if message_id:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
            else:
                bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
            print(f"Сообщение отправлено/отредактировано в чат {chat_id}") # Лог
        except Exception as e:
            print(f"Ошибка при отправке/редактировании сообщения: {e}") # Лог ошибки
            import traceback
            traceback.print_exc() # Печатает полный traceback

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_id = message.from_user.id

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📝 Записаться на занятие", callback_data="book_lesson"))
        markup.add(telebot.types.InlineKeyboardButton("📅 Мои записи", callback_data="my_bookings"))
        markup.add(telebot.types.InlineKeyboardButton("📥 Мои ДЗ", callback_data="my_homework")) # <-- Новая кнопка
        markup.add(telebot.types.InlineKeyboardButton("❌ Отменить запись", callback_data="cancel_booking"))
        markup.add(telebot.types.InlineKeyboardButton("📖 Помощь", callback_data="help"))

        # Заменяем bot.reply_to на bot.send_message
        bot.send_message(
            message.chat.id,
            "Привет! Я бот для записи на занятия и получения домашних заданий.\nВыберите действие:",
            reply_markup=markup
        )

    @bot.message_handler(commands=['help', 'client_help'])
    def client_help_handler(message):
        """Помощь для клиентов"""
        help_text = """
📖 Доступные команды для клиентов:

/start - Главное меню
/help - Помощь по командам

📝 Как записаться на занятие:
1. Нажмите "📝 Записаться на занятие"
2. Выберите дату и время
3. Введите свои данные
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
        client_help_handler(message)

    @bot.message_handler(func=lambda message: message.text == "📱 Меню")
    def show_menu(message):
        send_welcome(message)

    def start_booking_call(call):
        user_id = call.from_user.id
        try:
            bot.delete_message(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
        except:
            pass

        slots = data.load_slots()
        has_available_slots = False
        today = date.today()

        for date_str, date_slots in slots.items():
            try:
                slot_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                if slot_date >= today:
                    available_slots = [slot for slot in date_slots if slot.get('available', True) and not slot.get('deleted_by_admin', False)]
                    if available_slots:
                        has_available_slots = True
                        break
            except ValueError:
                continue

        if not has_available_slots:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))
            send_or_edit_message(
                call.message.chat.id, None, 
                "К сожалению, пока нет свободных слотов для записи.\nПожалуйста, попробуйте позже.",
                reply_markup=markup, call=call
            )
            return

        show_available_dates_first_step(call.message)

    def show_available_dates_first_step(message):
        user_id = message.from_user.id
        slots = data.load_slots()
        available_dates = []

        today = date.today()

        for date_str, date_slots in slots.items():
            try:
                slot_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                if slot_date >= today:
                    available_slots = [slot for slot in date_slots if slot.get('available', True)]
                    if available_slots:
                        available_dates.append(date_str)
            except ValueError:
                continue

        if not available_dates:
            # Убираем ReplyKeyboardRemove
            bot.send_message(message.chat.id, "К сожалению, пока нет доступных дат для записи.")
            return

        try:
            available_dates.sort(key=lambda x: datetime.strptime(x, "%d.%m.%Y"))
        except:
            pass

        markup = telebot.types.InlineKeyboardMarkup()
        for date_str in available_dates[:7]:
            markup.add(telebot.types.InlineKeyboardButton(date_str, callback_data=f"select_date_{date_str}"))

        markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))

        bot.send_message(message.chat.id, "Выберите дату для записи:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('select_date_'))
    def process_date_selection_first_step(call):
        try:
            selected_date = call.data.replace('select_date_', '')
            user_id = call.from_user.id

            slots = data.load_slots()
            available_slots = []

            if selected_date in slots:
                for slot in slots[selected_date]:
                    if slot.get('available', True):
                        available_slots.append(slot['time'])

            if not available_slots:
                bot.answer_callback_query(call.id, "На эту дату нет доступных слотов")
                return

            def time_sort_key(time_str):
                try:
                    hour = int(time_str.split(':')[0])
                    return hour
                except:
                    return 99

            available_slots.sort(key=time_sort_key)

            markup = telebot.types.InlineKeyboardMarkup()
            for slot in available_slots:
                markup.add(telebot.types.InlineKeyboardButton(slot, callback_data=f"select_time_{selected_date}_{slot}"))

            markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="book_lesson"))

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Выберите время для записи на {selected_date}:",
                reply_markup=markup
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            print(f"Ошибка при выборе даты: {e}")
            bot.answer_callback_query(call.id, "Ошибка при выборе даты")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('select_time_'))
    def process_time_selection_first_step(call):
        try:
            parts = call.data.split('_', 2)
            if len(parts) != 3:
                bot.answer_callback_query(call.id, "Ошибка: некорректные данные")
                return

            selected_date = parts[2].split('_', 1)[0]
            selected_time = parts[2].split('_', 1)[1]

            user_id = call.from_user.id
            set_temp_data(user_id, 'booking_date', selected_date)
            set_temp_data(user_id, 'booking_time', selected_time)

            bot.answer_callback_query(call.id, "Отлично! Теперь введите ваши данные.")

            msg = bot.send_message(
                chat_id=call.message.chat.id,
                text="Для завершения записи, пожалуйста, представьтесь.\nВведите вашу фамилию и имя:"
            )

            bot.register_next_step_handler(msg, process_parent_name_step_v2)
        except Exception as e:
            print(f"Ошибка при выборе времени: {e}")
            bot.answer_callback_query(call.id, "Ошибка при выборе времени")

    def process_parent_name_step_v2(message):
        user_id = message.from_user.id
        parent_name = message.text
        set_temp_data(user_id, 'temp_parent_name', parent_name)

        msg = bot.send_message(message.chat.id, "Введите фамилию и имя ребенка:")
        bot.register_next_step_handler(msg, process_child_name_step_v2)

    def process_child_name_step_v2(message):
        user_id = message.from_user.id
        child_name = message.text
        set_temp_data(user_id, 'temp_child_name', child_name)

        msg = bot.send_message(message.chat.id, "Введите ваш номер телефона, или прикрепите его из телефонной книги:")
        # Регистрируем ОДНУ функцию, которая сама разберётся
        bot.register_next_step_handler(msg, process_phone_input_or_contact)

    def process_phone_input_or_contact(message):
        user_id = message.from_user.id
        phone_input = None

        if message.contact:
            # Если это контакт, используем номер из контакта
            phone_input = message.contact.phone_number
        elif message.text:
            # Если это текст, проверяем его
            phone_input = message.text
        else:
            # Если ни то, ни другое
            msg = bot.send_message(message.chat.id, "Пожалуйста, введите номер телефона или поделитесь контактом.")
            bot.register_next_step_handler(msg, process_phone_input_or_contact)
            return

        # Теперь phone_input — это строка (если всё прошло успешно)
        # Проверяем формат
        if not re.match(r'^[\d\s\+\-\(\)]+$', phone_input):
            msg = bot.send_message(message.chat.id, "Некорректный формат номера. Пожалуйста, введите только цифры и специальные символы (+, -, (, ), пробел).")
            bot.register_next_step_handler(msg, process_phone_input_or_contact)
            return

        # Убираем лишние символы, оставляем только цифры (для проверки длины и т.д.)
        clean_phone = re.sub(r'\D', '', phone_input)

        # Пример: проверим минимальную длину
        if len(clean_phone) < 10:
            msg = bot.send_message(message.chat.id, "Номер телефона слишком короткий. Пожалуйста, введите корректный номер.")
            bot.register_next_step_handler(msg, process_phone_input_or_contact)
            return

        set_temp_data(user_id, 'temp_phone', phone_input)
        show_final_confirmation_v2(message)

    # --- НОВАЯ ФУНКЦИЯ С ПРОВЕРКОЙ НОМЕРА ---
    def process_manual_phone_v2(message):
        user_id = message.from_user.id
        phone_input = message.text

        # Проверяем, что ввод содержит только цифры, +, -, (, ), и пробелы
        if not re.match(r'^[\d\s\+\-\(\)]+$', phone_input):
            msg = bot.send_message(message.chat.id, "Некорректный формат номера. Пожалуйста, введите только цифры и специальные символы (+, -, (, ), пробел).")
            bot.register_next_step_handler(msg, process_manual_phone_v2)
            return

        # Убираем лишние символы, оставляем только цифры (для проверки длины и т.д.)
        clean_phone = re.sub(r'\D', '', phone_input)

        # Пример: проверим минимальную длину
        if len(clean_phone) < 10:
            msg = bot.send_message(message.chat.id, "Номер телефона слишком короткий. Пожалуйста, введите корректный номер.")
            bot.register_next_step_handler(msg, process_manual_phone_v2)
            return

        set_temp_data(user_id, 'temp_phone', phone_input)
        show_final_confirmation_v2(message)

    def show_final_confirmation_v2(message):
        user_id = message.from_user.id
        selected_date = get_temp_data(user_id, 'booking_date')
        selected_time = get_temp_data(user_id, 'booking_time')
        parent_name = get_temp_data(user_id, 'temp_parent_name')
        child_name = get_temp_data(user_id, 'temp_child_name')
        phone = get_temp_data(user_id, 'temp_phone')

        if not all([selected_date, selected_time, parent_name, child_name, phone]):
            bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните сначала.")
            return

        confirmation_text = f"Подтвердите запись:\n\n"
        confirmation_text += f"Дата: {selected_date}\n"
        confirmation_text += f"Время: {selected_time}\n"
        confirmation_text += f"Ваше имя: {parent_name}\n"
        confirmation_text += f"Имя ребенка: {child_name}\n"
        confirmation_text += f"Телефон: {phone}\n\n"
        confirmation_text += "Всё верно?"

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_booking"))
        markup.add(telebot.types.InlineKeyboardButton("❌ Отмена", callback_data="main_menu"))

        bot.send_message(message.chat.id, confirmation_text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "confirm_booking")
    def process_final_confirmation(call):
        try:
            user_id = call.from_user.id
            print(f"Подтверждение записи для пользователя: {user_id}")

            selected_date = get_temp_data(user_id, 'booking_date')
            selected_time = get_temp_data(user_id, 'booking_time')
            parent_name = get_temp_data(user_id, 'temp_parent_name')
            child_name = get_temp_data(user_id, 'temp_child_name')
            phone = get_temp_data(user_id, 'temp_phone')

            print(f"Данные для записи: дата={selected_date}, время={selected_time}, имя={parent_name}, ребенок={child_name}, телефон={phone}")

            if not all([selected_date, selected_time, parent_name, child_name, phone]):
                bot.answer_callback_query(call.id, "Ошибка: данные не найдены")
                return

            # --- НОВОЕ: Сохраняем пользователя в БД ПЕРЕД созданием записи ---
            data.save_user(user_id, parent_name, phone)
            # ----------------------------------------------------------------

            slots = data.load_slots()

            if selected_date in slots:
                for slot in slots[selected_date]:
                    if slot['time'] == selected_time:
                        slot['available'] = False
                        break

            data.save_slots(slots)

            booking = {
                "user_id": user_id,
                "parent_name": parent_name, # Это поле не используется в save_booking, но оставим для совместимости
                "child_name": child_name,
                "phone": phone, # Это поле не используется в save_booking, но оставим для совместимости
                "date": selected_date,
                "time": selected_time,
                "timestamp": datetime.now().isoformat(),
                "confirmed": False
            }

            data.save_booking(booking)
            print(f"Запись сохранена: {booking}")

            clear_temp_data(user_id)

            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ Вы успешно записаны!\n\n"
                    f"Дата: {selected_date}\n"
                    f"Время: {selected_time}\n\n"
                    f"Напоминание придет за день до занятия.",
                reply_markup=markup
            )

            bot.answer_callback_query(call.id)

        except Exception as e:
            print(f"Ошибка при подтверждении записи: {e}")
            import traceback
            traceback.print_exc()
            bot.answer_callback_query(call.id, "Ошибка при подтверждении записи")

    @bot.callback_query_handler(func=lambda call: call.data in ['book_lesson', 'my_bookings', 'cancel_booking', 'help'])
    def process_main_menu_callback(call):
        try:
            print(f"Callback received: {call.data} from user: {call.from_user.id}")
            if call.data == 'book_lesson':
                start_booking_call(call)
            elif call.data == 'my_bookings':
                view_my_bookings_call(call)
            elif call.data == 'cancel_booking':
                cancel_booking_callback_version(call)
            elif call.data == 'help':
                client_help_call(call)
            bot.answer_callback_query(call.id)
        except Exception as e:
            print(f"Error in main menu callback: {e}")
            bot.answer_callback_query(call.id, "Ошибка при обработке запроса")

    def view_my_bookings_call(call):
        """Просмотр записей через callback"""
        user_id = call.from_user.id
        print(f"View bookings call from user: {user_id}")

        bookings = data.load_bookings()
        print(f"Всего записей в системе: {len(bookings)}")

        user_bookings = [b for b in bookings if b['user_id'] == user_id and not b.get('cancelled_by_user', False)]
        print(f"Записей пользователя {user_id}: {len(user_bookings)}")

        if not user_bookings:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))

            send_or_edit_message(
                call.message.chat.id, call.message.message_id,
                "У вас нет активных записей.",
                reply_markup=markup, call=call
            )
            return

        response = "📅 Ваши записи на занятия:\n\n"
        for booking in user_bookings:
            print(f"Запись: {booking}")
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
            if booking.get('cancelled_by_admin', False):
                status = " (🚫 Запись отменена администратором)"
            elif not slot_exists:
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

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))

        send_or_edit_message(
            call.message.chat.id, call.message.message_id,
            response,
            reply_markup=markup, call=call
        )

    def cancel_booking_call(call):
        cancel_booking_callback_version(call)

    def client_help_call(call):
        message = call.message
        client_help_handler(message)

    @bot.callback_query_handler(func=lambda call: call.data == "main_menu")
    def process_main_menu_return(call):
        try:
            send_welcome(call.message)
            bot.answer_callback_query(call.id)
        except Exception as e:
            bot.answer_callback_query(call.id, "Ошибка при возврате в меню")

    @bot.message_handler(func=lambda message: message.text == "📅 Мои записи")
    def view_my_bookings(message):
        """Просмотр записей клиента"""
        user_id = message.from_user.id
        print(f"Просмотр записей для пользователя {user_id}")

        bookings = data.load_bookings()
        print(f"Всего записей в системе: {len(bookings)}")

        user_bookings = [b for b in bookings if b['user_id'] == user_id and not b.get('cancelled_by_user', False)]
        print(f"Записей пользователя {user_id}: {len(user_bookings)}")

        if not user_bookings:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))

            bot.send_message(
                message.chat.id, 
                "У вас нет активных записей.", 
                reply_markup=markup
            )
            return

        response = "📅 Ваши записи на занятия:\n\n"
        for booking in user_bookings:
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
            if booking.get('cancelled_by_admin', False):
                status = " (🚫 Запись отменена администратором)"
            elif not slot_exists:
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

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))

        bot.send_message(
            message.chat.id, 
            response, 
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data == "my_homework")
    def client_view_homework_call(call):
        """Показывает клиенту его домашние задания."""
        user_id = call.from_user.id
        print(f"client_view_homework_call вызвана для пользователя: {user_id}")

        homeworks = data.load_homeworks_for_user(user_id)

        if not homeworks:
            send_or_edit_message(
                call.message.chat.id,
                call.message.message_id,
                "У вас пока нет домашних заданий.",
                reply_markup=telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))
            )
            return

        response = "📚 Ваши домашние задания:\n\n"
        for hw in homeworks:
            # Загружаем информацию о записи, чтобы показать дату и время занятия
            all_bookings = data.load_bookings()
            booking = next((b for b in all_bookings if b['id'] == hw['booking_id']), None)
            date_time_str = f"{booking['date']} {booking['time']}" if booking else "Неизвестное занятие"
            response += f"📅 Занятие: {date_time_str}\n"
            response += f"📅 Отправлено: {hw['sent_at']}\n"
            if hw['comment']:
                response += f"📝 Комментарий: {hw['comment']}\n"
            response += "➖➖➖➖➖\n"

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))

        send_or_edit_message(
            call.message.chat.id,
            call.message.message_id,
            response,
            reply_markup=markup
        )

        bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda message: message.text == "❌ Отменить запись")
    def cancel_booking(message):
        user_id = message.from_user.id
        bookings = data.load_bookings()

        user_bookings = [b for b in bookings if b['user_id'] == user_id and not b.get('cancelled_by_user', False)]

        if not user_bookings:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))

            bot.send_message(
                message.chat.id, 
                "У вас нет активных записей.", 
                reply_markup=markup
            )
            return

        markup = telebot.types.InlineKeyboardMarkup()
        for i, booking in enumerate(user_bookings):
            button_text = f"{booking['date']} {booking['time']} - {booking['child_name']}"
            callback_data = f"cancel_{i}_{user_id}"
            markup.add(telebot.types.InlineKeyboardButton(button_text, callback_data=callback_data))

        markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))

        bot.send_message(
            message.chat.id, 
            "Выберите запись для отмены:", 
            reply_markup=markup
        )

    def cancel_booking_callback_version(call):
        user_id = call.from_user.id
        print(f"Отмена записей для пользователя {user_id}")

        bookings = data.load_bookings()
        print(f"Всего записей в системе: {len(bookings)}")

        slots = data.load_slots()
        user_bookings = [
            b for b in bookings
            if (
                b['user_id'] == user_id and
                not b.get('cancelled_by_user', False) and
                not b.get('cancelled_by_admin', False)
            )
        ]

        active_user_bookings = []
        for b in user_bookings:
            slot_exists = False
            if b['date'] in slots:
                for slot in slots[b['date']]:
                    if slot['time'] == b['time']:
                        slot_exists = True
                        break
            if slot_exists:
                active_user_bookings.append(b)

        print(f"Активных записей пользователя {user_id}: {len(active_user_bookings)}")

        if not active_user_bookings:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))

            send_or_edit_message(
                call.message.chat.id, call.message.message_id,
                "У вас нет активных записей.",
                reply_markup=markup, call=call
            )
            return

        markup = telebot.types.InlineKeyboardMarkup()
        for i, booking in enumerate(active_user_bookings):
            button_text = f"{booking['date']} {booking['time']} - {booking['child_name']}"
            callback_data = f"cancel_{i}_{user_id}"
            markup.add(telebot.types.InlineKeyboardButton(button_text, callback_data=callback_data))

        markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))

        send_or_edit_message(
            call.message.chat.id, call.message.message_id,
            "Выберите запись для отмены:",
            reply_markup=markup, call=call
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
    def process_cancel_callback(call):
        try:
            print(f"Process cancel callback: {call.data} from user: {call.from_user.id}")
            parts = call.data.split('_')
            if len(parts) >= 3:
                index = int(parts[1])
                booking_user_id = int(parts[2])

                if call.from_user.id != booking_user_id:
                    bot.answer_callback_query(call.id, "Ошибка: вы можете отменять только свои записи")
                    return

                bookings = data.load_bookings()
                user_bookings = [b for b in bookings if b['user_id'] == booking_user_id and not b.get('cancelled_by_user', False) and not b.get('cancelled_by_admin', False)]
                print(f"Найдено {len(user_bookings)} записей пользователя для отмены")

                if index < len(user_bookings):
                    booking_to_cancel = user_bookings[index]
                    print(f"Отмена записи: {booking_to_cancel}")

                    slots = data.load_slots()
                    date = booking_to_cancel['date']
                    time = booking_to_cancel['time']

                    slot_found = False
                    if date in slots:
                        for slot in slots[date]:
                            if slot['time'] == time:
                                slot['available'] = True
                                slot_found = True
                                break

                    if slot_found:
                        data.save_slots(slots)

                    for booking in bookings:
                        if (booking['user_id'] == booking_user_id and 
                            booking['date'] == booking_to_cancel['date'] and 
                            booking['time'] == booking_to_cancel['time']):
                            booking['cancelled_by_user'] = True
                            break

                    data.save_bookings(bookings)

                    markup = telebot.types.InlineKeyboardMarkup()
                    markup.add(telebot.types.InlineKeyboardButton("📱 Главное меню", callback_data="main_menu"))

                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f"✅ Запись отменена:\n{booking_to_cancel['date']} {booking_to_cancel['time']}\n{booking_to_cancel['child_name']}\n\nСлот освобожден.",
                        reply_markup=markup
                    )
                else:
                    bot.answer_callback_query(call.id, "Ошибка: запись не найдена")
            else:
                bot.answer_callback_query(call.id, "Ошибка: некорректные данные")

        except Exception as e:
            print(f"Ошибка при отмене записи: {e}")
            import traceback
            traceback.print_exc()
            bot.answer_callback_query(call.id, "Ошибка при отмене записи")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_') or call.data.startswith('cancel_reminder_'))
    def process_reminder_callback(call):
        try:
            if call.data.startswith('confirm_'):
                parts = call.data.split('_', 2)
                if len(parts) < 3:
                    bot.answer_callback_query(call.id, "Ошибка: некорректные данные")
                    return

                user_id = int(parts[1])
                date = parts[2]
                time_slot = parts[3] if len(parts) > 3 else "_".join(parts[3:])

                if call.from_user.id != user_id:
                    bot.answer_callback_query(call.id, "Ошибка: вы можете подтверждать только свои записи")
                    return

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

            elif call.data.startswith('cancel_reminder_'):
                parts = call.data.split('_', 3)
                if len(parts) < 4:
                    bot.answer_callback_query(call.id, "Ошибка: некорректные данные")
                    return

                user_id = int(parts[2])
                date = parts[3]
                time_slot = parts[4] if len(parts) > 4 else "_".join(parts[4:])

                if call.from_user.id != user_id:
                    bot.answer_callback_query(call.id, "Ошибка: вы можете отменять только свои записи")
                    return

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

        except Exception as e:
            bot.answer_callback_query(call.id, f"Ошибка при обработке: {str(e)}")