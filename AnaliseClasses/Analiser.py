import config
from Exceptions import WrongTimeFrameException
from .Levels import Level

class Analiser:

    @staticmethod
    def tf_level_to_sec(tf: str) -> int:
        match tf:
            case '1h':
                return 3600
            case '4h':
                return 14400
            case '1d':
                return 86400
            case '1m':
                return 60
            case '5m':
                return 300
            case _:
                raise WrongTimeFrameException(tf)

    @staticmethod
    def calc_level_board(level: Level) -> tuple:
        up_board = level.level_price + (level.level_price * 0.01 * (config.level_width / 2))
        dn_board = level.level_price - (level.level_price * 0.01 * (config.level_width / 2))
        return up_board, dn_board


    @staticmethod
    def big_orders_in_range(big_orders: dict, level_price: float, type: str) -> bool:
        prices = list(big_orders.keys())
        third_price = prices[2]

        if type == 'up_level':
            max_order_price = level_price + (level_price * 0.01 * config.range_width)
            if third_price <= max_order_price:
                return True
            else:
                return False
        elif type == 'down_level':
            min_order_price = level_price - (level_price * 0.01 * config.range_width)
            if third_price >= min_order_price:
                return True
            else:
                return False



