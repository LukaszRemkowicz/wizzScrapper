import argparse
import datetime
import json
import os
import pathlib
import re
import sys
from contextlib import contextmanager
from logging import RootLogger
from timeit import default_timer
from typing import Dict

from django.conf import settings
from django.core.mail import send_mail
from django.core.wsgi import get_wsgi_application

from wizzairScrapper.logger import SetupLogger
from wizzairScrapper.parsers import MainParser

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()


def create_parser():

    parser = argparse.ArgumentParser(description="Command line interface for 4clubbers.")

    parser.add_argument(
        '-lf',
        '--log-filename',
        dest='log_filename',
        help='custom file log name'
    )

    parser.add_argument(
        '-d',
        '--destination',
        dest='destination',
        help='Flight destination',
        nargs='+',
        metavar='Flight destination',
        type=str
    )
    parser.add_argument(
        '-f',
        '--from_flight',
        dest='from_flight',
        help='Flight from',
        nargs='+',
        metavar='Flight from',
        type=str
    )

    return parser


class CmdLineInterface:

    def __init__(self):

        parser = create_parser()
        self.args = parser.parse_args()
        self.used_command = " ".join(sys.argv)
        custom_log_name = self.args.log_filename or None
        self.session = Session(filename=custom_log_name)
        self.logger = self.session.logger

    def parse(self) -> None:

        options = self.get_options()

        self.logger.debug(f'Session parameters: {options}')
        self.logger.debug(f'Session invoked with following parameters: {self.used_command}')
        self.logger.info(f'Session logs will be stored under name: {self.session.logfile}')


        try:
            with self.elapsed_timer() as elapsed:
                elapsed()

                if self.args.destination and self.args.from_flight:
                    MainParser(self.logger).get_data()

            time_elapsed = elapsed()

            if time_elapsed > 60:
                result = f'{int(time_elapsed // 60)} min and {time_elapsed % 60} s.'
            else:
                result = f'{time_elapsed} s'

            result = re.sub(r'([^\n].*)\.([^\n].*)', r'\1', result)
            self.logger.info(f'Finished in {result} s')

            title = f'[WizzairScrapper] Sukces {self.session.id}'
            message = f'Wykonywanie komendy {self.used_command} zakonczylo sukcesem.' \
                      f'\n\n Więcej szczegółów znjdziesz: {self.session.logfile} \n\n v{settings.VERSION}'

            send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [settings.DEFAULT_FROM_EMAIL])

        except Exception as e:

            title = f'[WizzairScrapper] Nie powodzenie. {self.session.id}'
            message = f'Wykonywanie komendy {self.used_command} zakonczylo sie bledem  ' \
                      f'"{e}" -------------- \n\n  Więcej szczegółów znjdziesz: ' \
                      f'{self.session.logfile} v{settings.VERSION}'
            self.logger.exception(f'error during command execution {self.used_command}:')

            send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [settings.DEFAULT_FROM_EMAIL])

    @contextmanager
    def elapsed_timer(self):

        start = default_timer()
        elapser = lambda: default_timer() - start
        yield lambda: elapser()
        end = default_timer()
        elapser = lambda: end - start

    def get_options(self) -> Dict:
        return {
        }

class Session:
    """  Class to take control over session. Keep logs, data in sync. one logger, one session """

    session_filename = 'linkssesion.json'
    session_path = '..'

    def __init__(self, session_id=None, filename=None):
        self.session_id = session_id or self.get_new_session_id()
        self._current_session_logfile = filename or f'session_{self.session_id}'
        self.logger = self._setup_session_logger()

        self.content = self.get_or_create_content()

        self.logger.info(f'session ID: {self.session_id}')

    @property
    def id(self):
        return self.session_id

    def set_id(self, id_):
        self.session_id = id_

    @property
    def logfile(self):
        return self._current_session_logfile

    def _setup_session_logger(self) -> RootLogger:
        logging_settings = {'console_handler': True}

        self.logger = SetupLogger(
            logfile=self._current_session_logfile,
            settings=logging_settings,
            root_path=settings.LOGGING_ROOT_PATH
        ).get_logger()

        print(f'session logs: {self._current_session_logfile}')
        return self.logger

    def get_new_session_id(self) -> str:
        return datetime.datetime.now().strftime('%y%m%d-%H%M%S')

    def create_session_cookie(self) -> Dict:
        return {'id': self.get_new_session_id(), 'data': {}}

    def set_session_content(self):
        pass

    def get_or_create_content(self) -> Dict:
        session_file = pathlib.Path(self.session_path, self.session_filename)

        if session_file.exists():
            with open(session_file, 'r') as sessionFile:
                data = json.load(sessionFile)
                if data.get(self.session_id):
                    self.logger.info(f'Session cookie exists with id:{self.session_id}')
                    return data.get(self.session_id)
                else:
                    self.logger.info(f'Creating new session cookie for id:{self.session_id}')
                    data[self.session_id] = self.create_session_cookie()
        else:
            with open(session_file, 'w') as sessionFile:
                data = {self.session_id: self.create_session_cookie()}
                json.dump(data, sessionFile, indent=4, ensure_ascii=False)

        with open(session_file, 'w') as sessionFile:
            json.dump(data, sessionFile, indent=4, ensure_ascii=False)

        return data[self.session_id]


if __name__ == '__main__':
    CmdLineInterface().parse()
