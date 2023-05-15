from datetime import datetime
from enums import LevelType


class Level:
    def __init__(self, name:  str,
                 level_type: LevelType,
                 level_price: float,
                 level_date: datetime):
        self.name = name
        self.level_type = level_type
        self.level_price = level_price
        self.level_date = level_date
        self.level_validate = False

    def __str__(self):
        return f'Level: {self.name}, Type: {self.level_type}, Price: {self.level_price}, Date: {self.level_date}' \
                f'Validate: {self.level_validate}'

    @property
    def price(self):
        return self.level_price

    @property
    def l_date(self):
        return self.level_date
