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

def init_file_loggers(path: str):
    core_logger.add(
        os.path.join(path, "core", "core.log"),
        format=FILE_LOGS_FORMAT,
        enqueue=True,
        rotation="3 MB",
        compression="zip",
        filter=lambda record: record["extra"]["service"] == "core",
        level="INFO"
    )

    bot_logger.add(
        os.path.join(path, "bot", "bot.log"),
        format=FILE_LOGS_FORMAT,
        enqueue=True,
        rotation="3 MB",
        compression="zip",
        filter=lambda record: record["extra"]["service"] == "bot",
        level="INFO"
    )

    core_logger.info("File loggers initialized")


if __name__ == "__main__":
    init_file_loggers(PATH_TO_LOGS)
