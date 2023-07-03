import logging


def get_logger() -> logging.Logger:
    format = "%(levelname)s:%(filename)s:%(lineno)d: %(message)s"
    logging.basicConfig(format=format)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    return logger
