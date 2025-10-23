import requests
from common_config import load_data_from_file

""" Основные функции:
- translate(word): Осуществляет перевод слова с русского на английский через Yandex.Dictionary API.
"""

# Функция перевода слова с Yandex.Dictionary
url = 'https://dictionary.yandex.net/api/v1/dicservice.json/lookup'
token_YAD = load_data_from_file('token_YAD.txt')

def translate(word):

    params = {
        'key': token_YAD,
        'lang': 'ru-en',
        'text': word
    }

    response = requests.get(url, params = params).json()
    if 'def' in response and len(response['def']) > 0 and 'tr' in response['def'][0]:
        trans_word = response['def'][0]['tr'][0].get('text')
        return trans_word
    else:
        return None