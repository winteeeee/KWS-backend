import logging
import logging.handlers
import os


def get_logger(name: str = 'log',
               log_level: any = logging.INFO,
               save_path: str = None):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s: %(message)s')

    stream_handler = _get_stream_handler(formatter)
    if len(logger.handlers) == 0:
        logger.addHandler(stream_handler)

    if save_path is not None:
        _init_path(save_path)
        file_handler = _get_file_handler(save_path, name, formatter)
        if len(logger.handlers) == 0:
            logger.addHandler(file_handler)

    return logger


def _get_file_handler(path: str, name: str, formatter):
    file_path = path + '/' + name
    handler = logging.handlers.TimedRotatingFileHandler(filename=file_path, when='midnight',
                                                        interval=1, encoding='utf-8')
    handler.suffix = "%Y%m%d.log"
    handler.setFormatter(formatter)

    return handler


def _get_stream_handler(formatter):
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    return handler


def _init_path(path: str):
    if not os.path.exists(path):
        os.makedirs(path)
