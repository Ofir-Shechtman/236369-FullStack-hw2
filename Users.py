import sqlite3
from dataclasses import dataclass
from typing import Union, List

@dataclass(frozen=True)
class User:
     username: str
     password: str


class Users:
    def __init__(self, auto_commit: bool=True, db_file: str='users.db'):
        self.__connection = sqlite3.connect(db_file)
        self.__cursor = self.__connection.cursor()
        self.__auto_commit = auto_commit

    def close(self):
        if self.__auto_commit:
            self.commit()
        self.__connection.close()

    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        self.close()

    def commit(self):
        self.__connection.commit()

    def rollback(self):
        self.__connection.rollback()

    def insert(self, *args):
        """insert(self, user: User)
           insert(self, username: str,password: str)"""
        if len(args)==1 and isinstance(args[0], User):
            self.__cursor.execute("insert into Users(username,password) values (?, ?)", (args[0].username, args[0].password))
        elif len(args)==2:
            self.__cursor.execute("insert into Users(username,password) values (?, ?)", args)
        else:
            raise NotImplementedError()

    def delete(self, username:str) -> int:
        return self.__cursor.execute("delete from Users where username=?", (username,)).rowcount

    def select(self, username: str) -> Union[User, bool]:
        self.__cursor.execute("select password from Users where username=?", (username,))
        password = self.__cursor.fetchone()
        if password:
            return User(username, password)
        else:
            return False

    def delete_all(self) ->int:
        return self.__cursor.execute("delete from Users").rowcount

    def select_all(self) -> List[User]:
        self.__cursor.execute("select username, password from Users")
        return list(map(lambda x: User(*x), self.__cursor.fetchall()))

    def __repr__(self) -> str:
        data = users.select_all()
        if not data:
            return ''
        s = 'Users:\n'
        for u in users.select_all():
            s+=str(u)+'\n'
        return s


    

with Users() as users:
    print(users)
    users.delete_all()
    users.insert('Ofir', '1234')
    users.insert(User('admin', '0000'))
    print(users)
    users.rollback()
    


