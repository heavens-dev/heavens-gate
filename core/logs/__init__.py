import os
import sys

from loguru import logger

DEFAULT_PATH_TO_LOGS = "logs"
STDERR_LOGS_FORMAT = "{time:DD MMM YYYY at HH:mm:ss.SSS} | <level>{level}</level> | {file}/{function}:{line} -> {message} | {extra}"
FILE_LOGS_FORMAT = "{time:DD MMM YYYY at HH:mm:ss.SSS} | {level} | {file}/{function}:{line} -> {message} | {extra}"

core_logger = logger.bind(service="core")
bot_logger = logger.bind(service="bot")

def init_file_loggers(path: str, is_debug: bool = False):
    path = os.path.abspath(path) + "/debug" if is_debug else os.path.abspath(path)

    core_logger.add(
        os.path.join(path, "core", "core.log"),
        format=FILE_LOGS_FORMAT,
        enqueue=True, # ? makes output to file thread-safe
        rotation="3 MB",
        compression="zip",
        filter=lambda record: record["extra"]["service"] == "core",
        level="INFO" if not is_debug else "DEBUG"
    )

    bot_logger.add(
        os.path.join(path, "bot", "bot.log"),
        format=FILE_LOGS_FORMAT,
        enqueue=True,
        rotation="3 MB",
        compression="zip",
        filter=lambda record: record["extra"]["service"] == "bot",
        level="INFO" if not is_debug else "DEBUG"
    )

    core_logger.info("File loggers initialized")

def init_terminal_logger(is_debug: bool = False):
    logger.add(
        sys.stderr,
        format=STDERR_LOGS_FORMAT,
        enqueue=True,
        colorize=True,
        backtrace=False,
        level="INFO" if not is_debug else "DEBUG"
    )

    core_logger.info("oh hello there! Terminal logger initialized")

def add_loggers(file_path: str, is_debug: bool = False):
    logger.remove() # ? remove default logger
    init_file_loggers(file_path, is_debug=is_debug)
    init_terminal_logger(is_debug=is_debug)

if __name__ == "__main__":
    add_loggers(DEFAULT_PATH_TO_LOGS, is_debug=True)
    core_logger.debug("Debug log")
    core_logger.info("Info log")
    core_logger.warning("Warning log")
    core_logger.error("Error log")
