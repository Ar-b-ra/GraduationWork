import sys
from datetime import datetime
from pathlib import Path
from typing import Union

from loguru import logger

rootLogger = logger
now = datetime.now()
dt_string = now.strftime("%d %B %Y")
time_string = now.strftime("%H_%M_%S")


def init_logger_levels(
    root_logger_level: Union[int, str] = "DEBUG",
    file_handler_level: Union[int, str, None] = None,
    console_handler_level: Union[int, str, None] = None,
) -> None:
    """
    Инициализация логеров согласно конфигурации программы

    Основной уровень логирования используется в случае, если не указан уровень логирования для конкретного логгера

    :param root_logger_level: основной уровень логирования
    :param file_handler_level: уровень логирования в файл
    :param console_handler_level: уровень логирования в консоль

    """
    rootLogger.remove()
    rootLogger.add(
        sys.stdout,
        level=root_logger_level
        if console_handler_level is None
        else console_handler_level,
    )
    rootLogger.add(
        Path("../logs") / dt_string / time_string / "log_{time}.log",
        level=root_logger_level if file_handler_level is None else file_handler_level,
        rotation="1 MB",
    )
