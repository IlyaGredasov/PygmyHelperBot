import asyncio
import os
import logging

from aiogram import Bot, Dispatcher, types, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from numpy.random import choice
from collections import deque

bot = Bot(token=os.environ['TOKEN_API'])
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


class Randomizer(StatesGroup):
    list_loading = State()
    list_is_loaded = State()
    picking = State()
    randomize_list = []
    picking_sample = deque()
    current_value = None
    eventual_sample = []
    accept_left = 0
    ban_left = 0


@dp.message(Command('start'))
async def start(message: types.Message, state: FSMContext):
    await bot.send_message(
        chat_id=message.from_user.id,
        text="start"
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
    Randomizer.randomize_list = []
    await bot.send_message(
        chat_id=message.from_user.id,
        text="Загрузи лист"
    )
    await state.set_state(Randomizer.list_loading)


@dp.message(StateFilter(Randomizer.list_loading), Command('stop_loading'))
async def stop_list_loading(message: types.Message, state: FSMContext):
    await state.set_state(Randomizer.list_is_loaded)
    await bot.send_message(
        chat_id=message.from_user.id,
        text="stopped!"
    )


@dp.message(StateFilter(Randomizer.list_loading))
async def list_loading(message: types.Message):
    for line in message.text.split('\n'):
        Randomizer.randomize_list.append(line.strip())


@dp.message(StateFilter(Randomizer.list_is_loaded), Command('sample'))
async def sample(message: types.Message):
    sample_size = message.text.split(' ')[1]
    if sample_size.isdigit():
        sample_array = choice(Randomizer.randomize_list, size=int(sample_size), replace=False)
        await bot.send_message(
            chat_id=message.from_user.id,
            text="".join(str(item) + '\n' for item in sample_array)
        )


@dp.message(StateFilter(Randomizer.list_is_loaded), Command('picking'))
async def picking(message: types.Message, state: FSMContext):
    Randomizer.picking_sample = deque()
    Randomizer.current_value = None
    Randomizer.eventual_sample = []
    Randomizer.accept_left = int(message.text.split(' ')[1])
    Randomizer.ban_left = int(message.text.split(' ')[2])
    for item in choice(Randomizer.randomize_list, size=Randomizer.accept_left + Randomizer.ban_left, replace=False):
        Randomizer.picking_sample.appendleft(item)
    Randomizer.current_value = Randomizer.picking_sample.popleft()
    await bot.send_message(
        chat_id=message.from_user.id,
        text=str(Randomizer.current_value)
    )
    await state.set_state(Randomizer.picking)


@dp.message(StateFilter(Randomizer.picking), Command(commands=['accept', 'ban']))
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
        await state.set_state(Randomizer.list_is_loaded)
    elif Randomizer.ban_left == 0:
        while len(Randomizer.picking_sample) > 0:
            Randomizer.current_value = Randomizer.picking_sample.popleft()
            Randomizer.eventual_sample.append(Randomizer.current_value)
        await bot.send_message(
            chat_id=message.from_user.id,
            text="".join(str(item) + '\n' for item in Randomizer.eventual_sample)
        )
        await state.set_state(Randomizer.list_is_loaded)
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
