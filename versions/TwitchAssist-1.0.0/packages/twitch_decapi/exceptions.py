class TwitchDecapiError(Exception):
    """Базовое исключение для всех ошибок пакета."""
    pass

class ChannelNotFoundError(TwitchDecapiError):
    """Канал не найден или недоступен."""
    pass

class DecapiRequestError(TwitchDecapiError):
    """Ошибка при выполнении запроса к decapi."""
    pass