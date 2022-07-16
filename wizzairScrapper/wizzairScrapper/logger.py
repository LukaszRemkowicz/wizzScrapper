import logging
import logging.handlers
import os
import sys
from logging.handlers import (
    RotatingFileHandler,
)

from pierky.buffered_smtp_handler import BufferedSMTPHandler

FORMATTER = logging.Formatter("%(asctime)s|%(name)s|%(levelname)s|%(message)s", "%Y-%m-%d %H:%M:%S")


class SmartBufferHandler(logging.handlers.MemoryHandler):
    def __init__(self, num_buffered, *args, **kwargs):
        kwargs["capacity"] = num_buffered + 2  # +2 one for current, one for prepop
        super().__init__(*args, **kwargs)

    def emit(self, record) -> None:
        if len(self.buffer) == self.capacity - 1:
            self.buffer.pop(0)
        super().emit(record)


def get_buffered_handler(num: int = 2) -> SmartBufferHandler:
    handler = SmartBufferHandler(num_buffered=num, target=get_console_handler(), flushLevel=logging.ERROR)
    handler.setFormatter(FORMATTER)
    return handler


def get_console_handler(level=logging.INFO) -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FORMATTER)
    handler.setLevel(level)
    return handler


def get_file_handler(logfile: str = None, level=logging.DEBUG) -> RotatingFileHandler:
    handler = RotatingFileHandler(logfile, maxBytes=10000000, backupCount=20)  # 10MB
    handler.setFormatter(FORMATTER)
    handler.setLevel(level)
    return handler


def get_smtp_handler(
        mail_host, mail_port, mail_sender, mail_recievier_list, mail_username, mail_password
) -> BufferedSMTPHandler:
    handler = BufferedSMTPHandler(
        mailhost=(mail_host, mail_port),
        fromaddr=mail_sender,
        toaddrs=mail_recievier_list,
        subject='[title] Application Error',
        credentials=(mail_username, mail_password),
        secure=())
    handler.setFormatter(FORMATTER)
    # mail_handler.setLevel(logging.ERROR)
    return handler


class SetupLogger:
    """
    Sets logging class for application
    """
    extension = '.log'

    def __init__(self, logfile: str = 'application', settings: dict = None, root_path: str = ''):
        self.log_name = logfile
        self.root_dir = root_path
        self.settings = settings or {}

    def get_logger(self):
        return self._get_logger(**self.settings)

    @property
    def root_path(self):
        if os.path.exists(self.root_dir):
            return self.root_dir
        else:
            raise RuntimeError(f'Given path does not exits {self.root_dir}. Please create folder and re-run.')

    @property
    def file_log_name(self):
        return os.path.join(self.root_path, f'{self.log_name}{self.extension}')

    @property
    def debug_file_log_name(self):
        return os.path.join(self.root_path, f'{self.log_name}_debug{self.extension}')

    @property
    def error_file_log_name(self):
        return os.path.join(self.root_path, f'{self.log_name}_error{self.extension}')

    def _get_logger(
            self,
            logger_name: str = None,
            file_handler: bool = True,
            console_handler: bool = False,
            mail_handler: bool = False,
            buffered_handler: bool = False):

        if logger_name is None:
            logger = logging.getLogger()
        else:
            logger = logging.getLogger(logger_name)

        logger.setLevel(logging.DEBUG)  # better to have too much log than not enough

        if buffered_handler:
            logger.addHandler(get_buffered_handler())

        if console_handler:
            logger.addHandler(get_console_handler())

        if mail_handler:
            logger.addHandler(get_smtp_handler(*mail_handler))

        if file_handler:
            logger.addHandler(
                get_file_handler(logfile=self.file_log_name, level=logging.INFO))
            logger.addHandler(
                get_file_handler(logfile=self.error_file_log_name, level=logging.ERROR))
            logger.addHandler(
                get_file_handler(logfile=self.debug_file_log_name, level=logging.DEBUG))

        # With this pattern, it's rarely necessary to propagate the error up to parent
        logger.propagate = False
        return logger


getLogger = SetupLogger
