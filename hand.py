from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters.command import CommandStart, Command
import scenarios, cards
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import kb

user = Router()

# Хранилище игр (временно в памяти, потом перенесём в БД)
# Структура: {chat_id: {"players": [user_id1, user_id2, ...], "started": False}}
games = {}
# Состояния игры
class GameStates(StatesGroup):
    discussion = State()      # Обсуждение
    voting = State()          # Голосование


@user.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        'Добро пожаловать 🧙‍♂️\n\nВыберите тип игры:',
        reply_markup=kb.restart
    )


@user.message(F.text == "Новая игра")
async def new_game(message: Message):
    chat_id = message.chat.id
    
    if message.chat.type not in ["group", "supergroup"]:
        await message.answer("⚠️ Эта команда работает только в группах!")
        return
    
    if chat_id in games and not games[chat_id].get("finished", True):
        await message.answer("️ В этой группе уже идёт игра!")
        return

    games[chat_id] = {
    "players": [],
    "cards": {},
    "scenario": None,
    "started": False,
    "finished": False,
    "round": 1,
    "votes": {},       # {voter_id: voted_for_id}
    "exiled": []       # список исключённых игроков
}
    
    await message.answer(
        "🎮 Новая игра в Бункер создана!\n"
        "Нажмите кнопку ниже, чтобы присоединиться:",
        reply_markup=kb.get_join_keyboard()
    )


@user.callback_query(F.data == "join_game")
async def join_game(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    username = callback.from_user.first_name
    
    # Проверяем, есть ли игра
    if chat_id not in games:
        await callback.answer("Сначала создайте игру кнопкой 'Новая игра'", show_alert=True)
        return
    
    game = games[chat_id]
    
    # Проверяем, не началась ли уже игра
    if game["started"]:
        await callback.answer("Игра уже началась!", show_alert=True)
        return
    
    # Проверяем, не присоединился ли уже
    if user_id in game["players"]:
        await callback.answer("Ты уже в игре!", show_alert=True)
        return
    
    # Добавляем игрока
    game["players"].append(user_id)
    
    await callback.message.answer(
        f"✅ {username} присоединился к игре!\n"
        f"👥 Всего игроков: {len(game['players'])}"
    )
    await callback.answer()


@user.message(CommandStart())  # можно добавить команду /players для проверки
async def show_players(message: Message):
    chat_id = message.chat.id
    if chat_id in games:
        count = len(games[chat_id]["players"])
        await message.answer(f" В игре сейчас {count} игроков")
    else:
        await message.answer("Игра не создана. Нажми '🎮 Новая игра'")

@user.callback_query(F.data == "start_game")
async def start_game(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    
    if chat_id not in games:
        await callback.answer("Игра не создана!", show_alert=True)
        return
    
    game = games[chat_id]
    
    # Проверяем, что нажал создатель (первый игрок)
    if user_id != game["players"][0]:
        await callback.answer("Только создатель может начать игру!", show_alert=True)
        return
    
    # Проверяем, что есть хотя бы 2 игрока
    if len(game["players"]) < 2:
        await callback.answer("Нужно минимум 2 игрока!", show_alert=True)
        return
    
    game["started"] = True
    player_count = len(game["players"])
    
    # ГЕНЕРАЦИЯ СЦЕНАРИЯ ПОД ТЕКУЩЕЕ ЧИСЛО ИГРОКОВ
    # (В scenarios.py теперь вместимость = player_count - 1)
    game["scenario"] = scenarios.generate_scenario(player_count)
    
    # Показываем условия всем в группе
    scenario = game["scenario"]
    catastrophe = scenario["catastrophe"]
    bunker = scenario["bunker"]
    
    conditions_text = (
        f"🌍 <b>КАТАСТРОФА:</b> {catastrophe['name']}\n"
        f"{catastrophe['description']}\n\n"
        f"🏠 <b>БУНКЕР:</b> {bunker['name']}\n"
        f"👥 Вместимость: {bunker['capacity']} человек\n"
        f"📦 Ресурсы: {bunker['resources']}\n"
        f"️ Особенности: {bunker['features']}\n\n"
        f"⚠️ <b>Внимание!</b> В бункер могут попасть только {bunker['capacity']} человек из {len(game['players'])}.\n"
        f"Остальные будут изгнаны и погибнут.\n\n"
        f"🎯 <b>Цель:</b> Убедить остальных, что именно ты достоин выжить!\n\n"
        f"Сейчас начнётся обсуждение. Каждый игрок по очереди раскроет один факт о себе."
    )
    await callback.message.answer(conditions_text, parse_mode="HTML")
    
    # Генерируем уникальные карточки для всех игроков
    all_cards = cards.generate_cards_for_players(len(game["players"]))
    
    for i, player_id in enumerate(game["players"]):
        card = all_cards[i]
        game["cards"][player_id] = card
        
        card_text = (
            f"🎴 <b>ТВОЯ КАРТОЧКА В БУНКЕР</b>\n\n"
            f"👨‍️ <b>Профессия:</b> {card['profession']}\n"
            f"❤️ <b>Здоровье:</b> {card['health']}\n"
            f"⚡ <b>Навык:</b> {card['skill']}\n"
            f"🎨 <b>Хобби:</b> {card['hobby']}\n"
            f"🎒 <b>Инвентарь:</b> {card['inventory']}\n\n"
            f"📝 Подготовь аргументы, почему именно ты достоин выжить!"
        )
        
        try:
            await callback.bot.send_message(player_id, card_text, parse_mode="HTML")
        except:
            await callback.message.answer(
                f"⚠️ Не удалось отправить карточку одному из игроков. "
                f"Попроси его написать боту /start в личку."
            )
    
    # Сообщение с кнопкой начала обсуждения
    await callback.message.answer(
        f"🚀 Игра началась!\n"
        f"👥 Игроков: {len(game['players'])}\n\n"
        f"Всем розданы карточки в личные сообщения!\n"
        f"Используйте /mycard чтобы посмотреть свою карточку.\n\n"
        f"Нажмите кнопку ниже, чтобы начать обсуждение.",
        reply_markup=kb.get_discussion_keyboard(),
        parse_mode="HTML"
    )
    
    # Кнопка отмены игры
    await callback.message.answer(
        "⚠️ Если передумали играть — нажмите кнопку ниже:",
        reply_markup=kb.get_cancel_round_keyboard()
    )
    
    await callback.answer()

@user.callback_query(F.data == "cancel_game")
async def cancel_game(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    
    if chat_id not in games:
        await callback.answer("Игра не найдена!", show_alert=True)
        return
    
    game = games[chat_id]
    
    # Только создатель может отменить
    if user_id != game["players"][0]:
        await callback.answer("Только создатель может отменить игру!", show_alert=True)
        return
    
    # Удаляем игру
    del games[chat_id]
    
    await callback.message.answer("❌ Игра отменена.")
    await callback.answer()

@user.message(Command("mycard"))
async def show_mycard(message: Message):
    """Показать карточку игрока"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if chat_id not in games:
        await message.answer("Игра не найдена!")
        return
    
    game = games[chat_id]
    
    if user_id not in game["cards"]:
        await message.answer("У тебя ещё нет карточки. Дождись начала игры!")
        return
    
    card = game["cards"][user_id]
    
    card_text = (
        f"🎴 <b>ТВОЯ КАРТОЧКА</b>\n\n"
        f"👨‍️ <b>Профессия:</b> {card['profession']}\n"
        f"❤️ <b>Здоровье:</b> {card['health']}\n"
        f"⚡ <b>Навык:</b> {card['skill']}\n"
        f"🎨 <b>Хобби:</b> {card['hobby']}\n"
        f"🎒 <b>Инвентарь:</b> {card['inventory']}"
    )
    
    await message.answer(card_text, parse_mode="HTML")

@user.callback_query(F.data == "start_discussion")
async def start_discussion(callback: CallbackQuery, state: FSMContext):
    """Начать обсуждение"""
    chat_id = callback.message.chat.id
    
    if chat_id not in games:
        await callback.answer("Игра не найдена!", show_alert=True)
        return
    
    game = games[chat_id]
    
    if not game["started"]:
        await callback.answer("Игра ещё не началась!", show_alert=True)
        return
    
    if game.get("finished", False):
        await callback.answer("Игра уже завершена!", show_alert=True)
        return
    
    # Сбрасываем голоса перед новым раундом
    game["votes"] = {}
    
    await state.set_state(GameStates.discussion)
    await state.update_data(chat_id=chat_id, current_player=0)
    
    await callback.message.answer(
        f"🗣️ <b>НАЧИНАЕТСЯ ОБСУЖДЕНИЕ!</b>\n\n"
        f"Раунд {game['round']}\n"
        f"Игроков осталось: {len(game['players'])}\n\n"
        f"Каждый игрок должен раскрыть ОДИН факт о себе "
        f"(профессия, здоровье, навык, хобби или инвентарь).\n"
        f"Используйте аргументы, почему это полезно для выживания.\n\n"
        f"Когда все выскажутся, нажмите кнопку ниже для голосования.",
        reply_markup=kb.get_discussion_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@user.callback_query(F.data == "start_voting")
async def start_voting(callback: CallbackQuery, state: FSMContext):
    """Начать голосование"""
    chat_id = callback.message.chat.id
    
    if chat_id not in games:
        await callback.answer("Игра не найдена!", show_alert=True)
        return
    
    game = games[chat_id]
    
    if not game["started"]:
        await callback.answer("Игра ещё не началась!", show_alert=True)
        return
    
    await state.set_state(GameStates.voting)
    
    # Собираем имена игроков
    player_names = {}
    for player_id in game["players"]:
        try:
            player = await callback.bot.get_chat_member(chat_id, player_id)
            player_names[player_id] = player.user.first_name
        except:
            player_names[player_id] = f"Игрок {player_id}"
    
    keyboard = kb.get_voting_keyboard(player_names)
    
    await callback.message.answer(
        f"️ <b>ГОЛОСОВАНИЕ!</b>\n\n"
        f"Нажмите на кнопку, чтобы проголосовать за исключение игрока.\n"
        f"Можно переголосовать — засчитается последний голос.\n\n"
        f"Когда все проголосуют, нажмите 'Подвести итоги голосования'.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@user.callback_query(F.data.startswith("vote_"))
async def process_vote(callback: CallbackQuery):
    """Обработка голоса"""
    chat_id = callback.message.chat.id
    voter_id = callback.from_user.id
    voted_for_id = int(callback.data.split("_")[1])
    
    if chat_id not in games:
        await callback.answer("Игра не найдена!", show_alert=True)
        return
    
    game = games[chat_id]
    
    # Проверяем, что голосующий ещё в игре
    if voter_id not in game["players"]:
        await callback.answer("Ты уже исключён из игры!", show_alert=True)
        return
    
    # Нельзя голосовать за себя
    if voter_id == voted_for_id:
        await callback.answer("Нельзя голосовать за себя!", show_alert=True)
        return
    
    # Записываем голос
    game["votes"][voter_id] = voted_for_id
    
    # Получаем имя того, за кого проголосовали
    try:
        player = await callback.bot.get_chat_member(chat_id, voted_for_id)
        name = player.user.first_name
    except:
        name = f"Игрок {voted_for_id}"
    
    await callback.answer(f"Ты проголосовал за исключение {name}!", show_alert=True)
    
    # Обновляем сообщение с голосованием — показываем кто за кого проголосовал
    player_names = {}
    for player_id in game["players"]:
        try:
            player = await callback.bot.get_chat_member(chat_id, player_id)
            player_names[player_id] = player.user.first_name
        except:
            player_names[player_id] = f"Игрок {player_id}"
    
    keyboard = kb.get_voting_keyboard(player_names)

    await callback.message.edit_text(
    f"🗳️ <b>ГОЛОСОВАНИЕ!</b>\n\n"
    f"🔒 Голосование тайное.\n"
    f"Проголосовало: {len(game['votes'])} из {len(game['players'])}\n\n"
    f"Нажмите на кнопку, чтобы проголосовать (можно переголосовать).\n"
    f"Когда все проголосуют, нажмите 'Подвести итоги голосования'.",
    reply_markup=keyboard,
    parse_mode="HTML"
)

@user.callback_query(F.data == "finish_voting")
async def finish_voting(callback: CallbackQuery, state: FSMContext):
    """Подвести итоги голосования"""
    chat_id = callback.message.chat.id
    
    if chat_id not in games:
        await callback.answer("Игра не найдена!", show_alert=True)
        return
    
    game = games[chat_id]
    
    if len(game["votes"]) < len(game["players"]):
        await callback.answer(
            f"Ещё не все проголосовали! ({len(game['votes'])}/{len(game['players'])})",
            show_alert=True
        )
        return
    
    # Подсчитываем голоса
    vote_counts = {}
    for voted_for_id in game["votes"].values():
        vote_counts[voted_for_id] = vote_counts.get(voted_for_id, 0) + 1
    
    # Формируем статистику (кто сколько набрал, но БЕЗ имён голосовавших)
    stats_text = " <b>Результаты голосования:</b>\n"
    for pid, count in vote_counts.items():
        try:
            p = await callback.bot.get_chat_member(chat_id, pid)
            name = p.user.first_name
        except:
            name = f"Игрок {pid}"
        stats_text += f"• {name}: {count} голос(ов)\n"
    
    # Находим игрока с максимальным числом голосов
    max_votes = max(vote_counts.values())
    exiled_ids = [pid for pid, count in vote_counts.items() if count == max_votes]
    
    # Если ничья — исключаем первого по списку
    exiled_id = exiled_ids[0]
    
    # Получаем имя исключённого
    try:
        player = await callback.bot.get_chat_member(chat_id, exiled_id)
        exiled_name = player.user.first_name
    except:
        exiled_name = f"Игрок {exiled_id}"
    
    # Удаляем игрока из списка
    game["players"].remove(exiled_id)
    game["exiled"].append(exiled_id)
    
    # Получаем вместимость бункера
    bunker_capacity = game["scenario"]["bunker"]["capacity"]
    
    # Проверяем, закончилась ли игра
    if len(game["players"]) <= bunker_capacity:
        # Игра окончена — все оставшиеся проходят в бункер
        game["finished"] = True
        
        # Собираем имена выживших
        survivors_names = []
        for pid in game["players"]:
            try:
                p = await callback.bot.get_chat_member(chat_id, pid)
                survivors_names.append(p.user.first_name)
            except:
                survivors_names.append(f"Игрок {pid}")
        
        survivors_list = ", ".join(survivors_names)
        
            # 1. Сначала отправляем сообщение, что бот думает
        thinking_msg = await callback.message.answer(
        f"{stats_text}\n\n"
        f"💀 <b>{exiled_name}</b> набрал больше всего голосов ({max_votes}) и был изгнан!\n\n"
        f"🏆 <b>ИГРА ОКОНЧЕНА!</b>\n\n"
        f"В бункер прошли: {survivors_list}\n"
        f"Вместимость бункера: {bunker_capacity} человек\n\n"
        f"🧠 <i>Нейросеть анализирует ваш выбор и пишет вердикт... (это займет 5-10 секунд)</i>",
        parse_mode="HTML"
        )
    
        # 2. Импортируем и вызываем нашу функцию
        import ai_results
        ai_verdict = ai_results.generate_final_verdict(game)
        
        # 3. Отправляем готовый вердикт от нейросети
        await callback.message.answer(
            f"📜 <b>ВЕРДИКТ НЕЙРОСЕТИ:</b>\n\n{ai_verdict}",
            parse_mode="HTML"
        )
        
        # Здесь потом вызовем нейросеть для итогов
        if len(game["players"]) <= bunker_capacity:
            game["finished"] = True
            survivors_names = []
            for pid in game["players"]:
                try:
                    p = await callback.bot.get_chat_member(chat_id, pid)
                    survivors_names.append(p.user.first_name)
                except:
                    survivors_names.append(f"Игрок {pid}")
            
            survivors_list = ", ".join(survivors_names)
            
            # 1. Сначала отправляем сообщение, что бот "думает"
            await callback.message.answer(
                f"{stats_text}\n\n"
                f"💀 <b>{exiled_name}</b> набрал больше всего голосов ({max_votes}) и был изгнан!\n\n"
                f"🏆 <b>ИГРА ОКОНЧЕНА!</b>\n\n"
                f"В бункер прошли: {survivors_list}\n"
                f"Вместимость бункера: {bunker_capacity} человек\n\n"
                f"🧠 <i>Нейросеть анализирует ваш выбор и пишет вердикт... (это займет 10-15 секунд)</i>",
                parse_mode="HTML"
            )
            
            # 2. Вызываем нейросеть
            import ai_results
            ai_verdict = ai_results.generate_final_verdict(game)
            
            # 3. Отправляем красивый вердикт
            await callback.message.answer(
                f"📜 <b>ВЕРДИКТ НЕЙРОСЕТИ:</b>\n\n{ai_verdict}",
                parse_mode="HTML"
            )
        
    else:
        # Игра продолжается — новый раунд
        game["round"] += 1
        
        await callback.message.answer(
            f"{stats_text}\n\n"
            f"💀 <b>{exiled_name}</b> набрал больше всего голосов ({max_votes}) и был изгнан!\n\n"
            f"Игроков осталось: {len(game['players'])}\n"
            f"Мест в бункере: {bunker_capacity}\n\n"
            f"Начинается новый раунд обсуждения!",
            reply_markup=kb.get_next_round_keyboard(),
            parse_mode="HTML"
        )
    
    await callback.answer()

@user.message(F.text == "Правила")
async def show_rules(message: Message):
    rules_text = (
        "📜 <b>ПРАВИЛА ИГРЫ «БУНКЕР»</b>\n\n"
        "🌍 <b>Суть:</b> Произошла катастрофа. Вы — группа людей, которые нашли бункер. "
        "Но мест в бункере меньше, чем игроков. Лишние будут изгнаны и погибнут.\n\n"
        "🎴 <b>Карточки:</b> Каждый игрок получает скрытую карточку с характеристиками:\n"
        "• Профессия\n• Здоровье\n• Навык\n• Хобби\n• Инвентарь\n\n"
        "🗣️ <b>Обсуждение:</b> Игроки по очереди раскрывают ОДИН факт о себе "
        "и аргументируют, почему их навыки полезны для выживания.\n\n"
        "️ <b>Голосование:</b> После обсуждения все голосуют за исключение одного игрока. "
        "Кто набрал больше голосов — покидает игру.\n\n"
        "🔄 <b>Раунды:</b> Обсуждение и голосование повторяются, "
        "пока не останется столько игроков, сколько вмещает бункер.\n\n"
        "🏆 <b>Победа:</b> Выжившие игроки проходят в бункер. "
        "В конце нейросеть проанализирует ваш выбор!"
    )
    await message.answer(rules_text, parse_mode="HTML")

@user.callback_query(F.data == "cancel_current_game")
async def cancel_current_game(callback: CallbackQuery, state: FSMContext):
    """Отмена текущей игры"""
    chat_id = callback.message.chat.id
    
    if chat_id not in games:
        await callback.answer("Игра не найдена!", show_alert=True)
        return
    
    game = games[chat_id]
    
    # Только создатель может отменить
    if callback.from_user.id != game["players"][0]:
        await callback.answer("Только создатель может отменить игру!", show_alert=True)
        return
    
    # Сбрасываем состояние
    await state.clear()
    
    # Удаляем игру
    del games[chat_id]
    
    await callback.message.answer(
        "❌ <b>Игра отменена.</b>\n"
        "Чтобы начать новую, нажмите 'Новая игра'.",
        parse_mode="HTML"
    )
    await callback.answer()