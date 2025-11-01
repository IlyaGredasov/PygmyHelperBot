import asyncio
import logging
import os
import re
from aiogram import Bot
from aiogram import Dispatcher
from aiogram import Router
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.fsm.state import StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton
from aiogram.types import ReplyKeyboardMarkup
from collections import deque
from numpy.random import choice

bot = Bot(token=os.environ['TOKEN_API'])
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


class RandomizerState(StatesGroup):
    list_loading = State()
    list_is_loaded = State()
    picking = State()


class Randomizer:
    randomize_list: list[str] = []
    picking_sample: deque = deque()
    current_value: str = ""
    eventual_sample: list[str] = []
    accept_left: int = 0
    ban_left: int = 0

    @staticmethod
    def reset():
        Randomizer.randomize_list = []
        Randomizer.picking_sample = deque()
        Randomizer.current_value = ""
        Randomizer.eventual_sample = []
        Randomizer.accept_left = 0
        Randomizer.ban_left = 0

    @staticmethod
    def interrupt():
        Randomizer.picking_sample = deque()
        Randomizer.current_value = ""
        Randomizer.eventual_sample = []
        Randomizer.accept_left = 0
        Randomizer.ban_left = 0


@dp.message(Command('start'))
async def start(message: types.Message, state: FSMContext):
    await bot.send_message(
        chat_id=message.from_user.id,
        text="""
        Hello!
        Use /randomizer to load wishlist
        Use /clear to clear char
        Use /start to restart system
        """,
        reply_markup=ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[
                [KeyboardButton(text="/start"), KeyboardButton(text="/clear")],
                [KeyboardButton(text="/randomizer")]
            ]
        ),
    )
    await state.clear()


@dp.message(Command('clear'))
async def clear(message: types.Message):
    for i in range(message.message_id, 0, -1):
        try:
            await bot.delete_message(message.from_user.id, i)
        except TelegramBadRequest:
            continue


@dp.message(Command('randomizer'))
async def randomizer(message: types.Message, state: FSMContext):
    Randomizer.reset()
    await bot.send_message(
        chat_id=message.from_user.id,
        text="""
        Start to load list
        Send message with your list
        Use /show_list to show list
        Use /stop_loading to stop loading
        Use /start to restart system
        """,
        reply_markup=ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[
                [KeyboardButton(text='/show_list'), KeyboardButton(text='/stop_loading')],
                [KeyboardButton(text='/start')]
            ]
        )
    )
    await state.set_state(RandomizerState.list_loading)


@dp.message(StateFilter(RandomizerState.list_loading, RandomizerState.list_is_loaded),
            Command('show_list'))
async def show_list(message: types.Message):
    await bot.send_message(
        chat_id=message.from_user.id,
        text="".join(str(item) + '\n' for item in Randomizer.randomize_list) if len(
            Randomizer.randomize_list) > 0 else "Empty list"
    )


@dp.message(StateFilter(RandomizerState.list_loading), Command('stop_loading'))
async def stop_list_loading(message: types.Message, state: FSMContext):
    await state.set_state(RandomizerState.list_is_loaded)
    await bot.send_message(
        chat_id=message.from_user.id,
        text="""
        Stopped!
        Use /sample %size% for generating sample
        Use /picking %accept_count% %ban_count% for picking choosing
        """,
        reply_markup=ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[
                [KeyboardButton(text='/show_list')],
                [KeyboardButton(text='/randomizer')],
                [KeyboardButton(text='/start')]
            ]
        )
    )


@dp.message(StateFilter(RandomizerState.list_loading))
async def list_loading(message: types.Message):
    for line in message.text.split('\n'):
        Randomizer.randomize_list.append(line.strip())
    await bot.send_message(
        chat_id=message.from_user.id,
        text="""
        Loaded
        Send one more message to extend list
        Use /show_list to show list
        Use /stop_loading to stop loading
        Use /randomizer to clear list
        Use /start to restart system
        """,
        reply_markup=ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[
                [KeyboardButton(text='/show_list'), KeyboardButton(text='/stop_loading')],
                [KeyboardButton(text='/randomizer')],
                [KeyboardButton(text='/start')]
            ]
        )
    )


@dp.message(StateFilter(RandomizerState.list_is_loaded), Command('sample'))
async def sample(message: types.Message):
    command_pattern = re.compile(r"/sample\s(\d+)$")
    result = re.match(command_pattern, message.text)
    if result is None:
        await bot.send_message(
            chat_id=message.from_user.id,
            text="Invalid format for command. Use /sample %size%"
        )
        return
    sample_size = int(result.group(1))
    if sample_size > len(Randomizer.randomize_list) or sample_size < 0:
        await bot.send_message(
            chat_id=message.from_user.id,
            text="Sample size is invalid"
        )
        return
    sample_array = choice(Randomizer.randomize_list, size=int(sample_size), replace=False)
    await bot.send_message(
        chat_id=message.from_user.id,
        text="".join(str(item) + '\n' for item in sample_array)
    )


@dp.message(StateFilter(RandomizerState.list_is_loaded), Command('picking'))
async def picking(message: types.Message, state: FSMContext):
    command_pattern = re.compile(r"/picking\s(\d+)\s(\d+)$")
    result = re.match(command_pattern, message.text)
    if result is None:
        await bot.send_message(
            chat_id=message.from_user.id,
            text="Invalid format for command. Use /picking %accept_count% %ban_count%",
        )
        return
    accept_left = int(result.group(1))
    ban_left = int(result.group(2))
    if accept_left + ban_left > len(Randomizer.randomize_list) or accept_left <= 0 or ban_left <= 0:
        await bot.send_message(
            chat_id=message.from_user.id,
            text="Invalid numbers in command",
        )
        return
    Randomizer.picking_sample = deque()
    Randomizer.current_value = None
    Randomizer.eventual_sample = []
    Randomizer.accept_left = accept_left
    Randomizer.ban_left = ban_left
    for item in choice(Randomizer.randomize_list, size=Randomizer.accept_left + Randomizer.ban_left, replace=False):
        Randomizer.picking_sample.appendleft(item)
    Randomizer.current_value = Randomizer.picking_sample.popleft()
    await bot.send_message(
        chat_id=message.from_user.id,
        text=str(Randomizer.current_value),
        reply_markup=ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[
                [KeyboardButton(text='/accept'), KeyboardButton(text='/ban')],
                [KeyboardButton(text='/interrupt')]
            ]
        )
    )
    await state.set_state(RandomizerState.picking)


@dp.message(StateFilter(RandomizerState.picking), Command('interrupt'))
async def interrupt(message: types.Message, state: FSMContext):
    Randomizer.interrupt()
    await bot.send_message(
        chat_id=message.from_user.id,
        text="""
            Interrupted!
            Use /sample %size% for generating sample
            Use /picking %accept_count% %ban_count% for picking choosing
            """,
        reply_markup=ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[
                [KeyboardButton(text='/show_list')],
                [KeyboardButton(text='/randomizer')],
                [KeyboardButton(text='/start')]
            ]
        )
    )
    await state.set_state(RandomizerState.list_is_loaded)


@dp.message(StateFilter(RandomizerState.picking), Command(commands=['accept', 'ban']))
async def handle_picking(message: types.Message, state: FSMContext):
    if message.text == '/accept':
        Randomizer.eventual_sample.append(Randomizer.current_value)
        Randomizer.accept_left -= 1
    elif message.text == '/ban':
        Randomizer.ban_left -= 1
    if Randomizer.accept_left == 0:
        await bot.send_message(
            chat_id=message.from_user.id,
            text="".join(str(item) + '\n' for item in Randomizer.eventual_sample)
        )
        await state.set_state(RandomizerState.list_is_loaded)
    elif Randomizer.ban_left == 0:
        while len(Randomizer.picking_sample) > 0:
            Randomizer.current_value = Randomizer.picking_sample.popleft()
            Randomizer.eventual_sample.append(Randomizer.current_value)
        await bot.send_message(
            chat_id=message.from_user.id,
            text="".join(str(item) + '\n' for item in Randomizer.eventual_sample)
        )
        await state.set_state(RandomizerState.list_is_loaded)
    else:
        Randomizer.current_value = Randomizer.picking_sample.popleft()
        await bot.send_message(
            chat_id=message.from_user.id,
            text=str(Randomizer.current_value)
        )


async def main():
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
