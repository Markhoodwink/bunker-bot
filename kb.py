# kb.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Обычная клавиатура для /start
restart = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Новая игра")],
        [KeyboardButton(text="Правила")]
    ],
    resize_keyboard=True
)

def get_join_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Присоединиться к игре", callback_data="join_game")],
        [InlineKeyboardButton(text="🚀 Начать игру", callback_data="start_game")]
    ])

def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить игру", callback_data="cancel_game")]
    ])

def get_discussion_keyboard():
    """Клавиатура во время обсуждения"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗳️ Начать голосование", callback_data="start_voting")]
    ])


def get_voting_keyboard(player_names):
    """Клавиатура для голосования. player_names = {user_id: name}"""
    buttons = []
    for user_id, name in player_names.items():
        buttons.append([InlineKeyboardButton(
            text=f"❌ Исключить {name}",
            callback_data=f"vote_{user_id}"
        )])
    # Кнопка подведения итогов
    buttons.append([InlineKeyboardButton(
        text="✅ Подвести итоги голосования",
        callback_data="finish_voting"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_next_round_keyboard():
    """Клавиатура после исключения игрока"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗣️ Начать новое обсуждение", callback_data="start_discussion")]
    ])

def get_cancel_round_keyboard():
    """Кнопка отмены текущей игры"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить игру", callback_data="cancel_current_game")]
    ])

def get_play_again_keyboard():
    """Клавиатура после окончания игры"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Играть снова", callback_data="play_again")]
    ])