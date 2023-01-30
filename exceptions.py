class TelegrammError(Exception):
    """Ошибка  при отправке сообщения."""

    pass


class GetApiAnswerError(Exception):
    """Ошибка при запросе к API."""

    pass
