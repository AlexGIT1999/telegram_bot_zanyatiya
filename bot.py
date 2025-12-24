import telebot
import config
from handlers import client_handlers, admin_handlers
import reminders
import data # Импортируем data

# Получаем токен и список админов из конфига
BOT_TOKEN = config.BOT_TOKEN
ADMIN_IDS = config.ADMIN_IDS

if not BOT_TOKEN:
    raise ValueError("Не найден токен бота. Проверь файл .env")

# Создаем бота
bot = telebot.TeleBot(BOT_TOKEN)

# Настраиваем команды меню
def setup_bot_commands():
    """Настраиваем команды бота"""
    commands = [
        telebot.types.BotCommand("/start", "Главное меню"),
        telebot.types.BotCommand("/help", "Помощь"),
        telebot.types.BotCommand("/admin", "Админ панель"),
        telebot.types.BotCommand("/admin_help", "Помощь администратора"),
    ]
    try:
        bot.set_my_commands(commands)
        print("Команды бота установлены.")
    except Exception as e:
        print(f"Ошибка при установке команд: {e}")

# Регистрируем обработчики
print("Регистрация обработчиков...")
client_handlers.register_client_handlers(bot, ADMIN_IDS)
admin_handlers.register_admin_handlers(bot, ADMIN_IDS)

# Запуск бота
if __name__ == '__main__':
    print("Инициализация базы данных...")
    data.init_db() # Вызываем инициализацию БД

    print("Бот запущен...")
    print(f"Администраторские ID: {ADMIN_IDS}")
    print(f"Production mode: {config.IS_PRODUCTION}")
    
    # Настраиваем команды меню
    setup_bot_commands()
    
    # Запускаем напоминания (только в продакшене или при необходимости в dev)
    if config.IS_PRODUCTION:
        print("Запуск напоминаний (production режим)")
        reminders.setup_reminders(bot)
    else:
        print("Напоминания отключены (dev режим)")

    # Запускаем polling с обработкой исключений
    try:
        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем.")
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
