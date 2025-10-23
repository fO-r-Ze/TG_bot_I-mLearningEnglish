import random
import json

import sqlalchemy as sq
from sqlalchemy import text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from common_config import load_data_from_file
from YAD_config import translate
from log_config import logger

"""
Основные функции:
- create_tables(engine): Создает необходимые таблицы в базе данных.
- insert_data(data): Заполняет базу данных русским словарем с переводами.
- add_user(cid, user_name=None): Регистрирует нового пользователя и создает начальный набор слов.
- random_target_word(cid): Возвращает случайное слово из словаря пользователя.
- translate_target_word(target_word): Возвращает перевод заданного слова из базы данных.
- other_words(): Возвращает три случайных слова для составления альтернативных вариантов перевода.
- add_word(cid, word): Добавляет слово в персональный словарь пользователя.
- del_word(cid, word): Удаляет слово из персонального словаря пользователя.
- get_user_word_count(cid): Возвращает количество слов в словаре пользователя.
"""

Base = declarative_base()

password = load_data_from_file("DSN_password.txt")
base_name = 'ImLearningEnglish'
encoding ='utf-8'

DSN = "postgresql://postgres:" + password + "@localhost:5432/" + base_name + "?client_encoding=" + encoding
engine = sq.create_engine(DSN)

Session = sessionmaker(bind=engine)
session = Session()

class Words(Base):
    __tablename__ = "words"

    id = sq.Column(sq.Integer, primary_key=True)
    russian_word = sq.Column(sq.String(length=40), unique=True)
    english_word = sq.Column(sq.String(length=40))

class Users(Base):
    __tablename__ = "users"

    id = sq.Column(sq.Integer, primary_key=True)
    telegram_id = sq.Column(sq.BIGINT, unique=True)
    name = sq.Column(sq.String(length=40))

class UserWords(Base):
    __tablename__ = "user_words"
    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey('users.id'))
    word_id = sq.Column(sq.Integer, sq.ForeignKey('words.id'))
    count = sq.Column(sq.Integer, default=0, nullable=False)

    user = relationship("Users")
    word = relationship("Words")

 # База русских слов
russian_words = [
    "абрикос", "аппарат", "астра", "аквариум", "барсук", "банан", "баран", "борщ", "варенье", "виноград", "весна",
    "витамин", "гриб", "горох", "гантель", "газета", "дуб", "деньги", "доктор", "дождь", "елочка", "ёжик", "единица",
    "еда", "жаба", "желудок", "железо", "жизнь", "завод", "золото", "забор", "змея", "игла", "игра", "игрушка", "изба",
    "костёр", "карандаш", "каша", "комната", "ласточка", "лавка", "леденец", "лось", "матрас", "масло", "маска", "море",
    "носок", "ночь", "нога", "ноутбук", "облако", "очки", "одеяло", "ответ", "перо", "пирог", "палатка", "портфель",
    "радуга", "работа", "рама", "реклама", "санки", "сыр", "снег", "соль", "табурет", "туча", "термос", "тапочки",
    "уголь", "улитка", "утка", "улыбка", "фонтан", "фильм", "футбол", "ферма", "хатка", "хвост", "хлеб", "хвоя",
    "центавр", "церковь", "цыплёнок", "цилиндр", "чайник", "чемодан", "частица", "человек", "шина", "шоколад", "шалаш",
    "шампунь", "щетка", "щука", "щипцы", "щепка", "экран", "электричка", "экономика", "эксперт", "юрта", "ягода", "яд",
    "язычок", "ячмень", "яма", "яблоко", "ящик"
]

# Создаем таблицы в БД
def create_tables(engine):
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        session.rollback()
        print(f'Ошибка {e}')

# Очищаем все таблицы и сбрасываем счётчики последовательностей.
def truncate_all_tables(session, Base):
    metadata = Base.metadata
    tables = reversed(metadata.sorted_tables) # Сортируем таблицы в обратном порядке для соблюдения ограничений FK

    try:
        for table in tables:
            table_name = table.name

            # Удаляем все записи из таблицы
            delete_stmt = table.delete()
            session.execute(delete_stmt)

            # Пропускаем сброс последовательности для ассоциативных таблиц
            if "_association" not in table_name:
                # Сбрасываем счётчик последовательности для остальных таблицы
                seq_name = f"{table_name}_id_seq"
                reset_seq_query = f"ALTER SEQUENCE {seq_name} RESTART WITH 1;"
                session.execute(text(reset_seq_query))

        # Фиксируем изменения
        session.commit()
    except Exception as e:
        session.rollback()
        print(f'Ошибка {e}')

# Наполняем БД русскими словами с переводом (запрос на Yandex.Dictionary)
def insert_data(data):
    truncate_all_tables(session, Base)

    with session.no_autoflush:
        try:
            for word in data:
                existing_word = session.query(Words).filter_by(russian_word=word.lower()).first()

                if not existing_word:
                    translated_word = translate(word)

                    if translated_word is not None:
                        new_word = Words(russian_word=word.lower(), english_word=translated_word.lower())
                        session.add(new_word)
                        print(f'Слово "{word.title()} / {translated_word.title()}" успешно добавлено в базу данных')
                    else:
                        print(f'Перевод для слова "{word.title()}" не найден, пропускаем...')

            session.commit()

            print(f'Всего в базе: {session.query(Words).count()} русских слов')

        except Exception as e:
            session.rollback()
            print(f'Ошибка {e}')

# Создаем user и наполняем персональную базу стандартным набором слов
def add_user(cid, user_name = None):
    with session.no_autoflush:
        try:
            # Проверяем, существует ли уже пользователь с таким именем
            existing_user = session.query(Users).filter_by(telegram_id=cid.lower()).first()

            if existing_user:
                return

            # Создаем нового пользователя
            new_user = Users(telegram_id=cid.lower(), name=user_name.title())
            session.add(new_user)
            session.flush()

            add_words = session.query(Words).order_by(Words.id).limit(111).all()
            for word in add_words:
                user_words = UserWords(user_id=new_user.id, word_id=word.id)
                session.add(user_words)

            session.commit()

            # Подготавливаем данные для логирования
            details = {
                'RESULT': 'created',
                'USER': cid,
                'WORDS_ADDED': len(add_words),
            }

            # Формируем финальную лог-запись
            log_entry = {
                'ACTION': 'create_user',
                'DETAILS': details,
            }

            # Конвертируем словарь в строку и записываем в лог с поддержкой UTF-8
            logger.info(json.dumps(log_entry, ensure_ascii=False))

            # print(f"Пользователь '{cid.lower()}' успешно добавлен в систему!")
            return new_user
        except Exception as e:
            session.rollback()
            print(f'Ошибка {e}')

# Получаем из персонального словаря пользователя случайное русское слово
def random_target_word(cid):
    with session.no_autoflush:
        try:
            # Получаем пользователя по telegram_id
            user = session.query(Users).filter_by(telegram_id=cid).first()
            if not user:
                print(f"Пользователь с tg_id={cid} не найден.")
                return None

            # Получаем все слова, принадлежащие данному пользователю
            user_words_query = session.query(Words.russian_word) \
                .join(UserWords, Words.id == UserWords.word_id) \
                .filter(UserWords.user_id == user.id) \
                .all()

            # Преобразуем результат в список слов
            user_words = [word.russian_word for word in user_words_query]

            # Выбираем случайное слово из списка
            if user_words:
                random_word = random.choice(user_words)
                return random_word
            else:
                print("Нет слов в словаре пользователя.")
                return None
        except Exception as e:
            session.rollback()
            print(f'Ошибка {e}')

# Получаем из БД перевод русского слова
def translate_target_word(target_word):
    with session.no_autoflush:
        try:
            # Попробуем найти перевод слова
            translation = session.query(Words).filter_by(russian_word=target_word).first()

            if translation is None:
                # Нет подходящего слова в базе данных
                print(f"Не удалось найти перевод для слова '{target_word.title()}'")
                return None

            return translation.english_word
        except Exception as e:
            session.rollback()
            print(f'Ошибка {e}')

# Формируем список из 3 случайных слов
def other_words():
    with session.no_autoflush:
        try:
            all_words = session.query(Words.english_word).all()
            all_words = [word.english_word for word in all_words]
            other_random_words = random.sample(all_words, 3)

            return other_random_words
        except Exception as e:
            session.rollback()
            print(f'Ошибка {e}')

# Функция добавления слова в персональный словарь пользователя
def add_word(cid, word):
    with session.no_autoflush:
        try:
            # Получаем пользователя по telegram_id
            user = session.query(Users).filter_by(telegram_id=cid).first()
            if not user:
                # print(f"Пользователь с tg_id={cid} не найден.")
                return False, None

            # Проверяем, есть ли это слово уже в таблице Words (русская версия)
            existing_word = session.query(Words).filter_by(russian_word=word.lower()).first()
            translated_word = translate(word)

            if existing_word:
                # Проверяем, связано ли уже существующее слово с данным пользователем
                existing_user_word = session.query(UserWords).filter_by(user_id=user.id, word_id=existing_word.id).first()
                if existing_user_word:

                    # Подготавливаем данные для логирования
                    details = {
                        'RESULT': 'already_exists',
                        'USER': cid,
                        'WORD': word.title(),
                    }

                    # Формируем финальную лог-запись
                    log_entry = {
                        'ACTION': 'add_word',
                        'DETAILS': details,
                    }

                    # Конвертируем словарь в строку и записываем в лог с поддержкой UTF-8
                    logger.info(json.dumps(log_entry, ensure_ascii=False))

                    # print(f"Слово '{word.title()}' уже присутствует в словаре пользователя: {cid}.")
                    return False, translated_word

                # Если слово есть в общем словаре, но не у текущего пользователя, добавляем связь
                user_word = UserWords(user_id=user.id, word_id=existing_word.id)
                session.add(user_word)
                session.commit()

                # Подготавливаем данные для логирования
                details = {
                    'RESULT': 'added_existing',
                    'USER': cid,
                    'WORD': word.title(),
                }

                # Формируем финальную лог-запись
                log_entry = {
                    'ACTION': 'add_word',
                    'DETAILS': details,
                }

                # Конвертируем словарь в строку и записываем в лог с поддержкой UTF-8
                logger.info(json.dumps(log_entry, ensure_ascii=False))

                # print(f"Слово '{word.title()} / {existing_word.english_word.title()}' успешно добавлено в словарь пользователя: {cid}.")
                return True, translated_word

            # Если слово не найдено, добавляем его в Words и подключаем к пользователю
            if not translated_word:

                # Подготавливаем данные для логирования
                details = {
                    'RESULT': 'translation_failed',
                    'USER': cid,
                    'WORD': word.title(),
                }

                # Формируем финальную лог-запись
                log_entry = {
                    'ACTION': 'add_word',
                    'DETAILS': details,
                }

                # Конвертируем словарь в строку и записываем в лог с поддержкой UTF-8
                logger.warning(json.dumps(log_entry, ensure_ascii=False))


                # print(f"Не удалось перевести слово '{word.title()}'. Попробуйте позже.")
                return False, None

            # Добавляем слово в общий словарь
            new_word = Words(russian_word=word.lower(), english_word=translated_word.lower())
            session.add(new_word)
            session.flush()  # Фиксируем временный ID для дальнейшего использования

            # Создаем связь пользователя с этим словом
            user_word = UserWords(user_id=user.id, word_id=new_word.id)
            session.add(user_word)
            session.commit()

            # Подготавливаем данные для логирования
            details = {
                'RESULT': 'added',
                'USER': cid,
                'WORD': word.title(),
            }

            # Формируем финальную лог-запись
            log_entry = {
                'ACTION': 'add_word',
                'DETAILS': details,
            }

            # Конвертируем словарь в строку и записываем в лог с поддержкой UTF-8
            logger.info(json.dumps(log_entry, ensure_ascii=False))

            # print(f"Слово '{word.title()} /  {translated_word.title()}' успешно добавлено в словарь пользователя: {cid}.")
            return True, translated_word

        except Exception as e:
            session.rollback()
            print(f'Ошибка {e}')

# Функция удаления слова из персонального словаря пользователя
def del_word(cid, word):
    with session.no_autoflush:
        try:
            # Получаем пользователя по telegram_id
            user = session.query(Users).filter_by(telegram_id=cid).first()

            if not user:
                # print(f"Пользователь с tg_id='{cid}' не найден.")
                return False

            # Поиск слова в базе данных по русской форме
            word_to_delete = session.query(Words).filter_by(russian_word=word.lower()).first()

            if not word_to_delete:

                # Подготавливаем данные для логирования
                details = {
                    'RESULT': 'word_not_found',
                    'USER': cid,
                    'WORD': word.title(),
                }

                # Формируем финальную лог-запись
                log_entry = {
                    'ACTION': 'delete_word',
                    'DETAILS': details,
                }

                # Конвертируем словарь в строку и записываем в лог с поддержкой UTF-8
                logger.info(json.dumps(log_entry, ensure_ascii=False))

                # print(f"Слово '{word.title()}' не найдено в базе данных.")
                return False

            # Проверяем, связана ли данная запись с указанным пользователем
            association = session.query(UserWords).filter_by(user_id=user.id, word_id=word_to_delete.id).first()

            if not association:

                # Подготавливаем данные для логирования
                details = {
                    'RESULT': 'not_in_user_dict',
                    'USER': cid,
                    'WORD': word.title(),
                }

                # Формируем финальную лог-запись
                log_entry = {
                    'ACTION': 'delete_word',
                    'DETAILS': details,
                }

                # Конвертируем словарь в строку и записываем в лог с поддержкой UTF-8
                logger.info(json.dumps(log_entry, ensure_ascii=False))

                # print(f"Слово '{word.title()} / {word_to_delete.english_word.title()}' не найдено в словаре пользователя: {cid}.")
                return False

            # Удаляем связь пользователя со словом
            session.delete(association)
            session.commit()

            # Подготавливаем данные для логирования
            details = {
                'RESULT': 'deleted',
                'USER': cid,
                'WORD': word.title(),
            }

            # Формируем финальную лог-запись
            log_entry = {
                'ACTION': 'delete_word',
                'DETAILS': details,
            }

            # Конвертируем словарь в строку и записываем в лог с поддержкой UTF-8
            logger.info(json.dumps(log_entry, ensure_ascii=False))

            # print(f"Слово '{word.title()} / {word_to_delete.english_word.title()}' успешно удалено из словаря пользователя: {cid}.")

            return True

        except Exception as e:
            session.rollback()
            print(f'Ошибка {e}')

# Функция для получения количества слов пользователя
def get_user_word_count(cid):
    with session.no_autoflush:
        try:
            user = session.query(Users).filter_by(telegram_id=cid).first()
            if not user:
                return 0

            # Количество слов пользователя
            return session.query(UserWords).filter_by(user_id=user.id).count()
        except Exception as e:
            session.rollback()
            print(f'Ошибка {e}')