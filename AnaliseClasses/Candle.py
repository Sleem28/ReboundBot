from datetime import datetime


class Candle:

    def __init__(self, c_time: datetime, c_open: float, c_high: float, c_low: float, c_close: float, c_volume: float):
        self.time = c_time
        self.open = c_open
        self.high = c_high
        self.low = c_low
        self.close = c_close
        self.volume = c_volume

    def __str__(self):
        return f'Candle date = {self.time}, open = {self.open}, high = {self.high} ' \
               f'low = {self.low}, close = {self.close}, volume = {self.volume}'
