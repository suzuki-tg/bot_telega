import json
import os
from datetime import datetime

CONFIG_FILE = "schedule_config.json"

# Конфиг по умолчанию
DEFAULT_CONFIG = {
    "api_id": 123456,  # твой API ID
    "api_hash": "your_api_hash",  # твой API Hash
    "phone": "+70000000000",  # номер телефона
    "schedule": {
        "enabled": True,
        "interval_type": "minutes",  # minutes, seconds, hours, days
        "interval_value": 5,  # значение интервала
    },
    "content": {
        "mode": "single",  # single или multi
        "items": [
            {
                "text": "Привет! Это тестовое сообщение",
                "photo_path": "photos/photo1.jpg"  # путь к фото
            }
        ]
    },
    "current_index": 0  # для мульти-режима (какой элемент отправлять)
}

def load_config():
    """Загружает конфиг из файла"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Сохраняет конфиг в файл"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_schedule_info():
    """Возвращает читаемое описание расписания"""
    config = load_config()
    sched = config["schedule"]
    if not sched["enabled"]:
        return "⏸ Расписание отключено"
    
    interval = sched["interval_value"]
    unit = sched["interval_type"]
    
    units = {
        "seconds": "секунд",
        "minutes": "минут",
        "hours": "часов",
        "days": "дней"
    }
    
    mode = "📝 Одиночный" if config["content"]["mode"] == "single" else "🎠 Мульти-режим"
    items_count = len(config["content"]["items"])
    
    return f"✅ Расписание: каждые {interval} {units[unit]}\n{mode} | Контентов: {items_count}"
