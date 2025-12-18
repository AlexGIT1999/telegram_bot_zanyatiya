import schedule
import time
import threading
import data
import telebot
from datetime import datetime, timedelta

def setup_reminders(bot):
    """Настройка напоминаний"""
    
    # Хранилище для отслеживания отправленных напоминаний (в памяти)
    sent_reminders_cache = set()

    def send_reminders():
        """Отправка напоминаний за день до занятия"""
        try:
            bookings = data.load_bookings()
            now = datetime.now()
            today_date = now.date()
            
            for booking in bookings:
                # Пропускаем уже отмененные записи
                if booking.get('cancelled_by_user', False) or booking.get('cancelled_by_admin', False):
                    continue
                
                # Пропускаем, если напоминание уже отправлено
                reminder_key = f"{booking['user_id']}_{booking['date']}_{booking['time']}"
                if reminder_key in sent_reminders_cache:
                    continue

                # Парсим дату занятия
                try:
                    booking_date = datetime.strptime(booking['date'], "%d.%m.%Y")
                except ValueError:
                    print(f"Некорректный формат даты в записи: {booking}")
                    continue

                # Парсим время начала занятия (берем первую часть до '-')
                time_range = booking['time']
                if '-' in time_range:
                    start_time = time_range.split('-')[0].strip()
                else:
                    start_time = time_range

                try:
                    booking_hour, booking_minute = map(int, start_time.split(':'))
                except (ValueError, IndexError):
                    print(f"Некорректный формат времени в записи: {booking}")
                    continue

                # Создаем полную дату и время занятия
                booking_datetime = booking_date.replace(hour=booking_hour, minute=booking_minute)
                
                # Вычисляем время для напоминания (за день до занятия)
                reminder_datetime = booking_datetime - timedelta(days=1)
                
                # Проверяем, нужно ли отправлять напоминание сегодня
                if reminder_datetime.date() == today_date and now.hour >= 9:
                    # Отправляем напоминание с кнопками подтверждения
                    try:
                        message = f"🔔 Напоминание о занятии!\n\n"
                        message += f"Завтра у вашего ребенка {booking['child_name']} занятие.\n"
                        message += f"Дата: {booking['date']}\n"
                        message += f"Время: {booking['time']}\n\n"
                        message += f"Пожалуйста, подтвердите ваше участие:"

                        # Создаем inline клавиатуру с кнопками подтверждения
                        markup = telebot.types.InlineKeyboardMarkup()
                        confirm_button = telebot.types.InlineKeyboardButton(
                            "✅ Подтвердить", 
                            callback_data=f"confirm_{booking['user_id']}_{booking['date']}_{booking['time']}"
                        )
                        cancel_button = telebot.types.InlineKeyboardButton(
                            "❌ Отменить", 
                            callback_data=f"cancel_reminder_{booking['user_id']}_{booking['date']}_{booking['time']}"
                        )
                        markup.add(confirm_button, cancel_button)

                        bot.send_message(booking['user_id'], message, reply_markup=markup)
                        print(f"Напоминание отправлено пользователю {booking['user_id']} на {booking['date']} {booking['time']}")
                        
                        # Добавляем в кэш, чтобы не отправлять снова
                        sent_reminders_cache.add(reminder_key)
                        
                    except telebot.apihelper.ApiException as e:
                        print(f"Ошибка API при отправке напоминания пользователю {booking['user_id']}: {e}")
                    except Exception as e:
                        print(f"Ошибка отправки напоминания пользователю {booking['user_id']}: {e}")
                        
        except Exception as e:
            print(f"Ошибка при отправке напоминаний: {e}")
    
    # Запланировать выполнение каждый день в 09:00
    schedule.every().day.at("09:00").do(send_reminders)
    
    def run_scheduler():
        """Запуск планировщика в отдельном потоке"""
        while True:
            schedule.run_pending()
            time.sleep(60)  # Проверяем каждую минуту
    
    # Запускаем планировщик в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("Планировщик напоминаний запущен")
    