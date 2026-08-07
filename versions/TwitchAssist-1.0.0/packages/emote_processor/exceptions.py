class EmoteProcessorError(Exception):
    """Базовое исключение для пакета обработки смайликов."""
    pass

class EmoteLoadError(EmoteProcessorError):
    """Ошибка при загрузке файла со смайликами."""
    pass