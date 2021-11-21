import pathlib
import abc


class File(abc.ABC):
    def __init__(self, path: pathlib.Path):
        self.path = path[1:]#= pathlib.Path
        self.mime_type = "text/plain"




class ReadableFile(File):
    def __init__(self, path: str):
        super().__init__(path)
        self.extension = 'txt'


class DynamicPage(File):
    pass


class FileManager:
    @staticmethod
    def get(path: str) -> File:
        return ReadableFile(path)