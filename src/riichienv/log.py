import logging
import os


class BaseColors:
    BGRED = "\033[41m"
    BGGREEN = "\033[42m"
    BGYELLOW = "\033[43m"
    BGBLUE = "\033[44m"
    BGMAGENDA = "\033[45m"
    BGCYAN = "\033[46m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENDA = "\033[95m"
    CYAN = "\033[96m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class LevelFormatter(logging.Formatter):
    def __init__(self, formatters):
        super().__init__()
        self.formatters = formatters

    def format(self, record):
        formatter = self.formatters.get(record.levelno, self.formatters[logging.DEBUG])
        return formatter.format(record)


def get_logger(name: str | None = None) -> logging.Logger:
    if name is None:
        name = "riichienv"

    logger = logging.getLogger(name)
    if logger.handlers:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                logger.removeHandler(handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    formatters = {
        logging.DEBUG: logging.Formatter(
            f"{BaseColors.GREEN}%(asctime)s{BaseColors.ENDC} | "
            f"{BaseColors.CYAN}%(levelname)s{BaseColors.ENDC} - "
            f"{BaseColors.CYAN}%(message)s{BaseColors.ENDC}",
            datefmt="%Y-%m-%d %H:%M:%S",
        ),
        logging.INFO: logging.Formatter(
            f"{BaseColors.GREEN}%(asctime)s{BaseColors.ENDC} | "
            f"{BaseColors.CYAN}%(levelname)s{BaseColors.ENDC} - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ),
        logging.WARNING: logging.Formatter(
            f"{BaseColors.GREEN}%(asctime)s{BaseColors.ENDC} | "
            f"{BaseColors.YELLOW}WARN{BaseColors.ENDC} - "
            f"{BaseColors.YELLOW}%(message)s{BaseColors.ENDC}",
            datefmt="%Y-%m-%d %H:%M:%S",
        ),
        logging.ERROR: logging.Formatter(
            f"{BaseColors.GREEN}%(asctime)s{BaseColors.ENDC} | "
            f"{BaseColors.RED}%(levelname)s{BaseColors.ENDC} - "
            f"{BaseColors.RED}%(message)s{BaseColors.ENDC}",
            datefmt="%Y-%m-%d %H:%M:%S",
        ),
        logging.CRITICAL: logging.Formatter(
            f"{BaseColors.GREEN}%(asctime)s{BaseColors.ENDC} | "
            f"{BaseColors.RED}%(levelname)s{BaseColors.ENDC} - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ),
    }
    stream_handler.setFormatter(LevelFormatter(formatters))
    logger.addHandler(stream_handler)
    logger.setLevel(logging.INFO)

    if os.environ.get("DEBUG") == "1":
        logger.setLevel(logging.DEBUG)
        stream_handler.setLevel(logging.DEBUG)

    return logger
