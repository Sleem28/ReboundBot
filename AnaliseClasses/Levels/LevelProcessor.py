import pandas as pd
from AnaliseClasses import DataGetter
from ..Candle import Candle
from .Level import Level
from enums import LevelType
import config


class LevelProcessor:
    __VOL_SMA_PERIOD = config.volume_sma_period
    __VALIDATE_PERCENT = config.percent_move_from_level
    __SEC_LIMIT = 4
    __FIRST_RUN_LEVEL_FIND = True
    """Manage the process of finding the support and the resistance levels who has one touch of the price"""

    def __init__(self, data_getter: DataGetter):
        self.__data_getter = data_getter
        self.__active_levels = []
        self.__level_counter = 0

    async def find_levels(self, symbol: str, tf: str, limit: int) -> list:
        """
        Look for levels by last candles by the symbol and limit params
        :param symbol:  symbol name
        :param tf:  timeframe
        :param limit:  a quantity of candles
        :return: a list with last Up and DOWN levels
        """
        limit = limit if self.__FIRST_RUN_LEVEL_FIND else self.__SEC_LIMIT  # The candle's limit for calculating
        candles = await self.__data_getter.get_candles(symbol=symbol, tf=tf, limit=limit + self.__VOL_SMA_PERIOD)

        candles = candles.iloc[::-1]
        max_index = candles.index.max()
        start_index = max_index - self.__VOL_SMA_PERIOD

        while start_index > 2:
            finish_index = start_index + self.__VOL_SMA_PERIOD
            vol_avg = candles.iloc[start_index: finish_index].Volume.astype(
                float).sum() / self.__VOL_SMA_PERIOD  # Finding SMA by volume

            first_candle = await self.__create_candle(candles.iloc[start_index - 2])
            second_candle = await self.__create_candle(candles.iloc[start_index - 1])
            third_candle = await self.__create_candle(candles.iloc[start_index])

            self.__validate_founded_levels(first_candle) # Check founded levels

            is_level = self.__find_level_pattern(first_candle, second_candle, third_candle, vol_avg) # Looking for the pattern
            name = f'Lv:{self.__level_counter}, symbol: {symbol}'

            if is_level == LevelType.TYPE_UP:  # If the up pattern found
                self.__level_counter += 1

                lvl = Level(name,
                            LevelType.TYPE_UP,
                            second_candle.high,
                            second_candle.time)

                self.__active_levels.append(lvl)   # Add the level to the list
            elif is_level == LevelType.TYPE_DOWN:  # If the down pattern found
                self.__level_counter += 1

                lvl = Level(name,
                            LevelType.TYPE_DOWN,
                            second_candle.low,
                            second_candle.time)

                self.__active_levels.append(lvl)   # Add the level to the list
            start_index -= 1

        return self.__last_levels()

    async def __create_candle(self, df_candle: pd.DataFrame) -> Candle:
        """
        Create the candle class's object by params in the dataframe
        :param df_candle: - a dataframe with candles params
        :return: object Candle
        """
        c_time = df_candle.Time
        c_open = float(df_candle.Open)
        c_high = float(df_candle.High)
        c_low = float(df_candle.Low)
        c_close = float(df_candle.Close)
        c_volume = float(df_candle.Volume)

        candle = Candle(c_time, c_open, c_high, c_low, c_close, c_volume)
        return candle

    def __find_level_pattern(self, first_candle: Candle,
                             second_candle: Candle,
                             third_candle: Candle,
                             vol_sma: float) -> LevelType:
        """
        Looking for an up or down pattern by three last candles
        :param first_candle:
        :param second_candle:
        :param third_candle:
        :param vol_sma:
        :return: - type of the level or none
        """
        vol_coeff = config.vol_coeff
        vol_lvl = vol_sma * vol_coeff
        if first_candle.volume > vol_lvl or second_candle.volume > vol_lvl or third_candle.volume > vol_lvl:
            halh_candle_price = (second_candle.high + second_candle.low) * 0.5

            if first_candle.close <= halh_candle_price:  # The up pattern's conditions
                if second_candle.high > first_candle.high and second_candle.high > third_candle.high:
                    return LevelType.TYPE_UP
            elif first_candle.close >= halh_candle_price:  # The down pattern's conditions
                if second_candle.low < first_candle.low and second_candle.low < third_candle.low:
                    return LevelType.TYPE_DOWN
            else:
                return LevelType.TYPE_NONE
        else:
            return LevelType.TYPE_NONE

    def __validate_founded_levels(self, last_candle: Candle):
        """
        Delete all breakout levels
        :param last_candle: - current close
        """
        up_level_valid_price = last_candle.low + (last_candle.low * 0.01 * self.__VALIDATE_PERCENT)
        dn_level_valid_price = last_candle.high - (last_candle.high * 0.01 * self.__VALIDATE_PERCENT)

        for lvl in self.__active_levels:

            if lvl.level_type == LevelType.TYPE_UP: # For the up level
                if last_candle.low > lvl.level_price: # If the candle is higher than the level then delete it
                    self.__active_levels.remove(lvl)
                    continue # Next level

                if not lvl.level_touch and last_candle.high > lvl.level_price and lvl.level_validate: # If there was no touch and the price touched the level and the level is valid
                    lvl.level_touch = True
                    continue
                elif lvl.level_touch and last_candle.high < lvl.level_price and lvl.level_validate:   # If there was touch and the price moved away from the level and the level is valid
                    lvl.level_touch_counter += 1
                    lvl.level_touch = False
                    continue

                if lvl.level_price > up_level_valid_price and not lvl.level_validate:                 # If the price moved away from the level by 3 percent
                    lvl.level_validate = True

            elif lvl.level_type == LevelType.TYPE_DOWN:  # For the down level
                if last_candle.high < lvl.level_price:  # If the candle is lower than the level then delete it
                    self.__active_levels.remove(lvl)
                    continue

                if not lvl.level_touch and last_candle.low < lvl.level_price and lvl.level_validate:  # If there was no touch and the price touched the level and the level is valid
                    lvl.level_touch = True
                    continue
                elif lvl.level_touch and last_candle.low > lvl.level_price and lvl.level_validate:    # If there was touch and the price moved away from the level and the level is valid
                    lvl.level_touch_counter += 1
                    lvl.level_touch = False
                    continue

                if lvl.level_price < dn_level_valid_price and not lvl.level_validate:
                    lvl.level_validate = True
                    continue

    def __last_levels(self) -> list:
        """
        Looking for last two levels of TYPE_UP and TYPE_DOWN
        :return: list with last founded levels
        """
        last_levels = [None, None]
        is_up = False
        is_down = False

        for lvl in self.__active_levels:
            if not is_up and lvl.level_type == LevelType.TYPE_UP and lvl.level_validate:
                last_levels[0] = lvl
                is_up = True
            elif not is_down and lvl.level_type == LevelType.TYPE_DOWN and lvl.level_validate:
                last_levels[1] = lvl
                is_down = True

            if is_up and is_down:
                return last_levels

        return last_levels

    def first_run(self):
        self.__FIRST_RUN_LEVEL_FIND = False