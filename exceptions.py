class TelegrammError(Exception):
    """Ошибка  при отправке сообщения."""

    pass


class GetApiAnswerError(ConnectionError):
    """Ошибка при запросе к API."""

    pass
