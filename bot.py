import asyncio
import os
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import config

class SchedulerBot:
    def __init__(self):
        self.cfg = config.load_config()
        self.client = None
        self.scheduler_task = None
        self.running = False
        
    async def start(self):
        """Запуск бота"""
        self.client = TelegramClient(
            'session', 
            self.cfg["api_id"], 
            self.cfg["api_hash"]
        )
        
        await self.client.start(phone=self.cfg["phone"])
        print(f"[{datetime.now()}] Бот запущен на аккаунте: {await self.client.get_me()}")
        
        # Регистрация обработчиков команд
        @self.client.on(events.NewMessage(pattern=r'\.help$'))
        async def help_handler(event):
            await self.send_help(event)
            
        @self.client.on(events.NewMessage(pattern=r'\.config$'))
        async def config_handler(event):
            await self.show_config(event)
            
        @self.client.on(events.NewMessage(pattern=r'\.start$'))
        async def start_handler(event):
            await self.start_scheduler_command(event)
            
        @self.client.on(events.NewMessage(pattern=r'\.stop$'))
        async def stop_handler(event):
            await self.stop_scheduler_command(event)
            
        @self.client.on(events.NewMessage(pattern=r'\.status$'))
        async def status_handler(event):
            await self.show_status(event)
            
        @self.client.on(events.NewMessage(pattern=r'\.add'))
        async def add_content_handler(event):
            await self.add_content_command(event)
            
        @self.client.on(events.NewMessage(pattern=r'\.remove'))
        async def remove_content_handler(event):
            await self.remove_content_command(event)
            
        @self.client.on(events.CallbackQuery())
        async def callback_handler(event):
            await self.handle_callback(event)
        
        # Запуск планировщика если включен
        if self.cfg["schedule"]["enabled"]:
            await self.start_scheduler()
            
        print("Бот готов к работе!")
        await self.client.run_until_disconnected()
    
    async def send_help(self, event):
        """Отправка справки"""
        help_text = """
🤖 **Команды бота-рассыльщика:**

`.help` - показать эту справку
`.config` - открыть настройки (инлайн-кнопки)
`.status` - показать статус расписания
`.start` - запустить рассылку по расписанию
`.stop` - остановить рассылку
`.add` - добавить контент (ответь на фото с текстом)
`.remove [номер]` - удалить контент (пример: .remove 1)

**Как добавить контент:**
1. Отправь фото с подписью
2. Ответь на это сообщение командой `.add`
3. Контент добавится в список

**Мульти-режим:** бот будет отправлять контент по очереди
"""
        await event.reply(help_text, link_preview=False)
    
    async def show_config(self, event):
        """Показ конфига с инлайн-кнопками"""
        cfg = config.load_config()
        
        # Кнопки настройки
        buttons = [
            [
                Button.inline("📅 Интервал", b"interval"),
                Button.inline("🔁 Режим", b"mode")
            ],
            [
                Button.inline("▶️ Вкл/Выкл", b"toggle_schedule"),
                Button.inline("📊 Просмотр", b"view_content")
            ],
            [
                Button.inline("💾 Сохранить", b"save"),
                Button.inline("🔄 Сброс", b"reset")
            ]
        ]
        
        config_text = self.format_config_text(cfg)
        await event.reply(config_text, buttons=buttons, link_preview=False)
    
    def format_config_text(self, cfg):
        """Форматирование текста конфига"""
        sched = cfg["schedule"]
        interval_types = {
            "seconds": "сек",
            "minutes": "мин",
            "hours": "час",
            "days": "дн"
        }
        
        status = "✅ ВКЛ" if sched["enabled"] else "❌ ВЫКЛ"
        mode = "📝 Одиночный" if cfg["content"]["mode"] == "single" else "🎠 Мульти-режим"
        
        text = f"""
📋 **Текущая конфигурация**

**Расписание:** {status}
**Интервал:** {sched['interval_value']} {interval_types.get(sched['interval_type'], sched['interval_type'])}
**Режим:** {mode}
**Контентов:** {len(cfg['content']['items'])}

"""
        if len(cfg['content']['items']) > 0 and cfg["content"]["mode"] == "multi":
            current = cfg.get("current_index", 0)
            text += f"🎯 Следующий: #{current + 1}\n"
            
        return text
    
    async def handle_callback(self, event):
        """Обработка инлайн-кнопок"""
        data = event.data.decode()
        cfg = config.load_config()
        
        if data == "interval":
            # Меню выбора интервала
            buttons = [
                [
                    Button.inline("5 секунд", b"set_interval_seconds_5"),
                    Button.inline("10 секунд", b"set_interval_seconds_10"),
                    Button.inline("30 секунд", b"set_interval_seconds_30")
                ],
                [
                    Button.inline("1 минута", b"set_interval_minutes_1"),
                    Button.inline("5 минут", b"set_interval_minutes_5"),
                    Button.inline("15 минут", b"set_interval_minutes_15")
                ],
                [
                    Button.inline("30 минут", b"set_interval_minutes_30"),
                    Button.inline("1 час", b"set_interval_hours_1"),
                    Button.inline("6 часов", b"set_interval_hours_6")
                ],
                [
                    Button.inline("1 день", b"set_interval_days_1"),
                    Button.inline("7 дней", b"set_interval_days_7")
                ],
                [Button.inline("◀️ Назад", b"back")]
            ]
            await event.edit("⏰ **Выберите интервал:**", buttons=buttons)
            
        elif data.startswith("set_interval_"):
            parts = data.split("_")
            unit = parts[2]  # seconds, minutes, hours, days
            value = int(parts[3])
            cfg["schedule"]["interval_type"] = unit
            cfg["schedule"]["interval_value"] = value
            config.save_config(cfg)
            
            # Перезапуск планировщика
            if self.running:
                await self.stop_scheduler()
                await self.start_scheduler()
            
            await event.answer(f"Интервал изменён на {value} {unit}!")
            await self.show_config(event)
            
        elif data == "mode":
            # Переключение режима
            new_mode = "multi" if cfg["content"]["mode"] == "single" else "single"
            cfg["content"]["mode"] = new_mode
            if new_mode == "single" and len(cfg["content"]["items"]) > 0:
                cfg["current_index"] = 0
            config.save_config(cfg)
            await event.answer(f"Режим изменён на {'Мульти' if new_mode == 'multi' else 'Одиночный'}")
            await self.show_config(event)
            
        elif data == "toggle_schedule":
            cfg["schedule"]["enabled"] = not cfg["schedule"]["enabled"]
            config.save_config(cfg)
            
            if cfg["schedule"]["enabled"]:
                await self.start_scheduler()
                await event.answer("Расписание ВКЛЮЧЕНО!")
            else:
                await self.stop_scheduler()
                await event.answer("Расписание ВЫКЛЮЧЕНО!")
            await self.show_config(event)
            
        elif data == "view_content":
            await self.show_content_list(event)
            
        elif data.startswith("delete_"):
            idx = int(data.split("_")[1])
            if 0 <= idx < len(cfg["content"]["items"]):
                deleted = cfg["content"]["items"].pop(idx)
                if cfg.get("current_index", 0) >= len(cfg["content"]["items"]):
                    cfg["current_index"] = 0
                config.save_config(cfg)
                await event.answer(f"Удалён контент #{idx + 1}")
                await self.show_content_list(event)
            else:
                await event.answer("Неверный номер!")
                
        elif data == "save":
            await event.answer("Конфигурация сохранена!")
            
        elif data == "reset":
            config.save_config(config.DEFAULT_CONFIG)
            self.cfg = config.load_config()
            if self.running:
                await self.stop_scheduler()
                if self.cfg["schedule"]["enabled"]:
                    await self.start_scheduler()
            await event.answer("Конфиг сброшен!")
            await self.show_config(event)
            
        elif data == "back":
            await self.show_config(event)
    
    async def show_content_list(self, event):
        """Показать список контента"""
        cfg = config.load_config()
        items = cfg["content"]["items"]
        
        if not items:
            await event.edit("📭 **Список контента пуст!**\n\nОтправь фото с подписью и ответь `.add`", buttons=[[Button.inline("◀️ Назад", b"back")]])
            return
            
        text = "📸 **Список контента:**\n\n"
        for i, item in enumerate(items):
            photo_status = "✅" if os.path.exists(item.get("photo_path", "")) else "❌"
            text += f"{i+1}. {photo_status} {item['text'][:50]}...\n"
            
        buttons = []
        row = []
        for i in range(len(items)):
            row.append(Button.inline(f"🗑 {i+1}", f"delete_{i}".encode()))
            if len(row) == 5:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([Button.inline("◀️ Назад", b"back")])
        
        await event.edit(text, buttons=buttons)
    
    async def add_content_command(self, event):
        """Добавление контента (ответом на сообщение с фото)"""
        reply = await event.get_reply_message()
        if not reply or not reply.photo:
            await event.reply("❌ Ответь на сообщение с фотографией!\nОтправь фото с подписью и ответь `.add`")
            return
            
        # Создаём папку для фото если нет
        os.makedirs("photos", exist_ok=True)
        
        # Сохраняем фото
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_path = f"photos/content_{timestamp}.jpg"
        await self.client.download_file(reply.photo, photo_path)
        
        # Получаем текст (подпись к фото или пустая строка)
        text = reply.text or ""
        
        cfg = config.load_config()
        cfg["content"]["items"].append({
            "text": text,
            "photo_path": photo_path
        })
        config.save_config(cfg)
        
        await event.reply(f"✅ Контент добавлен!\nТекст: {text[:50]}\nФото сохранено")
    
    async def remove_content_command(self, event):
        """Удаление контента по номеру"""
        parts = event.raw_text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            await event.reply("❌ Использование: `.remove [номер]`\nНомера можно посмотреть в `.config` -> Просмотр")
            return
            
        idx = int(parts[1]) - 1
        cfg = config.load_config()
        
        if 0 <= idx < len(cfg["content"]["items"]):
            removed = cfg["content"]["items"].pop(idx)
            config.save_config(cfg)
            await event.reply(f"✅ Удалён контент #{idx + 1}")
        else:
            await event.reply(f"❌ Контента с номером {idx + 1} не существует")
    
    async def start_scheduler_command(self, event):
        """Команда запуска рассылки"""
        if self.running:
            await event.reply("⏳ Рассылка уже запущена!")
            return
            
        cfg = config.load_config()
        cfg["schedule"]["enabled"] = True
        config.save_config(cfg)
        
        await self.start_scheduler()
        await event.reply(f"✅ Рассылка запущена!\n{config.get_schedule_info()}")
    
    async def stop_scheduler_command(self, event):
        """Команда остановки рассылки"""
        if not self.running:
            await event.reply("⏸ Рассылка уже остановлена!")
            return
            
        await self.stop_scheduler()
        
        cfg = config.load_config()
        cfg["schedule"]["enabled"] = False
        config.save_config(cfg)
        
        await event.reply("⏸ Рассылка остановлена!")
    
    async def show_status(self, event):
        """Показать статус"""
        cfg = config.load_config()
        status = config.get_schedule_info()
        
        if self.running:
            status += "\n🟢 Статус: АКТИВНА"
        else:
            status += "\n🔴 Статус: ОСТАНОВЛЕНА"
            
        await event.reply(status)
    
    async def start_scheduler(self):
        """Запуск планировщика"""
        if self.scheduler_task and not self.scheduler_task.done():
            return
            
        self.running = True
        self.scheduler_task = asyncio.create_task(self.scheduler_loop())
        print(f"[{datetime.now()}] Планировщик запущен")
    
    async def stop_scheduler(self):
        """Остановка планировщика"""
        self.running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        print(f"[{datetime.now()}] Планировщик остановлен")
    
    async def scheduler_loop(self):
        """Основной цикл рассылки"""
        while self.running:
            cfg = config.load_config()
            
            if not cfg["schedule"]["enabled"]:
                self.running = False
                break
                
            # Получаем текущий контент для отправки
            items = cfg["content"]["items"]
            if items:
                if cfg["content"]["mode"] == "single":
                    # Всегда отправляем первый элемент
                    item = items[0]
                else:
                    # Мульти-режим: отправляем по очереди
                    current = cfg.get("current_index", 0)
                    item = items[current % len(items)]
                    
                    # Обновляем индекс
                    cfg["current_index"] = (current + 1) % len(items)
                    config.save_config(cfg)
                
                await self.send_content(item)
                
            # Ждём следующий интервал
            interval_seconds = self.get_interval_seconds(cfg["schedule"])
            await asyncio.sleep(interval_seconds)
    
    def get_interval_seconds(self, schedule):
        """Конвертирует интервал в секунды"""
        value = schedule["interval_value"]
        unit = schedule["interval_type"]
        
        multipliers = {
            "seconds": 1,
            "minutes": 60,
            "hours": 3600,
            "days": 86400
        }
        
        return value * multipliers.get(unit, 60)
    
    async def send_content(self, item):
        """Отправка одного контента (текст + фото)"""
        try:
            me = await self.client.get_me()
            if os.path.exists(item["photo_path"]):
                await self.client.send_file(
                    me.username,  # отправляем самому себе
                    item["photo_path"],
                    caption=item["text"]
                )
                print(f"[{datetime.now()}] Отправлен контент: {item['text'][:50]}")
            else:
                # Если фото нет, отправляем только текст
                await self.client.send_message(me.username, item["text"])
                print(f"[{datetime.now()}] Фото не найдено, отправлен только текст")
        except FloodWaitError as e:
            print(f"[{datetime.now()}] Flood wait {e.seconds} секунд")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"[{datetime.now()}] Ошибка отправки: {e}")

def main():
    bot = SchedulerBot()
    asyncio.run(bot.start())

if __name__ == "__main__":
    main()
