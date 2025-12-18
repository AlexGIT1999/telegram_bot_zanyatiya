import telebot
import data
from datetime import datetime, timedelta

def register_admin_handlers(bot, admin_ids_list):
    """Регистрирует обработчики для администраторов"""
    # Сохраняем список админов в замыкании
    admin_ids = set(admin_ids_list)  # Используем set для лучшей производительности
    
    def is_admin(user_id):
        """Проверяет, является ли пользователь администратором"""
        return str(user_id) in admin_ids
    
    def send_or_edit_message(chat_id, message_id, text, reply_markup=None):
        """Отправляет или редактирует сообщение в зависимости от доступности message_id"""
        try:
            if message_id:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=reply_markup
                )
            else:
                bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
        except Exception:
            # Если не удалось отредактировать, просто отправляем новое сообщение
            bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

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
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("➕ Добавить слоты", callback_data="admin_add_slots"))
        markup.add(telebot.types.InlineKeyboardButton("📋 Просмотр слотов", callback_data="admin_view_slots"))
        markup.add(telebot.types.InlineKeyboardButton("🗑️ Удалить слоты", callback_data="admin_delete_slots"))
        markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        
        send_or_edit_message(
            message.chat.id,
            getattr(message, 'message_id', None),
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

    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_add_slots') or 
                                call.data.startswith('admin_view_slots') or 
                                call.data.startswith('admin_delete_slots') or 
                                call.data.startswith('admin_back'))
    def process_admin_slots_callback(call):
        """Обработка нажатий в меню управления слотами"""
        try:
            if call.data == 'admin_add_slots':
                admin_add_slots_call(call)
            elif call.data == 'admin_view_slots':
                admin_view_slots_call(call)
            elif call.data == 'admin_delete_slots':
                admin_delete_slots_call(call)
            elif call.data == 'admin_back':
                show_admin_menu(call.message)
                
            bot.answer_callback_query(call.id)
        except Exception as e:
            bot.answer_callback_query(call.id, "Ошибка при обработке запроса")
    
    def admin_add_slots_call(call):
        """Добавление слотов через callback"""
        try:
            bot.delete_message(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
        except:
            pass
            
        msg = bot.send_message(
            chat_id=call.message.chat.id,
            text="Введите дату в формате ДД.ММ.ГГГГ (например, 25.12.2025):"
        )
        bot.register_next_step_handler(msg, process_admin_date_input)
    
    def admin_view_slots_call(call):
        """Просмотр слотов через callback"""
        admin_view_slots(call.message)
    
    def admin_delete_slots_call(call):
        """Удаление слотов через callback"""
        try:
            bot.delete_message(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
        except:
            pass
        admin_delete_slots(call.message)

    def process_admin_date_input(message):
        """Обработка ввода даты админом"""
        try:
            # Проверяем формат даты
            datetime.strptime(message.text, "%d.%m.%Y")
            
            # Инициализируем user_data, если ещё не создано
            if not hasattr(bot, 'user_data'):
                bot.user_data = {}
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

    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
    def process_admin_menu_callback(call):
        """Обработка нажатий на кнопки админского меню"""
        try:
            if call.data == 'admin_slots':
                try:
                    bot.delete_message(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id
                    )
                except:
                    pass
                admin_manage_slots_call(call)
            elif call.data == 'admin_bookings':
                admin_view_bookings_call(call)
            elif call.data == 'admin_analytics':
                admin_analytics_call(call)
            elif call.data == 'admin_help':
                admin_help_call(call)
            elif call.data == 'admin_exit':
                admin_exit_call(call)
            elif call.data == 'admin_back':
                show_admin_menu(call.message)
                
            bot.answer_callback_query(call.id)
        except Exception as e:
            bot.answer_callback_query(call.id, "Ошибка при обработке запроса")

    def process_admin_time_input(message):
        """Обработка ввода времени админом"""
        try:
            time_range = message.text.strip()
            if '-' not in time_range:
                raise ValueError("Неверный формат времени")
            start_time, end_time = time_range.split('-', 1)
            start_time = start_time.strip()
            end_time = end_time.strip()

            datetime.strptime(start_time, "%H:%M")
            datetime.strptime(end_time, "%H:%M")
            
            # Разбиваем на часовые слоты
            slots = data.load_slots()
            date = bot.user_data[message.from_user.id]['admin_date']
            
            if date not in slots:
                slots[date] = []
            
            start_hour = int(start_time.split(':')[0])
            end_hour = int(end_time.split(':')[0])
            
            added_slots = []
            for hour in range(start_hour, end_hour):
                slot_time = f"{hour:02d}:00-{hour+1:02d}:00"
                # Проверяем, что слот еще не существует
                slot_exists = any(slot['time'] == slot_time for slot in slots[date])
                
                if not slot_exists:
                    slots[date].append({
                        'time': slot_time,
                        'available': True
                    })
                    added_slots.append(slot_time)
            
            data.save_slots(slots)
            
            if added_slots:
                response = f"✅ Слоты добавлены на {date}:\n" + "\n".join(added_slots)
            else:
                response = f"На {date} уже есть все указанные слоты."
            
            bot.send_message(
                message.chat.id, 
                response,
                reply_markup=telebot.types.ReplyKeyboardRemove()
            )
            
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
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
            
            bot.send_message(message.chat.id, "Нет созданных слотов.", reply_markup=markup)
            return
        
        from datetime import date
        today = date.today()
        
        response = "📅 Доступные слоты:\n\n"
        has_future_slots = False
        
        sorted_dates = []
        for date_str in slots.keys():
            try:
                slot_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                sorted_dates.append((date_str, slot_date))
            except ValueError:
                continue
        
        sorted_dates.sort(key=lambda x: x[1])
        
        for date_str, slot_date in sorted_dates:
            if slot_date >= today:
                has_future_slots = True
                response += f"📅 {date_str}:\n"
                for slot in slots[date_str]:
                    status = "✅ Свободен" if slot.get('available', True) else "❌ Занят"
                    response += f"  {slot['time']} - {status}\n"
                response += "\n"
        
        if not has_future_slots:
            response = "Нет слотов на будущие даты."
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        
        bot.send_message(message.chat.id, response, reply_markup=markup)
    
    @bot.message_handler(func=lambda message: message.text == "🗑️ Удалить слоты" and is_admin(message.from_user.id))
    def admin_delete_slots(message):
        """Админ: удаление слотов"""
        slots = data.load_slots()
        
        if not slots:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
            
            send_or_edit_message(
                message.chat.id,
                getattr(message, 'message_id', None),
                "Нет созданных слотов для удаления.",
                reply_markup=markup
            )
            return
        
        from datetime import date
        today = date.today()
        
        markup = telebot.types.InlineKeyboardMarkup()
        
        sorted_dates = []
        for date_str in slots.keys():
            try:
                slot_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                if slot_date >= today:
                    sorted_dates.append((date_str, slot_date))
            except ValueError:
                continue
        
        sorted_dates.sort(key=lambda x: x[1])
        
        has_future_slots = False
        for date_str, slot_date in sorted_dates:
            date_slots = slots[date_str]
            markup.add(telebot.types.InlineKeyboardButton(f"📅 {date_str}", callback_data=f"date_header_{date_str}"))
            
            for i, slot in enumerate(date_slots):
                # Показываем только слоты, которые ещё не были удалены админом
                if not slot.get('deleted_by_admin', False):
                    # Показываем и занятые тоже
                    slot_text = f"{slot['time']} - {'✅' if slot.get('available', True) else '❌'}"
                    callback_data = f"delete_slot_{date_str}_{i}"
                    markup.add(telebot.types.InlineKeyboardButton(slot_text, callback_data=callback_data))
                    has_future_slots = True
        
        if not has_future_slots:
            send_or_edit_message(
                message.chat.id,
                getattr(message, 'message_id', None),
                "Нет доступных слотов для удаления (все слоты на будущие даты уже удалены)."
            )
            return
        
        markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        
        send_or_edit_message(
            message.chat.id,
            getattr(message, 'message_id', None),
            "Выберите слот для удаления:",
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
    def process_delete_callback(call):
        """Обработка нажатий в меню удаления слотов"""
        try:
            print(f"Delete callback: {call.data}")  # Отладка
            
            if call.data == "delete_back":
                send_or_edit_message(
                    call.message.chat.id,
                    call.message.message_id,
                    "Удаление отменено."
                )
                show_admin_menu(call.message)
                return
            
            if call.data.startswith('delete_slot_'):
                # Разбираем данные слота
                parts = call.data.split('_', 2)
                if len(parts) < 3:
                    bot.answer_callback_query(call.id, "Ошибка: некорректные данные")
                    return

                date_slot_part = parts[2]
                try:
                    date, slot_index_str = date_slot_part.rsplit('_', 1)
                    slot_index = int(slot_index_str)
                except (ValueError, IndexError):
                    bot.answer_callback_query(call.id, "Ошибка: некорректные данные")
                    return
                
                # Загружаем слоты
                slots = data.load_slots()
                print(f"Available slots: {slots}")  # Отладка
                
                if date in slots and 0 <= slot_index < len(slots[date]):
                    deleted_slot = slots[date][slot_index]
                    slot_time = deleted_slot['time']
                    print(f"Deleting slot: {date} {slot_time}")  # Отладка
                    
                    # Отмечаем слот как удаленный админом (независимо от статуса)
                    slots[date][slot_index]['available'] = False
                    slots[date][slot_index]['deleted_by_admin'] = True
                    
                    # Помечаем все записи на этот слот как отмененные админом
                    bookings = data.load_bookings()
                    affected_users = []
                    for booking in bookings:
                        if (booking['date'] == date and 
                            booking['time'] == slot_time and 
                            not booking.get('cancelled_by_user', False) and 
                            not booking.get('cancelled_by_admin', False)):  # Только если не отменено пользователем или админом
                            booking['cancelled_by_admin'] = True
                            affected_users.append(booking['user_id'])
                    
                    data.save_bookings(bookings)
                    data.save_slots(slots)
                    
                    # Отправляем уведомление всем затронутым пользователям
                    for user_id in affected_users:
                        try:
                            bot.send_message(
                                user_id,
                                f"❌ Ваша запись отменена администратором:\n"
                                f"Дата: {date}\n"
                                f"Время: {slot_time}\n\n"
                                f"Приносим свои извинения за доставленные неудобства."
                            )
                        except Exception as e:
                            print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
                    
                    send_or_edit_message(
                        call.message.chat.id,
                        call.message.message_id,
                        f"✅ Слот помечен как удаленный администратором:\nДата: {date}\nВремя: {slot_time}"
                    )
                    
                    import time
                    time.sleep(2)
                    show_admin_menu(call.message)
                else:
                    bot.answer_callback_query(call.id, "Ошибка: слот не найден")
                    print(f"Slot not found: {date} index {slot_index}")  # Отладка
            else:
                bot.answer_callback_query(call.id, "Неизвестная команда")
                print(f"Unknown delete command: {call.data}")  # Отладка
                    
        except Exception as e:
            print(f"Ошибка при удалении слота: {e}")
            import traceback
            traceback.print_exc()
            bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")
        
    @bot.message_handler(func=lambda message: message.text == "👥 Просмотр записей" and is_admin(message.from_user.id))
    def admin_view_bookings(message):
        """Админ: просмотр записей"""
        bookings = data.load_bookings()
        
        if not bookings:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
            
            send_or_edit_message(
                message.chat.id,
                getattr(message, 'message_id', None),
                "Нет записей.",
                reply_markup=markup
            )
            return
        
        response = "👥 Записи на занятия:\n\n"
        for booking in bookings:
            status = ""
            if booking.get('cancelled_by_user', False):
                status = "🚫 Отменена пользователем (слот освобожден)"
            elif booking.get('cancelled_by_admin', False):
                status = "🚫 Отменена администратором"
            else:
                slots = data.load_slots()
                slot_available = False
                slot_exists = False
                slot_deleted_by_admin = False
                
                if booking['date'] in slots:
                    for slot in slots[booking['date']]:
                        if slot['time'] == booking['time']:
                            slot_exists = True
                            slot_available = slot.get('available', True)
                            slot_deleted_by_admin = slot.get('deleted_by_admin', False)
                            break
                
                if not slot_exists or slot_deleted_by_admin:
                    status = "🚫 Слот удален администратором"
                elif not slot_available:
                    status = "✅ Подтверждена"
                else:
                    status = "⏰ Ожидает подтверждения"
            
            response += f"📅 {booking['date']} {booking['time']}\n"
            response += f"👨 Родитель: {booking['parent_name']}\n"
            response += f"👶 Ребенок: {booking['child_name']}\n"
            response += f"📞 Телефон: {booking['phone']}\n"
            response += f"🆔 ID пользователя: {booking['user_id']}\n"
            response += f"📊 Статус: {status}\n"
            response += "➖➖➖➖➖\n"
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        
        send_or_edit_message(
            message.chat.id,
            getattr(message, 'message_id', None),
            response,
            reply_markup=markup
        )

    def admin_manage_slots_call(call):
        """Управление слотами через callback"""
        try:
            bot.delete_message(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
        except:
            pass
        admin_manage_slots(call.message)
    
    def admin_view_bookings_call(call):
        """Просмотр записей через callback"""
        admin_view_bookings(call.message)
    
    def admin_analytics_call(call):
        """Аналитика через callback"""
        admin_analytics(call.message)
    
    def admin_help_call(call):
        """Помощь через callback"""
        admin_help(call.message)
    
    def admin_exit_call(call):
        """Выход через callback"""
        send_or_edit_message(
            call.message.chat.id,
            call.message.message_id,
            "Вы вышли из админской панели."
        )

    @bot.message_handler(func=lambda message: message.text == "📊 Аналитика" and is_admin(message.from_user.id))
    def admin_analytics(message):
        """Админ: аналитика"""
        bookings = data.load_bookings()
        
        if not bookings:
            bot.send_message(message.chat.id, "Нет данных для аналитики.", reply_markup=telebot.types.ReplyKeyboardRemove())
            show_admin_menu(message)
            return
        
        total_bookings = len([b for b in bookings if not b.get('cancelled_by_user', False)])
        cancelled_bookings = len([b for b in bookings if b.get('cancelled_by_user', False)])
        confirmed_bookings = len([b for b in bookings if b.get('confirmed', False) and not b.get('cancelled_by_user', False)])
        unconfirmed_bookings = total_bookings - confirmed_bookings
        
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        year_ago = now - timedelta(days=365)
        
        week_count = 0
        month_count = 0
        year_count = 0
        
        for booking in bookings:
            if booking.get('cancelled_by_user', False):
                continue
            try:
                timestamp_str = booking['timestamp']
                if timestamp_str.endswith('Z'):
                    booking_datetime = datetime.fromisoformat(timestamp_str[:-1])
                else:
                    booking_datetime = datetime.fromisoformat(timestamp_str)
                
                if booking_datetime > week_ago:
                    week_count += 1
                if booking_datetime > month_ago:
                    month_count += 1
                if booking_datetime > year_ago:
                    year_count += 1
            except Exception:
                continue
        
        children_count = {}
        for booking in bookings:
            if booking.get('cancelled_by_user', False):
                continue
            child_name = booking['child_name']
            children_count[child_name] = children_count.get(child_name, 0) + 1
        
        top_children = sorted(children_count.items(), key=lambda x: x[1], reverse=True)[:5]
        
        user_cancellations = {}
        for booking in bookings:
            if 'cancelled_by_user' in booking and booking['cancelled_by_user']:
                user_id = booking['user_id']
                user_cancellations[user_id] = user_cancellations.get(user_id, 0) + 1
        
        top_cancelling_users = sorted(user_cancellations.items(), key=lambda x: x[1], reverse=True)[:5]
        
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
        
        if top_cancelling_users:
            report += "\n🚫 Топ клиентов по отменам:\n"
            for i, (uid, count) in enumerate(top_cancelling_users, 1):
                report += f"{i}. Пользователь {uid} - {count} отмен\n"
        
        bot.send_message(message.chat.id, report, reply_markup=telebot.types.ReplyKeyboardRemove())
        show_admin_menu(message)
    
    @bot.message_handler(func=lambda message: message.text == "📖 Помощь" and is_admin(message.from_user.id))
    def admin_help_button(message):
        admin_help(message)
    
    @bot.message_handler(func=lambda message: message.text == "🔙 Назад" and is_admin(message.from_user.id))
    def admin_back_to_main(message):
        show_admin_menu(message)
    
    @bot.message_handler(func=lambda message: message.text == "📱 Меню" and is_admin(message.from_user.id))
    def admin_show_menu(message):
        show_admin_menu(message)
    
    def show_admin_menu(message):
        """Показывает меню администратора"""
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📅 Управление слотами", callback_data="admin_slots"))
        markup.add(telebot.types.InlineKeyboardButton("👥 Просмотр записей", callback_data="admin_bookings"))
        markup.add(telebot.types.InlineKeyboardButton("📊 Аналитика", callback_data="admin_analytics"))
        markup.add(telebot.types.InlineKeyboardButton("📖 Помощь", callback_data="admin_help"))
        markup.add(telebot.types.InlineKeyboardButton("🚪 Выход", callback_data="admin_exit"))
        
        send_or_edit_message(
            message.chat.id,
            getattr(message, 'message_id', None),
            "Панель администратора\n\nВыберите действие:",
            reply_markup=markup
        )
    
    @bot.message_handler(func=lambda message: message.text == "🚪 Выход" and is_admin(message.from_user.id))
    def admin_exit(message):
        bot.send_message(
            message.chat.id, 
            "Вы вышли из админской панели.", 
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )

# Инициализация user_data для бота
def init_bot_data(bot):
    if not hasattr(bot, 'user_data'):
        bot.user_data = {}