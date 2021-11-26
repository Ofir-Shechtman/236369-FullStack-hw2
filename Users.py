import sqlite3
from dataclasses import dataclass
from typing import Union, List


@dataclass(frozen=True)
class User:
    username: str
    password: str


class IntegrityError(sqlite3.IntegrityError):
    pass


class Users:
    def __init__(self, db_file: str = 'users.db'):
        self.__connection = sqlite3.connect(db_file, isolation_level=None)
        self.__cursor = self.__connection.cursor()

    def close(self):
        self.__connection.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def insert(self, *args):
        """insert(self, user: User)
           insert(self, username: str,password: str)"""
        try:
            if len(args) == 1 and isinstance(args[0], User):
                self.__cursor.execute("insert into Users(username,password) values (?, ?)",
                                      (args[0].username, args[0].password))
            elif len(args) == 2:
                self.__cursor.execute("insert into Users(username,password) values (?, ?)", args)
            else:
                raise NotImplementedError()
        except sqlite3.IntegrityError as e:
            raise IntegrityError(e)

    def delete(self, username: str) -> int:
        return self.__cursor.execute("delete from Users where username=?", (username,)).rowcount

    def select(self, username: str) -> Union[User, bool]:
        self.__cursor.execute("select password from Users where username=?", (username,))
        password = self.__cursor.fetchone()
        if password:
            return User(username, password[0])
        else:
            return False

    def delete_all(self) -> int:
        return self.__cursor.execute("delete from Users").rowcount

    def select_all(self) -> List[User]:
        self.__cursor.execute("select username, password from Users order by lower(username)")
        return list(map(lambda x: User(*x), self.__cursor.fetchall()))

    def __repr__(self) -> str:
        data = self.select_all()
        if not data:
            return ''
        s = 'Users:\n'
        for u in data:
            s += str(u) + '\n'
        return s


if __name__ == '__main__':
    with Users() as users:
        print(users)
        users.delete_all()
        users.insert('Ofir', '1234')
        users.insert(User('admin', '0000'))
        print(users)
