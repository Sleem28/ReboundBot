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
            case _:
                raise WrongTimeFrameException(tf)

    @staticmethod
    def calc_level_board(level: Level) -> tuple:
        up_board = level.price + (level.price * 0.01 * (config.level_width / 2))
        dn_board = level.price - (level.price * 0.01 * (config.level_width / 2))
        return up_board, dn_board



