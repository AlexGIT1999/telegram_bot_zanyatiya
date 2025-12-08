import schedule
import time
import threading
import data
import telebot
from datetime import datetime, timedelta

def setup_reminders(bot):
    """Настройка напоминаний"""
    
    def send_reminders():
        """Отправка напоминаний за день до занятия"""
        try:
            bookings = data.load_bookings()
            now = datetime.now()
            
            for booking in bookings:
                # Пропускаем уже отмененные записи
                if booking.get('cancelled_by_user', False):
                    continue
                
                # Парсим дату занятия
                booking_date = datetime.strptime(booking['date'], "%d.%m.%Y")
                booking_time = booking['time'].split('-')[0]  # Берем время начала
                booking_hour = int(booking_time.split(':')[0])
                booking_minute = int(booking_time.split(':')[1])
                
                # Создаем полную дату и время занятия
                booking_datetime = booking_date.replace(hour=booking_hour, minute=booking_minute)
                
                # Вычисляем время для напоминания (за день до занятия)
                reminder_datetime = booking_datetime - timedelta(days=1)
                
                # Проверяем, нужно ли отправлять напоминание
                if reminder_datetime.date() == now.date() and now.hour >= 9:  # Отправляем после 9 утра
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
                        print(f"Напоминание отправлено пользователю {booking['user_id']}")
                    except Exception as e:
                        print(f"Ошибка отправки напоминания пользователю {booking['user_id']}: {e}")
                        
        except Exception as e:
            print(f"Ошибка при отправке напоминаний: {e}")
    
    # Запланировать выполнение каждый день в 9:00
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
