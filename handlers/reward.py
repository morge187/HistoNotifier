import random
from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.requests import (
    is_admin, get_all_rewards, create_reward,
    update_reward, get_reward_by_id, delete_reward,
    get_user, get_user_rewards, get_rewards_by_price,
    assign_reward_to_user, reset_rewards, get_enactive_rewards,
    get_reward_statistic
)

reward_router = Router()

class RewardStates(StatesGroup):
    waiting_reward_name = State()
    waiting_reward_description = State()
    waiting_reward_link = State()
    waiting_reward_price = State()
    waiting_reward_image = State()
    waiting_reward_to_edit = State()
    waiting_edit_choices = State()
    waiting_new_name = State()
    waiting_new_description = State()
    waiting_new_link = State()
    waiting_new_price = State()
    waiting_new_image = State()
    waiting_reward_to_delete = State()
    waiting_reward_confirmation = State()
    waiting_gift_link = State()


@reward_router.message(F.text == "Добавить награду")
@reward_router.message(Command('add_reward'))
async def add_reward_command(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для добавления наград!")
        return
    
    await message.answer("🎁 Давайте создадим новую награду!\n\nВведите название награды:")
    await state.set_state(RewardStates.waiting_reward_name)

@reward_router.message(RewardStates.waiting_reward_name)
async def process_reward_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("📝 Теперь введите описание награды:")
    await state.set_state(RewardStates.waiting_reward_description)

@reward_router.message(RewardStates.waiting_reward_description)
async def process_reward_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await message.answer("🔗 Введите подарочную ссылку (например, ссылку на стикерпак или другой подарок):")
    await state.set_state(RewardStates.waiting_reward_link)

@reward_router.message(RewardStates.waiting_reward_link)
async def process_reward_link(message: Message, state: FSMContext):
    link = message.text.strip()
    if not link.startswith(('http://', 'https://')):
        link = 'https://' + link
    
    await state.update_data(gift_link=link)
    await message.answer("💰 Введите стоимость награды в очках (только цифры):")
    await state.set_state(RewardStates.waiting_reward_price)

@reward_router.message(RewardStates.waiting_reward_price)
async def process_reward_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip())
        if price <= 0:
            await message.answer("⚠️ Стоимость должна быть положительным числом. Попробуйте снова:")
            return
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите число. Попробуйте снова:")
        return
    
    await state.update_data(price=price)
    await message.answer("🖼️ Теперь отправьте картинку для награды:")
    await state.set_state(RewardStates.waiting_reward_image)

@reward_router.message(RewardStates.waiting_reward_image, F.photo)
async def process_reward_image(message: Message, state: FSMContext):
    data = await state.get_data()
    
    # Сохраняем file_id картинки
    image_file_id = message.photo[-1].file_id
    
    # Создаем награду
    success = await create_reward(
        name=data['name'],
        description=data['description'],
        gift_link=data['gift_link'],
        price=data['price'],
        image_file_id=image_file_id
    )
    
    if success:
        await message.answer_photo(
            photo=image_file_id,
            caption=f"✅ Награда успешно создана!\n\n"
                   f"🎁 <b>{data['name']}</b>\n"
                   f"📝 {data['description']}\n"
                   f"💰 Стоимость: {data['price']} очков\n"
                   f"🔗 Ссылка: {data['gift_link']}"
        )
    else:
        await message.answer("❌ Не удалось создать награду. Попробуйте снова.")
    
    await state.clear()

@reward_router.message(RewardStates.waiting_reward_image)
async def process_reward_image_invalid(message: Message):
    await message.answer("⚠️ Пожалуйста, отправьте картинку!")

# Поменять награду
@reward_router.message(F.text == "Изменить награду")
@reward_router.message(Command('edit_reward'))
async def edit_reward_command(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для изменения наград!")
        return
    
    rewards = await get_all_rewards()
    
    if not rewards:
        await message.answer("📭 Нет доступных наград для изменения.")
        return
    
    # Формируем список наград
    rewards_list = "📋 Список наград для изменения:\n\n"
    for i, reward in enumerate(rewards, 1):
        rewards_list += f"{i}. 🆔 {reward.id} | {reward.name}\n"
        rewards_list += f"   💰 {reward.price} очков\n"
        rewards_list += f"   {'✅ Активна' if reward.is_active else '❌ Неактивна'}\n\n"
    
    rewards_list += "Введите номер награды для изменения (или 'отмена' для отмены):"
    
    await state.update_data(rewards=rewards)
    await state.set_state(RewardStates.waiting_reward_to_edit)
    await message.answer(rewards_list)

@reward_router.message(RewardStates.waiting_reward_to_edit)
async def process_reward_to_edit(message: Message, state: FSMContext):
    user_input = message.text.strip().lower()
    
    if user_input in ['отмена', 'cancel', 'стоп']:
        await message.answer("❌ Изменение отменено.")
        await state.clear()
        return
    
    try:
        reward_number = int(user_input)
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите номер цифрой или 'отмена' для отмены:")
        return
    
    data = await state.get_data()
    rewards = data.get('rewards', [])
    
    if not (1 <= reward_number <= len(rewards)):
        await message.answer(f"⚠️ Пожалуйста, введите номер от 1 до {len(rewards)}:")
        return
    
    # Получаем выбранную награду
    reward = rewards[reward_number - 1]
    
    # Показываем что можно изменить
    edit_options = (
        "📝 Что вы хотите изменить (введите номера через запятую)\n\n"
        "1. ✏️ Название\n"
        "2. 📄 Описание\n"
        "3. 🔗 Подарочная ссылка\n"
        "4. 💰 Стоимость\n"
        "5. 🖼️ Картинка\n"
        "6. 🔄 Статус активности\n\n"
        "Например: 1,3 или просто 2"
    )
    
    await state.update_data(selected_reward=reward)
    await message.answer_photo(
        photo=reward.image_file_id,
        caption=f"🎁 {reward.name}\n"
               f"📝 {reward.description}\n"
               f"💰 {reward.price} очков\n"
               f"🔗 {reward.gift_link}\n"
               f"📊 {'✅ Активна' if reward.is_active else '❌ Неактивна'}"
    )
    await message.answer(edit_options)
    await state.set_state(RewardStates.waiting_edit_choices)

@reward_router.message(RewardStates.waiting_edit_choices)
async def process_edit_choices(message: Message, state: FSMContext):
    try:
        choices = [int(choice.strip()) for choice in message.text.strip().split(',')]
        
        # Проверяем валидность выбора
        invalid_choices = [c for c in choices if not (1 <= c <= 6)]
        if invalid_choices:
            await message.answer(f"⚠️ Неверные номера: {invalid_choices}. Введите номера от 1 до 6:")
            return
        
        data = await state.get_data()
        reward = data.get('selected_reward')
        
        # Сохраняем выбранные опции
        await state.update_data(edit_choices=choices, reward_id=reward.id)
        
        # Обрабатываем каждую выбранную опцию
        for choice in sorted(set(choices)):  # Убираем дубликаты
            if choice == 1:
                await message.answer("✏️ Введите новое название награды:")
                await state.set_state(RewardStates.waiting_new_name)
                return
            elif choice == 2:
                await message.answer("📄 Введите новое описание награды:")
                await state.set_state(RewardStates.waiting_new_description)
                return
            elif choice == 3:
                await message.answer("🔗 Введите новую подарочную ссылку:")
                await state.set_state(RewardStates.waiting_new_link)
                return
            elif choice == 4:
                await message.answer("💰 Введите новую стоимость награды (только цифры):")
                await state.set_state(RewardStates.waiting_new_price)
                return
            elif choice == 5:
                await message.answer("🖼️ Отправьте новую картинку для награды:")
                await state.set_state(RewardStates.waiting_new_image)
                return
            elif choice == 6:
                # Меняем статус активности
                new_status = not reward.is_active
                success = await update_reward(
                    reward.id,
                    is_active=new_status
                )
                if success:
                    await message.answer(f"🔄 Статус изменен на: {'✅ Активна' if new_status else '❌ Неактивна'}")
                else:
                    await message.answer("❌ Не удалось изменить статус")
                
                # Проверяем, нужно ли еще что-то менять
                await continue_editing(message, state, choices, choice)
                return
        
    except ValueError:
        await message.answer("⚠️ Неверный формат. Введите номера через запятую (например: 1,3 или просто 2):")

async def continue_editing(message: Message, state: FSMContext, choices: list, processed_choice: int):
    data = await state.get_data()
    reward_id = data.get('reward_id')
    
    # Убираем обработанный пункт
    remaining_choices = [c for c in choices if c != processed_choice]
    
    if not remaining_choices:
        # Все изменения завершены
        reward = await get_reward_by_id(reward_id)
        if reward:
            await message.answer_photo(
                photo=reward.image_file_id,
                caption=f"✅ Награда обновлена!\n\n"
                       f"🎁 {reward.name}\n"
                       f"📝 {reward.description}\n"
                       f"💰 {reward.price} очков\n"
                       f"🔗 {reward.gift_link}\n"
                       f"📊 {'✅ Активна' if reward.is_active else '❌ Неактивна'}"
            )
        await state.clear()
        return
    
    # Сохраняем оставшиеся пункты
    await state.update_data(edit_choices=remaining_choices)
    
    # Переходим к следующему пункту
    next_choice = sorted(set(remaining_choices))[0]
    if next_choice == 1:
        await message.answer("✏️ Введите новое название награды:")
        await state.set_state(RewardStates.waiting_new_name)
    elif next_choice == 2:
        await message.answer("📄 Введите новое описание награды:")
        await state.set_state(RewardStates.waiting_new_description)
    elif next_choice == 3:
        await message.answer("🔗 Введите новую подарочную ссылку:")
        await state.set_state(RewardStates.waiting_new_link)
    elif next_choice == 4:
        await message.answer("💰 Введите новую стоимость награды (только цифры):")
        await state.set_state(RewardStates.waiting_new_price)
    elif next_choice == 5:
        await message.answer("🖼️ Отправьте новую картинку для награды:")
        await state.set_state(RewardStates.waiting_new_image)

@reward_router.message(RewardStates.waiting_new_name)
async def process_new_name(message: Message, state: FSMContext):
    data = await state.get_data()
    reward_id = data.get('reward_id')
    
    success = await update_reward(reward_id, name=message.text.strip())
    
    if success:
        await message.answer("✅ Название обновлено!")
        await continue_editing(message, state, data.get('edit_choices', []), 1)
    else:
        await message.answer("❌ Не удалось обновить название")

@reward_router.message(RewardStates.waiting_new_description)
async def process_new_description(message: Message, state: FSMContext):
    data = await state.get_data()
    reward_id = data.get('reward_id')
    
    success = await update_reward(reward_id, description=message.text.strip())
    
    if success:
        await message.answer("✅ Описание обновлено!")
        await continue_editing(message, state, data.get('edit_choices', []), 2)
    else:
        await message.answer("❌ Не удалось обновить описание")

@reward_router.message(RewardStates.waiting_new_link)
async def process_new_link(message: Message, state: FSMContext):
    data = await state.get_data()
    reward_id = data.get('reward_id')
    
    link = message.text.strip()
    if not link.startswith(('http://', 'https://')):
        link = 'https://' + link
    
    success = await update_reward(reward_id, gift_link=link)
    
    if success:
        await message.answer("✅ Ссылка обновлена!")
        await continue_editing(message, state, data.get('edit_choices', []), 3)
    else:
        await message.answer("❌ Не удалось обновить ссылку")

@reward_router.message(RewardStates.waiting_new_price)
async def process_new_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip())
        if price <= 0:
            await message.answer("⚠️ Стоимость должна быть положительным числом. Попробуйте снова:")
            return
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите число. Попробуйте снова:")
        return
    
    data = await state.get_data()
    reward_id = data.get('reward_id')
    
    success = await update_reward(reward_id, price=price)
    
    if success:
        await message.answer("✅ Стоимость обновлена!")
        await continue_editing(message, state, data.get('edit_choices', []), 4)
    else:
        await message.answer("❌ Не удалось обновить стоимость")

@reward_router.message(RewardStates.waiting_new_image, F.photo)
async def process_new_image(message: Message, state: FSMContext):
    data = await state.get_data()
    reward_id = data.get('reward_id')
    
    image_file_id = message.photo[-1].file_id
    success = await update_reward(reward_id, image_file_id=image_file_id)
    
    if success:
        await message.answer("✅ Картинка обновлена!")
        await continue_editing(message, state, data.get('edit_choices', []), 5)
    else:
        await message.answer("❌ Не удалось обновить картинку")

@reward_router.message(RewardStates.waiting_new_image)
async def process_new_image_invalid(message: Message):
    await message.answer("⚠️ Пожалуйста, отправьте картинку!")


@reward_router.message(F.text == "Удалить награду")
@reward_router.message(Command('delete_reward'))
async def delete_reward_command(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для удаления наград!")
        return
    
    rewards = await get_all_rewards()
    
    if not rewards:
        await message.answer("📭 Нет доступных наград для удаления.")
        return
    
    # Формируем список наград
    rewards_list = "📋 Список наград для удаления:\n\n"
    for i, reward in enumerate(rewards, 1):
        rewards_list += f"{i}. 🆔 {reward.id} | {reward.name}\n"
        rewards_list += f"   💰 {reward.price} очков\n\n"
    
    rewards_list += "Введите номер награды для удаления (или 'отмена' для отмены):"
    
    await state.update_data(rewards=rewards)
    await state.set_state(RewardStates.waiting_reward_to_delete)
    await message.answer(rewards_list)

@reward_router.message(RewardStates.waiting_reward_to_delete)
async def process_reward_to_delete(message: Message, state: FSMContext):
    user_input = message.text.strip().lower()
    
    if user_input in ['отмена', 'cancel', 'стоп']:
        await message.answer("❌ Удаление отменено.")
        await state.clear()
        return
    
    try:
        reward_number = int(user_input)
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите номер цифрой или 'отмена' для отмены:")
        return
    
    data = await state.get_data()
    rewards = data.get('rewards', [])
    
    if not (1 <= reward_number <= len(rewards)):
        await message.answer(f"⚠️ Пожалуйста, введите номер от 1 до {len(rewards)}:")
        return
    
    # Получаем выбранную награду
    reward = rewards[reward_number - 1]
    
    # Создаем клавиатуру для подтверждения
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_reward_{reward.id}"),
        InlineKeyboardButton(text="❌ Нет, отменить", callback_data="cancel_delete_reward")
    )
    
    confirmation_message = (
        f"⚠️ ВНИМАНИЕ: Вы уверены, что хотите удалить эту награду?\n\n"
        f"🎁 {reward.name}\n"
        f"💰 Стоимость: {reward.price} очков\n"
        f"🆔 ID: {reward.id}\n\n"
        f"Это действие невозможно отменить!"
    )
    
    await message.answer_photo(
        photo=reward.image_file_id,
        caption=confirmation_message,
        reply_markup=keyboard.as_markup()
    )
    await state.clear()

@reward_router.callback_query(F.data.startswith("confirm_delete_reward_"))
async def confirm_reward_deletion(callback: CallbackQuery):
    reward_id = int(callback.data.split("_")[3])
    
    success = await delete_reward(reward_id)
    
    if success:
        await callback.message.edit_caption(caption="✅ Награда успешно удалена!")
        await callback.answer("Награда удалена!")
    else:
        await callback.message.edit_caption(caption="❌ Ошибка при удалении награды")
        await callback.answer("Произошла ошибка!")

@reward_router.callback_query(F.data == "cancel_delete_reward")
async def cancel_reward_deletion(callback: CallbackQuery):
    await callback.message.edit_caption(caption="❌ Удаление отменено.")
    await callback.answer()

# Награды
@reward_router.message(F.text == "Награды")
@reward_router.message(Command('rewards'))
async def show_rewards_command(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйтесь с помощью /start")
        return
    
    rewards = await get_all_rewards(active_only=True)
    
    if not rewards:
        await message.answer("🏆 На данный момент нет доступных наград.")
        return
    
    # Группируем награды по цене
    rewards_by_price = {}
    for reward in rewards:
        if reward.price not in rewards_by_price:
            rewards_by_price[reward.price] = []
        rewards_by_price[reward.price].append(reward)
    
    response = f"🏆 Список доступных наград\n\n"
    response += f"💎 Ваши очки: {user.points or 0}\n\n"
    
    for price in sorted(rewards_by_price.keys()):
        rewards_list = rewards_by_price[price]
        reward_count = len(rewards_list)
        
        if reward_count > 1:
            response += f"💰 {price} очков - {reward_count} наград\n"
        else:
            response += f"💰 {price} очков - {rewards_list[0].name}\n"
        
        # Показываем первую награду из группы как пример
        if rewards_list:
            for reward in rewards_list:
                example_reward = reward
                can_afford = (user.points or 0) >= price
                
                # Создаем клавиатуру для каждой цены
                keyboard = InlineKeyboardBuilder()
                if can_afford:
                    keyboard.add(InlineKeyboardButton(
                        text=f"🎁 Получить ({price} очков)", 
                        callback_data=f"get_reward_{price}"
                    ))
                else:
                    keyboard.add(InlineKeyboardButton(
                        text=f"❌ Недостаточно очков ({price} очков)", 
                        callback_data="not_enough_points"
                    ))
                
                await message.answer_photo(
                    photo=example_reward.image_file_id,
                    caption=f"🎁 {example_reward.name}\n"
                        f"📝 {example_reward.description}\n"
                        f"💰 {price} очков\n\n"
                        f"{'✅ У вас достаточно очков!' if can_afford else '❌ У вас недостаточно очков'}",
                    reply_markup=keyboard.as_markup()
                )
    
    # Показываем награды пользователя
    user_rewards = await get_user_rewards(user.id)
    if user_rewards:
        rewards_text = f"\n\n🎪 Ваши полученные награды:\n"
        for i, reward in enumerate(user_rewards[:10], 1):  # Показываем первые 10
            rewards_text += f"{i}. {reward.name} ({reward.price} очков)\n"
        
        if len(user_rewards) > 10:
            rewards_text += f"\n... и еще {len(user_rewards) - 10} наград"
        
        await message.answer(rewards_text)

# Получение награды
@reward_router.callback_query(F.data.startswith("get_reward_"))
async def get_reward_handler(callback: CallbackQuery, state: FSMContext):
    try:
        price = int(callback.data.split("_")[2])
        user = await get_user(callback.from_user.id)
        
        if not user:
            await callback.answer("Сначала зарегистрируйтесь!")
            return
        
        # Проверяем, хватает ли очков
        if (user.points or 0) < price:
            await callback.answer("❌ У вас недостаточно очков!")
            return
        
        # Получаем все награды с такой ценой
        available_rewards = await get_rewards_by_price(price)
        
        if not available_rewards:
            await callback.answer("❌ Наград с такой ценой больше нет!")
            return
        
        # Выбираем случайную награду
        selected_reward = random.choice(available_rewards)
        
        if await is_admin(callback.from_user.id):
            # Для админа просим ввести новую ссылку
            await callback.answer("🎁 Вы выбрали награду! Как админ, вы должны ввести новую ссылку для этой награды.")
            await callback.message.answer(
                f"🎁 Администраторская награда\n\n"
                f"Вы выбрали: {selected_reward.name}\n"
                f"Старая ссылка: {selected_reward.gift_link}\n\n"
                f"Пожалуйста, введите новую подарочную ссылку для этой награды:"
            )
            
            # Сохраняем информацию в состоянии
            await state.update_data(
                reward_id=selected_reward.id,
                user_id=user.id,
                price=price
            )
            await state.set_state(RewardStates.waiting_gift_link)
            
        else:
            # Для обычного пользователя сразу назначаем награду
            success = await assign_reward_to_user(user.id, selected_reward.id)
            
            if success:
                # Деактивируем награду (только если не админ)
                await update_reward(selected_reward.id, is_active=False)
                
                await callback.answer(f"🎉 Поздравляем! Вы получили награду: {selected_reward.name}")
                await callback.message.edit_caption(
                    caption=callback.message.caption + f"\n\n🎉 <b>Вы получили эту награду!</b>\n"
                    f"🔗 Ссылка: {selected_reward.gift_link}"
                )
            else:
                await callback.answer("❌ Не удалось получить награду. Возможно, она уже закончилась.")
    
    except Exception as e:
        print(f"Ошибка при получении награды: {e}")
        await callback.answer("❌ Произошла ошибка!")

@reward_router.callback_query(F.data == "not_enough_points")
async def not_enough_points_handler(callback: CallbackQuery):
    await callback.answer("❌ У вас недостаточно очков для получения этой награды!")

@reward_router.message(RewardStates.waiting_gift_link)
async def process_new_gift_link(message: Message, state: FSMContext):
    data = await state.get_data()
    reward_id = data.get('reward_id')
    user_id = data.get('user_id')
    price = data.get('price')
    
    link = message.text.strip()
    if not link.startswith(('http://', 'https://')):
        link = 'https://' + link
    
    # Обновляем ссылку и деактивируем награду
    success = await update_reward(
        reward_id,
        gift_link=link,
        is_active=False
    )
    
    if success:
        # Назначаем награду админу
        await assign_reward_to_user(user_id, reward_id)
        
        reward = await get_reward_by_id(reward_id)
        
        await message.answer(
            f"✅ Награда обновлена и назначена!\n\n"
            f"🎁 {reward.name}\n"
            f"🔗 Новая ссылка: {link}\n"
            f"💰 Потрачено очков: {price}\n\n"
            f"Награда временно деактивирована до следующего пополнения."
        )
    else:
        await message.answer("❌ Не удалось обновить награду.")
    
    await state.clear()

# Мои награды
@reward_router.message(F.text == "Мои награды")
@reward_router.message(Command('my_rewards'))
async def my_rewards_command(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйтесь с помощью /start")
        return
    
    user_rewards = await get_user_rewards(user.id)
    
    if not user_rewards:
        await message.answer("🎁 У вас пока нет полученных наград.\n\n"
                           "Посмотрите доступные награды с помощью команды /rewards")
        return
    
    response = f"🎪 Ваши полученные награды\n"
    response += f"💎 Всего наград: {len(user_rewards)}\n\n"
    
    # Показываем первые 5 наград с картинками
    for i, reward in enumerate(user_rewards[:5], 1):
        await message.answer_photo(
            photo=reward.image_file_id,
            caption=f"🎁 {reward.name}\n"
                   f"📝 {reward.description}\n"
                   f"💰 Стоимость: {reward.price} очков\n"
                   f"🔗 Ссылка: {reward.gift_link}"
        )
        response += f"{i}. {reward.name} ({reward.price} очков)\n"
    
    if len(user_rewards) > 5:
                response += f"\n... и еще {len(user_rewards) - 5} наград"
    
    await message.answer(response)

# Перезагрузить награды
@reward_router.message(Command('reset_rewards'))
async def reset_rewards_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды!")
        return
    
    is_good = await reset_rewards()
    if (is_good):
        await message.answer("✅ Награды успешно перезаписаны")
    else:
        await message.answer(f"❌ Ошибка при сбросе наград")

@reward_router.message(F.text == 'Список наград')
@reward_router.message(Command('all_rewards'))
async def all_rewards_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для просмотра всех наград!")
        return
    
    rewards = await get_all_rewards()
    
    if not rewards:
        await message.answer("📭 В базе данных нет наград.")
        return
    
    active_count = sum(1 for r in rewards if r.is_active)
    inactive_count = len(rewards) - active_count
    
    response = (
        f"📊 Статистика наград\n\n"
        f"🎁 Всего наград: {len(rewards)}\n"
        f"✅ Активных: {active_count}\n"
        f"❌ Неактивных: {inactive_count}\n\n"
        f"📋 Полный список наград:\n\n"
    )
    
    # Группируем по активности
    active_rewards = [r for r in rewards if r.is_active]
    inactive_rewards = [r for r in rewards if not r.is_active]
    
    if active_rewards:
        response += "✅ Активные награды:\n"
        for i, reward in enumerate(active_rewards, 1):
            response += f"{i}. ID {reward.id}: {reward.name} ({reward.price} очков)\n"
        response += "\n"
    
    if inactive_rewards:
        response += "❌ Неактивные награды:\n"
        for i, reward in enumerate(inactive_rewards, 1):
            response += f"{i}. ID {reward.id}: {reward.name} ({reward.price} очков)\n"
        response += "\n"
    
    # Показываем распределение по цене
    price_distribution = {}
    for reward in rewards:
        if reward.price not in price_distribution:
            price_distribution[reward.price] = {'total': 0, 'active': 0}
        price_distribution[reward.price]['total'] += 1
        if reward.is_active:
            price_distribution[reward.price]['active'] += 1
    
    response += "💰 Распределение по цене:\n"
    for price in sorted(price_distribution.keys()):
        total = price_distribution[price]['total']
        active = price_distribution[price]['active']
        response += f"{price} очков: {active}/{total} активных\n"
    
    await message.answer(response)


# Пополнить ссылку
@reward_router.message(Command('refill_reward'))
async def refill_reward_command(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для пополнения наград!")
        return
    
    # Получаем только неактивные награды
    inactive_rewards = get_enactive_rewards()
    
    if not inactive_rewards:
        await message.answer("✅ Все награды активны, пополнение не требуется.")
        return
    
    # Формируем список неактивных наград
    rewards_list = "📋 Список неактивных наград для пополнения:\n\n"
    for i, reward in enumerate(inactive_rewards, 1):
        rewards_list += f"{i}. 🆔 {reward.id} | {reward.name}\n"
        rewards_list += f"   💰 {reward.price} очков\n"
        rewards_list += f"   🔗 Текущая ссылка: {reward.gift_link}...\n\n"
    
    rewards_list += "Введите номер награды для пополнения (или 'отмена' для отмены):"
    
    await state.update_data(inactive_rewards=inactive_rewards)
    await message.answer(rewards_list)
    await state.set_state(RewardStates.waiting_reward_confirmation)

@reward_router.message(RewardStates.waiting_reward_confirmation)
async def process_reward_refill(message: Message, state: FSMContext):
    user_input = message.text.strip().lower()
    
    if user_input in ['отмена', 'cancel', 'стоп']:
        await message.answer("❌ Пополнение отменено.")
        await state.clear()
        return
    
    try:
        reward_number = int(user_input)
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите номер цифрой или 'отмена' для отмены:")
        return
    
    data = await state.get_data()
    rewards = data.get('inactive_rewards', [])
    
    if not (1 <= reward_number <= len(rewards)):
        await message.answer(f"⚠️ Пожалуйста, введите номер от 1 до {len(rewards)}:")
        return
    
    # Получаем выбранную награду
    reward = rewards[reward_number - 1]
    
    await state.update_data(selected_reward_id=reward.id)
    await message.answer(
        f"🎁 {reward.name}\n"
        f"💰 Цена: {reward.price} очков\n"
        f"📝 Описание: {reward.description}\n"
        f"🔗 Текущая ссылка: {reward.gift_link}\n\n"
        f"Пожалуйста, введите новую подарочную ссылку для активации этой награды:"
    )
    await state.set_state(RewardStates.waiting_gift_link)

# Активация ссылки
@reward_router.message(RewardStates.waiting_gift_link)
async def process_refill_gift_link(message: Message, state: FSMContext):
    data = await state.get_data()
    reward_id = data.get('selected_reward_id')
    
    if not reward_id:
        await message.answer("❌ Ошибка: награда не найдена.")
        await state.clear()
        return
    
    link = message.text.strip()
    if not link.startswith(('http://', 'https://')):
        link = 'https://' + link
    
    # Активируем награду с новой ссылкой
    success = await update_reward(
        reward_id,
        gift_link=link,
        is_active=True
    )
    
    if success:
        reward = await get_reward_by_id(reward_id)
        await message.answer(
            f"✅ Награда успешно активирована!\n\n"
            f"🎁 {reward.name}\n"
            f"🔗 Новая ссылка: {link}\n"
            f"💰 Цена: {reward.price} очков\n\n"
            f"Награда теперь доступна для получения пользователями."
        )
    else:
        await message.answer("❌ Не удалось активировать награду.")
    
    await state.clear()

# Reward_stats
@reward_router.message(Command('reward_stats'))
async def reward_stats_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для просмотра статистики!")
        return
    
    total_rewards, active_rewards, user_rewards, unique_users = await get_reward_statistic()
    
    if not total_rewards:
        await message.answer("📭 В базе данных нет наград.")
        return
    
    # Анализируем распределение по цене
    price_stats = {}
    for reward in total_rewards:
        if reward.price not in price_stats:
            price_stats[reward.price] = {'total': 0, 'active': 0, 'claimed': 0}
        price_stats[reward.price]['total'] += 1
        if reward.is_active:
            price_stats[reward.price]['active'] += 1
    
    # Считаем сколько раз награды были получены
    for user_reward in user_rewards:
        reward = await get_reward_by_id(user_reward.reward_id)
        if reward and reward.price in price_stats:
            price_stats[reward.price]['claimed'] += 1
    
    response = (
        f"📊 Статистика системы наград\n\n"
        f"🎁 Общая статистика:\n"
        f"• Всего наград: {len(total_rewards)}\n"
        f"• Активных: {len(active_rewards)}\n"
        f"• Неактивных: {len(total_rewards) - len(active_rewards)}\n"
        f"• Всего выдано: {len(user_rewards)}\n"
        f"• Уникальных получателей: {len(unique_users)}\n\n"
        f"💰 Распределение по цене:\n"
    )
    
    for price in sorted(price_stats.keys()):
        stats = price_stats[price]
        response += (
            f"• {price} очков: {stats['active']}/{stats['total']} активных, "
            f"выдано {stats['claimed']} раз\n"
        )
    
    # Топ наград по получению
    if user_rewards:
        reward_counts = {}
        for user_reward in user_rewards:
            reward = await get_reward_by_id(user_reward.reward_id)
            if reward:
                if reward.id not in reward_counts:
                    reward_counts[reward.id] = {'reward': reward, 'count': 0}
                reward_counts[reward.id]['count'] += 1
        
        if reward_counts:
            top_rewards = sorted(reward_counts.values(), key=lambda x: x['count'], reverse=True)[:5]
            response += f"\n🏆 Топ-5 самых популярных наград:\n"
            for i, item in enumerate(top_rewards, 1):
                response += f"{i}. {item['reward'].name} - {item['count']} получений\n"
    
    await message.answer(response)


# Помощь по наградам
@reward_router.message(Command('reward_help'))
async def reward_help_command(message: Message):
    user = await get_user(message.from_user.id)
    is_admin_user = user and user.status == 'admin'
    
    help_text = "🏆 Система наград\n\n"
    help_text += "Доступные команды:\n\n"
    
    help_text += "👤 Для всех пользователей:\n"
    help_text += "/rewards - Показать доступные награды\n"
    help_text += "/my_rewards - Показать мои полученные награды\n"
    help_text += "Награды - Показать доступные награды (кнопка)\n"
    help_text += "Мои награды - Показать мои награды (кнопка)\n\n"
    
    if is_admin_user:
        help_text += "👑 Для администраторов:\n"
        help_text += "/add_reward - Добавить новую награду\n"
        help_text += "/edit_reward - Изменить существующую награду\n"
        help_text += "/delete_reward - Удалить награду\n"
        help_text += "/all_rewards - Показать все награды (статистика)\n"
        help_text += "/refill_reward - Пополнить ссылку неактивной награды\n"
        help_text += "/reward_stats - Статистика системы наград\n"
        help_text += "/reset_rewards - Сбросить все награды (отладка)\n\n"
    
    help_text += "🎮 Как получить награду:\n"
    help_text += "1. Посещайте ивенты и зарабатывайте очки\n"
    help_text += "2. Выберите награду в разделе /rewards\n"
    help_text += "3. Если очков достаточно, нажмите 'Получить'\n"
    help_text += "4. Получите уникальную ссылку на подарок!\n\n"
    
    help_text += "💡 Особенности системы:\n"
    help_text += "• Каждая награда уникальна\n"
    help_text += "• После получения награда временно деактивируется\n"
    help_text += "• Админы могут пополнять награды новыми ссылками\n"
    help_text += "• Награды с одинаковой ценой выдаются случайным образом\n"
    
    await message.answer(help_text)

# Ошибочки