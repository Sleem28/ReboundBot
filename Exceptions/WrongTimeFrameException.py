from .MyException import MyException


class WrongTimeFrameException(MyException):
    def __init__(self, tf:str):
        self.tf = tf

    def __str__(self):
        return f'Wrong timeframe {self.tf}'

