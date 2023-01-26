import logging
import os
import time
import sys

import requests

from dotenv import load_dotenv

import telegram

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


def check_tokens():
    """Проверка доступность переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens:
        if token is None:
            raise logger.critical(
                f'Отсутствует обязательная переменная окружения: {token}')


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение отправлено: "{message}"')
    except telegram.error.TelegramError as error:
        raise logger.error(f'Не удалось отправить сообщение: "{error}"')


def get_api_answer(timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp})
    except Exception as error:
        raise logger.error(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != 200:
        raise logger.error(f'Ошибка при запросе к API: {response.status_code}')
    return response.json()


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if type(response) != dict:
        raise logger.error('Неожиданный тип данных в ответе API.')
    if 'homeworks' not in response:
        raise logger.error('Ключ "homeworks" отсутствует')
    homeworks = response['homeworks']
    if type(homeworks) != list:
        raise logger.error('"homeworks" приходят не в виде списка')
    return homeworks


def parse_status(homework):
    """Извлечение статуса работы."""
    if 'homework_name' not in homework:
        raise logger.error('homework_name недоступно')
    if 'status' not in homework:
        raise logger.error('status недоступно')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise logger.error(
            f'Неожиданный статус домашней работы: {homework_status}')
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
