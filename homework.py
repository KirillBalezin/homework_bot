import logging
import os
import sys
import time

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
import requests
import telegram

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename='main.log')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
handler = RotatingFileHandler(
    os.path.expanduser('~/logger.log'), maxBytes=50000000, backupCount=5)
logger.addHandler(handler)


def check_tokens():
    """Проверка доступность переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens:
        if token is None:
            message = (f'Отсутствует переменная окружения: {token}')
            logger.critical(message, exc_info=True)
            raise ValueError(message)


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение отправлено: "{message}"', exc_info=True)
    except telegram.error.TelegramError as error:
        message = (f'Не удалось отправить сообщение: "{error}"')
        logger.error(message, exc_info=True)
        raise exceptions.TelegrammError(message)


def get_api_answer(timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp})
    except Exception as error:
        message = f'Ошибка при запросе к основному API: {error}'
        logger.error(message, exc_info=True)
        raise exceptions.GetApiAnswerError(message)
    if response.status_code != 200:
        message = f'Ошибка при запросе к API: {response.status_code}'
        logger.error(message, exc_info=True)
        raise exceptions.GetApiAnswerError(message)
    try:
        return response.json()
    except Exception as error:
        message = f'Ошибка преобразования json: {error}'
        logger.error(message)
        raise TypeError(message)


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if type(response) != dict:
        message = 'Неожиданный тип данных в ответе API.'
        logger.error(message, exc_info=True)
        raise TypeError(message)
    if 'homeworks' not in response:
        message = 'Ключ "homeworks" отсутствует'
        logger.error(message, exc_info=True)
        raise KeyError(message)
    homeworks = response['homeworks']
    if type(homeworks) != list:
        message = '"homeworks" приходят не в виде списка'
        logger.error(message, exc_info=True)
        raise TypeError(message)
    return homeworks


def parse_status(homework):
    """Извлечение статуса работы."""
    if 'homework_name' not in homework:
        message = 'homework_name недоступно'
        logger.error(message, exc_info=True)
        raise KeyError(message)
    if 'status' not in homework:
        message = 'status недоступно'
        logger.error(message, exc_info=True)
        raise KeyError(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        message = f'Неожиданный статус домашней работы: {homework_status}'
        logger.error(message, exc_info=True)
        raise ValueError(message)
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    valid_status = ''
    valid_error = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if not len(homework):
                logger.info('Статус не обновлен')
            else:
                homework_status = parse_status(homework[0])
                if valid_status == homework_status:
                    logger.info(homework_status)
                else:
                    valid_status = homework_status
                    send_message(bot, homework_status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if valid_error != str(error):
                valid_error = str(error)
                send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
