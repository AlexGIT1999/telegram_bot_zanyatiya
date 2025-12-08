import telebot
import data
from datetime import datetime, timedelta

def register_admin_handlers(bot, admin_ids_list):
    """Регистрирует обработчики для администраторов"""
    # Сохраняем список админов в замыкании
    admin_ids = admin_ids_list
    
    def is_admin(user_id):
        """Проверяет, является ли пользователь администратором"""
        return str(user_id) in admin_ids
    
    @bot.message_handler(commands=['admin'])
    def admin_panel(message):
        user_id = message.from_user.id
        if is_admin(user_id):
            show_admin_menu(message)
        else:
            bot.send_message(message.chat.id, "У вас нет доступа к админской панели.")
    
    @bot.message_handler(commands=['admin_help'])
    def admin_help_handler(message):
        """Помощь для администраторов"""
        if is_admin(message.from_user.id):
            admin_help(message)
        else:
            bot.send_message(message.chat.id, "У вас нет доступа к админской помощи.")
    
    def admin_help(message):
        """Помощь для администраторов"""
        if is_admin(message.from_user.id):
            help_text = """
👑 Команды администратора:

/admin - Вход в админскую панель
/admin_help - Помощь по командам админа

📅 Управление слотами:
- Добавление слотов: указать дату и временной диапазон
- Просмотр всех слотов и их статусов
- Удаление слотов

👥 Просмотр записей:
- Все активные записи клиентов
- Данные клиентов (имя, телефон, Telegram ID)

📊 Аналитика:
- Статистика по записям за периоды
- Подтверждения и отмены
"""
            bot.send_message(message.chat.id, help_text)
        else:
            bot.send_message(message.chat.id, "У вас нет доступа к админской помощи.")
    
    @bot.message_handler(func=lambda message: message.text == "📅 Управление слотами" and is_admin(message.from_user.id))
    def admin_manage_slots(message):
        """Админ: управление слотами"""
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Добавить слоты")
        markup.add("📋 Просмотр слотов")
        markup.add("🗑️ Удалить слоты")
        markup.add("🔙 Назад")
        
        bot.send_message(
            message.chat.id, 
            "Управление слотами для записи", 
            reply_markup=markup
        )
    
    @bot.message_handler(func=lambda message: message.text == "➕ Добавить слоты" and is_admin(message.from_user.id))
    def admin_add_slots(message):
        """Админ: добавление слотов"""
        msg = bot.send_message(
            message.chat.id, 
            "Введите дату в формате ДД.ММ.ГГГГ (например, 25.12.2025):"
        )
        bot.register_next_step_handler(msg, process_admin_date_input)
    
    def process_admin_date_input(message):
        """Обработка ввода даты админом"""
        try:
            # Проверяем формат даты
            datetime.strptime(message.text, "%d.%m.%Y")
            if message.from_user.id not in bot.user_data:
                bot.user_data[message.from_user.id] = {}
            bot.user_data[message.from_user.id]['admin_date'] = message.text
            
            msg = bot.send_message(
                message.chat.id, 
                "Введите временной диапазон в формате ЧЧ:ММ-ЧЧ:ММ (например, 09:00-14:00):"
            )
            bot.register_next_step_handler(msg, process_admin_time_input)
        except ValueError:
            msg = bot.send_message(
                message.chat.id, 
                "Неверный формат даты. Попробуйте еще раз.\nВведите дату в формате ДД.ММ.ГГГГ:"
            )
            bot.register_next_step_handler(msg, process_admin_date_input)
    
    def process_admin_time_input(message):
        """Обработка ввода времени админом"""
        try:
            start_time, end_time = message.text.split('-')
            datetime.strptime(start_time.strip(), "%H:%M")
            datetime.strptime(end_time.strip(), "%H:%M")
            
            # Разбиваем на часовые слоты
            slots = data.load_slots()
            date = bot.user_data[message.from_user.id]['admin_date']
            
            if date not in slots:
                slots[date] = []
            
            # Создаем часовые слоты
            start_hour = int(start_time.split(':')[0])
            end_hour = int(end_time.split(':')[0])
            
            for hour in range(start_hour, end_hour):
                slot_time = f"{hour:02d}:00-{hour+1:02d}:00"
                # Проверяем, что слот еще не существует
                slot_exists = False
                for existing_slot in slots[date]:
                    if existing_slot['time'] == slot_time:
                        slot_exists = True
                        break
                
                if not slot_exists:
                    slots[date].append({
                        'time': slot_time,
                        'available': True
                    })
            
            data.save_slots(slots)
            
            # Формируем список добавленных слотов
            added_slots = []
            for hour in range(start_hour, end_hour):
                slot_time = f"{hour:02d}:00-{hour+1:02d}:00"
                added_slots.append(slot_time)
            
            bot.send_message(
                message.chat.id, 
                f"✅ Слоты добавлены на {date}:\n" + "\n".join(added_slots),
                reply_markup=telebot.types.ReplyKeyboardRemove()
            )
            
            # Возвращаем в админское меню
            show_admin_menu(message)
            
        except ValueError:
            msg = bot.send_message(
                message.chat.id, 
                "Неверный формат времени. Попробуйте еще раз.\nВведите временной диапазон в формате ЧЧ:ММ-ЧЧ:ММ:"
            )
            bot.register_next_step_handler(msg, process_admin_time_input)
    
    @bot.message_handler(func=lambda message: message.text == "📋 Просмотр слотов" and is_admin(message.from_user.id))
    def admin_view_slots(message):
        """Админ: просмотр слотов"""
        slots = data.load_slots()
        
        if not slots:
            bot.send_message(message.chat.id, "Нет созданных слотов.", reply_markup=telebot.types.ReplyKeyboardRemove())
            show_admin_menu(message)
            return
        
        response = "📅 Доступные слоты:\n\n"
        for date, date_slots in slots.items():
            response += f"📅 {date}:\n"
            for slot in date_slots:
                status = "✅ Свободен" if slot.get('available', True) else "❌ Занят"
                response += f"  {slot['time']} - {status}\n"
            response += "\n"
        
        bot.send_message(message.chat.id, response, reply_markup=telebot.types.ReplyKeyboardRemove())
        show_admin_menu(message)
    
    @bot.message_handler(func=lambda message: message.text == "🗑️ Удалить слоты" and is_admin(message.from_user.id))
    def admin_delete_slots(message):
        """Админ: удаление слотов"""
        slots = data.load_slots()
        
        if not slots:
            bot.send_message(message.chat.id, "Нет созданных слотов для удаления.", reply_markup=telebot.types.ReplyKeyboardRemove())
            show_admin_menu(message)
            return
        
        # Создаем inline клавиатуру со всеми слотами
        markup = telebot.types.InlineKeyboardMarkup()
        
        for date, date_slots in slots.items():
            # Добавляем заголовок с датой
            markup.add(telebot.types.InlineKeyboardButton(f"📅 {date}", callback_data=f"date_header_{date}"))
            
            # Добавляем кнопки для каждого слота
            for i, slot in enumerate(date_slots):
                slot_text = f"{slot['time']} - {'✅' if slot.get('available', True) else '❌'}"
                callback_data = f"delete_slot_{date}_{i}"
                markup.add(telebot.types.InlineKeyboardButton(slot_text, callback_data=callback_data))
        
        # Добавляем кнопку "Назад"
        markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="delete_back"))
        
        bot.send_message(
            message.chat.id, 
            "Выберите слот для удаления:", 
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
    def process_delete_callback(call):
        """Обработка нажатий в меню удаления слотов"""
        try:
            if call.data == "delete_back":
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Удаление отменено."
                )
                show_admin_menu(call.message)
                return
            
            if call.data.startswith('delete_slot_'):
                # Разбираем данные слота
                parts = call.data.split('_')
                if len(parts) >= 4:
                    date = parts[2]
                    slot_index = int(parts[3])
                    
                    # Загружаем слоты
                    slots = data.load_slots()
                    
                    if date in slots and slot_index < len(slots[date]):
                        deleted_slot = slots[date][slot_index]
                        slot_time = deleted_slot['time']
                        
                        # Удаляем слот
                        del slots[date][slot_index]
                        
                        # Если после удаления в дате не осталось слотов, удаляем дату
                        if not slots[date]:
                            del slots[date]
                        
                        # Сохраняем изменения
                        data.save_slots(slots)
                        
                        bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=f"✅ Слот удален:\nДата: {date}\nВремя: {slot_time}"
                        )
                        
                        # Показываем меню через 2 секунды
                        import time
                        time.sleep(2)
                        show_admin_menu(call.message)
                    else:
                        bot.answer_callback_query(call.id, "Ошибка: слот не найден")
                else:
                    bot.answer_callback_query(call.id, "Ошибка: некорректные данные")
            else:
                bot.answer_callback_query(call.id, "Неизвестная команда")
                    
        except Exception as e:
            bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")
    
    @bot.message_handler(func=lambda message: message.text == "👥 Просмотр записей" and is_admin(message.from_user.id))
    def admin_view_bookings(message):
        """Админ: просмотр записей"""
        bookings = data.load_bookings()
        
        if not bookings:
            bot.send_message(message.chat.id, "Нет записей.", reply_markup=telebot.types.ReplyKeyboardRemove())
            show_admin_menu(message)
            return
        
        response = "👥 Записи на занятия:\n\n"
        for booking in bookings:
            # Пропускаем отмененные записи
            if booking.get('cancelled_by_user', False):
                continue
                
            status = ""
            if booking.get('confirmed', False):
                status = "✅ Подтверждена"
            else:
                status = "⏰ Не подтверждена"
            
            response += f"📅 {booking['date']} {booking['time']}\n"
            response += f"👨 Родитель: {booking['parent_name']}\n"
            response += f"👶 Ребенок: {booking['child_name']}\n"
            response += f"📞 Телефон: {booking['phone']}\n"
            response += f"🆔 ID пользователя: {booking['user_id']}\n"
            response += f"📊 Статус: {status}\n"
            response += "➖➖➖➖➖\n"
        
        bot.send_message(message.chat.id, response, reply_markup=telebot.types.ReplyKeyboardRemove())
        show_admin_menu(message)
    
    @bot.message_handler(func=lambda message: message.text == "📊 Аналитика" and is_admin(message.from_user.id))
    def admin_analytics(message):
        """Админ: аналитика"""
        bookings = data.load_bookings()
        
        if not bookings:
            bot.send_message(message.chat.id, "Нет данных для аналитики.", reply_markup=telebot.types.ReplyKeyboardRemove())
            show_admin_menu(message)
            return
        
        # Подсчет статистики
        total_bookings = len([b for b in bookings if not b.get('cancelled_by_user', False)])
        cancelled_bookings = len([b for b in bookings if b.get('cancelled_by_user', False)])
        
        # Статистика по подтверждениям
        confirmed_bookings = len([b for b in bookings if b.get('confirmed', False) and not b.get('cancelled_by_user', False)])
        unconfirmed_bookings = total_bookings - confirmed_bookings
        
        # Статистика по периодам
        now = datetime.now()
        
        # За последнюю неделю
        week_ago = now - timedelta(days=7)
        week_count = 0
        # За последний месяц
        month_ago = now - timedelta(days=30)
        month_count = 0
        # За последний год
        year_ago = now - timedelta(days=365)
        year_count = 0
        
        # Подсчитываем записи по периодам с обработкой ошибок
        for booking in bookings:
            if booking.get('cancelled_by_user', False):
                continue
                
            try:
                # Пытаемся распарсить timestamp
                timestamp_str = booking['timestamp']
                if timestamp_str.endswith('Z'):
                    booking_datetime = datetime.fromisoformat(timestamp_str[:-1])
                else:
                    # Пытаемся обработать различные форматы
                    try:
                        booking_datetime = datetime.fromisoformat(timestamp_str)
                    except:
                        # Если не удается, пропускаем эту запись
                        continue
                
                if booking_datetime > week_ago:
                    week_count += 1
                if booking_datetime > month_ago:
                    month_count += 1
                if booking_datetime > year_ago:
                    year_count += 1
            except Exception:
                # Пропускаем записи с некорректным форматом даты
                continue
        
        # Топ детей по количеству записей
        children_count = {}
        for booking in bookings:
            if booking.get('cancelled_by_user', False):
                continue
            child_name = booking['child_name']
            children_count[child_name] = children_count.get(child_name, 0) + 1
        
        top_children = sorted(children_count.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Статистика по отменам клиентов
        user_cancellations = {}
        for booking in bookings:
            if 'cancelled_by_user' in booking and booking['cancelled_by_user']:
                user_id = booking['user_id']
                user_cancellations[user_id] = user_cancellations.get(user_id, 0) + 1
        
        # Топ клиентов по отменам
        top_cancelling_users = sorted(user_cancellations.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Получаем имена пользователей для топа отмен
        users_data = data.load_users()
        top_cancelling_names = []
        for user_id, cancel_count in top_cancelling_users:
            user_info = users_data.get(str(user_id), {})
            parent_name = user_info.get('parent_name', f'Пользователь {user_id}')
            top_cancelling_names.append((parent_name, cancel_count))
        
        # Формируем отчет
        report = "📊 Аналитика по записям\n\n"
        report += f"Всего активных записей: {total_bookings}\n"
        report += f"Подтвержденных: {confirmed_bookings}\n"
        report += f"Не подтвержденных: {unconfirmed_bookings}\n"
        report += f"Отмененных клиентами: {cancelled_bookings}\n\n"
        report += "📅 По периодам:\n"
        report += f"За последнюю неделю: {week_count}\n"
        report += f"За последний месяц: {month_count}\n"
        report += f"За последний год: {year_count}\n\n"
        report += "👶 Топ детей по записям:\n"
        for i, (child, count) in enumerate(top_children, 1):
            report += f"{i}. {child} - {count} записей\n"
        
        if top_cancelling_names:
            report += "\n🚫 Топ клиентов по отменам:\n"
            for i, (name, count) in enumerate(top_cancelling_names, 1):
                report += f"{i}. {name} - {count} отмен\n"
        
        bot.send_message(message.chat.id, report, reply_markup=telebot.types.ReplyKeyboardRemove())
        show_admin_menu(message)
    
    @bot.message_handler(func=lambda message: message.text == "📖 Помощь" and is_admin(message.from_user.id))
    def admin_help_button(message):
        """Помощь через кнопку для админа"""
        admin_help(message)
    
    @bot.message_handler(func=lambda message: message.text == "🔙 Назад" and is_admin(message.from_user.id))
    def admin_back_to_main(message):
        """Админ: возврат в главное меню"""
        show_admin_menu(message)
    
    @bot.message_handler(func=lambda message: message.text == "📱 Меню" and is_admin(message.from_user.id))
    def admin_show_menu(message):
        """Показать главное меню администратора"""
        show_admin_menu(message)
    
    def show_admin_menu(message):
        """Показывает меню администратора"""
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📅 Управление слотами")
        markup.add("👥 Просмотр записей")
        markup.add("📊 Аналитика")
        markup.add("📖 Помощь")
        markup.add("🚪 Выход")
        markup.add("📱 Меню")
        
        bot.send_message(
            message.chat.id, 
            "Панель администратора\n\nДоступные команды:\n/admin - Вход в админку\n/admin_help - Помощь", 
            reply_markup=markup
        )
    
    @bot.message_handler(func=lambda message: message.text == "🚪 Выход" and is_admin(message.from_user.id))
    def admin_exit(message):
        """Админ: выход из админки"""
        bot.send_message(
            message.chat.id, 
            "Вы вышли из админской панели.", 
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )

# Инициализация user_data для бота
def init_bot_data(bot):
    if not hasattr(bot, 'user_data'):
        bot.user_data = {}
