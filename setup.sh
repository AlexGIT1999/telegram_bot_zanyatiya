#!/bin/bash

# Скрипт для настройки окружения на сервере

echo "Настройка окружения для бота..."

# Проверяем, существует ли venv
if [ ! -d "venv" ]; then
    echo "Создаем виртуальное окружение..."
    python3 -m venv venv
fi

echo "Активируем виртуальное окружение..."
source venv/bin/activate

echo "Устанавливаем зависимости..."
pip install -r requirements.txt

echo "Настройка завершена!"
echo "Для запуска бота используйте: python bot.py"
