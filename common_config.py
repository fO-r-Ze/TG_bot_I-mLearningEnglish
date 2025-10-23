"""
Основные функции:
- load_data_from_file(filename): Загружает данные из локального файла.
"""

# Функция для получения данных из локального файла
def load_data_from_file(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read()