import os
import sys

from loguru import logger

PATH_TO_LOGS = "logs"
STDERR_LOGS_FORMAT = "{time:DD MMM YYYY at HH:mm:ss.SSS} | <level>{level}</level> | {file}/{function}:{line} -> {message} | {extra}"
FILE_LOGS_FORMAT = "{time:DD MMM YYYY at HH:mm:ss.SSS} | {level} | {file}/{function}:{line} -> {message} | {extra}"

core_logger = logger.bind(service="core")
bot_logger = logger.bind(service="bot")

logger.remove()
logger.add(
    sys.stderr,
    format=STDERR_LOGS_FORMAT,
    enqueue=True, # ? makes logging to console asynchronous
    colorize=True,
    backtrace=False,
)

def init_file_loggers(path: str, is_debug: bool = False):
    path = os.path.abspath(path) + "/debug" if is_debug else os.path.abspath(path)

    core_logger.add(
        os.path.join(path, "core", "core.log"),
        format=FILE_LOGS_FORMAT,
        enqueue=True,
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


if __name__ == "__main__":
    init_file_loggers(PATH_TO_LOGS)
