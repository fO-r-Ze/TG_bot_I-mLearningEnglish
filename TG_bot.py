import telebot
from telebot import types

from psql_config import *
from common_config import load_data_from_file

"""
Модуль реализует Telegram-бота для изучения английского языка путем запоминания слов и проверки знаний пользователя.

Основные функции:
- handle_start(message): Обрабатывает команду '/start'.
- process_name_input(message): Обрабатывает ввод имени пользователя после старта.
- ask_question(cid): Запрашивает у пользователя перевод случайного слова.
- show_menu(cid): Показывает меню с выбором вариантов перевода слова.
- handle_response(message): Обрабатывает ответ пользователя на задание перевода.
- increment_count(cid, target_word): Увеличивает счетчик правильных ответов на перевод слова.
- handle_add_word(message): Обрабатывает событие добавления слова в словарь.
- process_add_word(message): Обрабатывает факт добавления слова.
- handle_del_word(message): Обрабатывает событие удаления слова из словаря.
- process_del_word(message): Обрабатывает факт удаления слова.

Обработчики:
- @bot.message_handler(commands=['start']): Начальная точка входа для пользователя.
- @bot.message_handler(func=lambda message: message.text.strip() != "Добавить слово \"+\"" and message.text.strip() != "Удалить слово \"-\"" and message.text.strip() != "Дальше ⏭"): Основная логика работы с ответами пользователя.
- @bot.message_handler(func=lambda message: message.text.startswith("Добавить")): Обработчик добавления слова.
- @bot.message_handler(func=lambda message: message.text.startswith("Удалить")): Обработчик удаления слова.
- @bot.message_handler(func=lambda message: message.text.startswith("Дальше")): Обработчик перехода к следующему вопросу.
"""

# Работа бота начинается с единоразового выполнения функций:
# - по созданию БД (create_tables(engine))
# - наполнению БД тестовыми данными insert_data(russian_words)

token_TG = load_data_from_file('token_TG.txt')
bot = telebot.TeleBot(token_TG)

current_question = {}

@bot.message_handler(commands=['start'])
def handle_start(message):
    cid = message.chat.id

    # Проверяем, существует ли пользователь
    existing_user = session.query(Users).filter_by(telegram_id=cid).first()

    if not existing_user:
        # Если пользователя нет, просим ввести имя
        msg = bot.send_message(cid, "Привет 👋\n\nДавай попрактикуемся в английском языке\\!\n\n"
                              "Тренировки можешь проходить в удобном для себя темпе\\.\n\n"
                              "У тебя есть возможность использовать тренажёр, как конструктор\\, так и собирать свою собственную базу для обучения\\.\n\n"
                              "\\*Для этого воспользуйся инструментами:\\* \n"
                              "\\- добавить слово ➕\n"
                              "\\- удалить слово ❌\\.\n\n"
                              "Ну что, начнём\\? Как тебя зовут\\? ", parse_mode="MarkdownV2")
        bot.register_next_step_handler(msg, process_name_input)
    else:
        # Если пользователь известен, приветствуем его по имени
        greeting_message = f"Hello, {existing_user.name.title()}, let's continue learning English..."
        bot.send_message(cid, greeting_message)

        # Начинаем обучение с первого вопроса
        ask_question(cid)

def process_name_input(message):
    cid = message.chat.id
    user_name = message.text.strip()

    # Регистрируем пользователя с введённым именем
    add_user(cid, user_name=user_name.title())

    # Приветствуем пользователя по имени
    greeting_message = f"Nice to meet you, {user_name.title()}! Let's start learning English..."
    bot.send_message(cid, greeting_message)

    # Начинаем обучение с первого вопроса
    ask_question(cid)

def ask_question(cid):
    # Получаем случайное целевое слово
    target_word = random_target_word(cid)
    translated_word = translate_target_word(target_word).title()

    # Сохраняем текущее слово в состоянии
    current_question[cid] = {'target_word': target_word, 'translated_word': translated_word}

    # Генерация интерфейса с кнопками
    show_menu(cid)

def show_menu(cid):
    markup = types.ReplyKeyboardMarkup(row_width=2)

    # Берем текущее слово из памяти
    target_word = current_question[cid]['target_word']
    translated_word = current_question[cid]['translated_word']

    # Кнопка правильного перевода
    target_word_btn = types.KeyboardButton(translated_word)

    # Другие возможные переводы
    others = other_words()
    other_words_btns = [types.KeyboardButton(word.title()) for word in others]

    # Объединяем кнопки и перемешиваем их
    buttons = [target_word_btn] + other_words_btns
    random.shuffle(buttons)

    # Стандартные кнопки "/add_word" и "/del_word"
    add_word_btn = types.KeyboardButton('Добавить слово "+" ')
    del_word_btn = types.KeyboardButton('Удалить слово "-" ')
    next_btn = types.KeyboardButton('Дальше ⏭')
    buttons.extend([add_word_btn, del_word_btn, next_btn])

    # Добавляем кнопки построчно
    for i in range(0, len(buttons), 2):
        row_buttons = buttons[i:i+2]
        markup.row(*row_buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {target_word.title()}"
    bot.send_message(cid, greeting, reply_markup=markup)


@bot.message_handler(func=lambda message: message.text.strip() != "Добавить слово \"+\"" and
                                        message.text.strip() != "Удалить слово \"-\"" and
                                        message.text.strip() != "Дальше ⏭")


def handle_response(message):
    cid = message.chat.id

    # Получаем текущее слово и перевод из состояния
    target_word = current_question.get(cid, {}).get('target_word')
    correct_translation = current_question.get(cid, {}).get('translated_word')

    # Проверяем, совпадают ли нажатая кнопка с правильным переводом
    if message.text.strip().lower() == correct_translation.lower():
        # Ответ правильный!
        increment_count(cid, target_word)
        bot.send_message(cid, "🎉 Правильно! Переходим к следующему слову.")
        # Очистка данных после правильного ответа
        del current_question[cid]
        ask_question(cid)  # Переход к следующему вопросу
    elif message.text.strip().lower() != correct_translation:
        # Неправильный ответ
        bot.send_message(cid, "❗ Ошибка! Попробуйте еще раз.")
        # Ничего не делаем, оставляем прежний вопрос
    else:
        bot.send_message(cid, "Ой, похоже что-то пошло не так... Попробуем начать сначала.")
        ask_question(cid)
        return

# Функция для увеличения счетчика правильных ответов на перевод слова
def increment_count(cid, target_word):
    with session.no_autoflush:
        # Получаем пользователя
        user = session.query(Users).filter_by(telegram_id=str(cid)).first()

        # Получаем слово
        word_obj = session.query(Words).filter_by(russian_word=target_word).first()

        # Получаем связь пользователя и слова
        user_word_link = session.query(UserWords).filter_by(user_id=user.id, word_id=word_obj.id).first()

        # Увеличиваем счетчик
        user_word_link.count += 1
        session.commit()

# Обработчик события на кнопку "Добавить слово"
@bot.message_handler(func=lambda message: message.text.startswith("Добавить"))

def handle_add_word(message):
    cid = message.chat.id

    # Запрашиваем у пользователя слово для добавления
    msg = bot.send_message(cid, "Введите русское слово, которое хотите добавить в словарь:")
    bot.register_next_step_handler(msg, process_add_word)

def process_add_word(message):
    cid = message.chat.id
    word = message.text.strip()

    success, translated_word = add_word(cid, word)

    if success:
        # Получили успешный результат и перевод
        num_words = get_user_word_count(cid)
        bot.send_message(cid, f"Слово '{word.title()} / {translated_word.title()}' успешно добавлено. Всего слов в вашем словаре: {num_words}")
    elif translated_word is not None:
        # Случай, когда слово уже есть в словаре
        bot.send_message(cid,f"Слово '{word.title()} / {translated_word.title()}' уже есть в вашем словаре.")
    else:
        # Ошибка перевода или другое условие неудачи
        bot.send_message(cid, f"Перевод слова '{word.title()}' не найден. Добавить такое слово не получится.")

    return ask_question(cid)

# Обработчик события на кнопку "Удалить слово"
@bot.message_handler(func=lambda message: message.text.startswith("Удалить"))
def handle_del_word(message):
    cid = message.chat.id

    # Запрашиваем у пользователя слово для удаления
    msg = bot.send_message(cid, "Введите русское слово, которое хотите удалить из словаря:")
    bot.register_next_step_handler(msg, process_del_word)

def process_del_word(message):
    cid = message.chat.id
    word = message.text.strip()
    existing_word = session.query(Words).filter_by(russian_word=word.lower()).first()
    translated_word = translate(word)
    if not existing_word:
        bot.send_message(cid, f"Cлова '{word.title()}' нет в Вашем словаре")

        return ask_question(cid)

    # Удаляем слово
    success = del_word(cid, word)

    if success:
        # Узнаем количество слов у пользователя
        num_words = get_user_word_count(cid)
        bot.send_message(cid, f"Слово '{word.title()} / {translated_word.title()}' успешно удалено. Всего слов в Вашем словаре: {num_words}")
    else:
        bot.send_message(cid, f"Слова '{word.title()} / {existing_word.english_word.title()}' не было в Вашем словаре.")

    return ask_question(cid)

# Обработчик события на кнопку "Дальше"
@bot.message_handler(func=lambda message: message.text.startswith("Дальше"))
def handle_del_word(message):
    cid = message.chat.id

    # Начинаем обучение с первого вопроса
    ask_question(cid)

if __name__ == '__main__':
    print('Bot is running...')
    bot.polling()