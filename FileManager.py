import os.path
from pathlib import Path
from abc import ABC
from typing import Callable
import json
import re

SENSITIVE_FILES = ['users.db', 'config.py']
PATTERN = '{%(.*?)%}'


class EvalFailed(BaseException):
    pass


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class FileManager(metaclass=Singleton):
    def __init__(self):
        with open('mime.json', 'r') as mime_file:
            mime_list = json.load(mime_file)['mime-mapping']
        self._mime = {d['extension']: d['mime-type'] for d in mime_list}

    def get_mime_type(self, extension):
        return self._mime.get(extension, 'text/plain')

    async def get_readable_file(self, path):
        return ReadableFile(path, self.get_mime_type)

    @staticmethod
    async def get_dynamic_page(path):
        return DynamicPage(path)


class File(ABC):
    def __init__(self, path: str):
        self._path = Path(path.strip('/'))
        if not os.path.isfile(self.path):
            raise FileNotFoundError
        if self.is_sensitive():
            raise PermissionError

    def is_sensitive(self):
        for sensitive_file in SENSITIVE_FILES:
            if os.path.samefile(self.path, sensitive_file):
                return True
        return False

    @property
    def path(self):
        return self._path


class ReadableFile(File):
    def __init__(self, path: str, get_mime_type: Callable):
        super().__init__(path)
        self._mime_type = get_mime_type(self.path.suffix.strip('.'))

    @property
    def mime_type(self):
        return self._mime_type


class DynamicPage(File):
    def __init__(self, path: str):
        super().__init__(path)
        with open(self.path, 'r') as dp_file:
            self.content = dp_file.read()

    def render(self, user, params):
        rendered_content = self.content
        while re.search(PATTERN, rendered_content, flags=re.DOTALL):
            re_obj = re.search(PATTERN, rendered_content, flags=re.DOTALL)
            substring = re_obj.group(1).replace('\n', '')
            indexes = re_obj.regs[0]
            try:
                evaluated = eval(substring, {'user': user, 'params': params})
            except Exception as e:
                raise EvalFailed
            rendered_content = rendered_content[:indexes[0]] + evaluated + rendered_content[indexes[1]:]
        return rendered_content
