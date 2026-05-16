#!/bin/bash

echo "==================================="
echo "Telegram Scheduler Bot - Установка"
echo "==================================="

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден!"
    echo "📦 Установи Python:"
    echo "   Termux: pkg install python"
    echo "   Linux: sudo apt install python3 python3-pip"
    exit 1
fi

echo "✅ Python найден"

# Установка зависимостей
echo "📦 Установка зависимостей..."
pip3 install -r requirements.txt

# Создание папки для фото
mkdir -p photos

# Создание файла конфига если нет
if [ ! -f "config.py" ]; then
    echo "⚠️ Файл config.py не найден!"
    echo "📝 Создайте config.py по инструкции в README.md"
fi

echo ""
echo "==================================="
echo "✅ Установка завершена!"
echo "==================================="
echo "🚀 Для запуска: python3 bot.py"
echo "📖 Инструкция: README.md"
