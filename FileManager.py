import os.path
from pathlib import Path
from abc import ABC
from typing import Callable
import json

SENSITIVE_FILES = ['users.db', 'config.py']


class BadExtension(BaseException):
    pass


class FileManager:
    def __init__(self):
        with open('mime.json', 'r') as mime_file:
            mime_list = json.load(mime_file)['mime-mapping']
        self._mime = {d['extension']: d['mime-type'] for d in mime_list}

    def get_mime_type(self, extension):
        mime_type = self._mime.get(extension)
        if not mime_type:
            raise BadExtension
        return self._mime[extension]

    async def get_readable_file(self, path):
        return ReadableFile(path, self.get_mime_type)


class File(ABC):
    def __init__(self, path: str):
        self._path = Path(path.strip('/'))
        if not os.path.exists(self.path):
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
    pass
