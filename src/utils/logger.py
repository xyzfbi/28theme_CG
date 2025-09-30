"""
Утилиты для логирования: предоставляют стандартизированную функцию для настройки
системы логирования в приложении.
"""

import logging
import sys

def setup_logger(
    name: str = "video_meeting_composer",
    level: int = logging.INFO
) -> logging.Logger:
    """
    Настраивает и возвращает объект логгера (logging.Logger) с заданным именем и уровнем.
    Логгер настроен на вывод сообщений в консоль (stdout).

    :param name: Имя логгера. По умолчанию "video_meeting_composer".
    :param level: Минимальный уровень логирования, который будет обрабатываться (например, logging.DEBUG, logging.INFO).
    :return: Настроенный объект logging.Logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Очищаем существующие обработчики. Это важно, чтобы избежать дублирования
    # сообщений, если функция вызывается повторно в ходе работы приложения (например, в Streamlit).
    logger.handlers.clear()

    # Формат сообщений: включает время, имя логгера, уровень и само сообщение.
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Обработчик для консоли (StreamHandler).
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
