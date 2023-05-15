import asyncio
import datetime
import time
import pandas as pd
from pandas.errors import ParserError
from keys import api_key, api_secret
from binance import AsyncClient, BinanceSocketManager, Client
from AnaliseClasses import LevelProcessor, DataGetter
from AnaliseClasses import Level
import config
from AnaliseClasses import Analiser


class MainProcessor:
    __async__client: AsyncClient
    __client: Client
    __bm: BinanceSocketManager
    __data_getter: DataGetter
    __is_position_open: bool
    __TASKS = []
    __SYMBOLS = []

    async def __task(self, symbol: str, tf: str, limit: int):

        control_time_levels = 0
        depth_control_time = 0
        lvl_proc = LevelProcessor(self.__data_getter)
        tf_level_sec = Analiser.tf_level_to_sec(config.tf)
        self.__is_position_open = False

        last_up_level: Level = None
        last_up_level_up_board = 0
        last_up_level_down_board = 0
        price_into_up_level = False

        last_down_level: Level = None
        last_down_level_up_board = 0
        last_down_level_down_board = 0
        price_into_down_level = False

        async with self.__bm.aggtrade_futures_socket(symbol=symbol) as ts:
            print(f'{symbol} initialized.')
            while True:  # Главный цикл
                cur_time = time.time()
                req = await ts.recv()
                try:
                    futures_agg_trade = pd.DataFrame(req)
                except ValueError:
                    print(f'Error during reading agg trades {symbol} {req = }')
                    continue

                cur_price = float(futures_agg_trade[futures_agg_trade.index == 'p']['data'].values[0])
                # print(f'{symbol} -> {cur_price}')
                # side = 'Sell' if bool(futures_agg_trade[futures_agg_trade.index == 'm']['data'].values[0]) else 'Buy'
                # ------------------------------Not open position_____________________________+
                if not self.__is_position_open:
                    # ----------------------------- Level control---------------------------------+
                    if cur_time >= control_time_levels:
                        #print(f'Find levels {symbol = } {datetime.datetime.now()} {control_time_levels = }')
                        last_levels = await lvl_proc.find_levels(symbol, config.tf, config.limit)
                        if control_time_levels == 0:
                            lvl_proc.FIRST_RUN_LEVEL_FIND = False
                        control_time_levels = cur_time - (cur_time % tf_level_sec) + tf_level_sec
                        last_up_level: Level = last_levels[0]
                        # if last_up_level is not None:
                        #     print(f'Last up level {symbol}: price{last_up_level.price}, date{last_up_level.l_date}')
                        last_down_level: Level = last_levels[1]
                        # if last_down_level is not None:
                        #     print(f'Last down level {symbol}: price{last_down_level.price}, date{last_down_level.l_date}')

                    # _______________________Looking for the current price is near the up level________________________+
                    if last_up_level is not None:
                        last_up_level_up_board, last_up_level_down_board = Analiser.calc_level_board(last_up_level)
                        if last_up_level_down_board < cur_price < last_up_level_up_board:
                            price_into_up_level = True
                        else:
                            price_into_up_level = False
                    # _______________________Looking for the current price is near the down level______________________+
                    if last_down_level is not None:
                        last_down_level_up_board, last_down_level_down_board = Analiser.calc_level_board(
                            last_down_level)
                        if last_down_level_down_board < cur_price < last_down_level_up_board:
                            price_into_down_level = True
                        else:
                            price_into_down_level = False

                    # _______________________________Price into an up level____________________________________________+
                    if price_into_up_level:
                        #print(f'Price near up level {symbol} {last_up_level.price} {last_up_level.level_date}')

                        if cur_time >= depth_control_time:
                            big_asks = await self.__data_getter.get_large_applications(symbol=symbol,
                                                                                       order_type='asks',
                                                                                       up_board_price=last_up_level_up_board,
                                                                                       down_board_price=last_up_level_down_board)
                            depth_control_time = cur_time + config.request_period_sec

                        if big_asks[0]: # Если есть 3 крупные заявки на продажу
                            pass

                    # _______________________________Price into a down level___________________________________________+
                    elif price_into_down_level:
                        #print(f'Price near down level {symbol} {last_down_level.price} {last_down_level.level_date}')

                        if cur_time >= depth_control_time:
                            big_bids = await self.__data_getter.get_large_applications(symbol=symbol,
                                                                                       order_type='bids',
                                                                                       up_board_price=last_down_level_up_board,
                                                                                       down_board_price=last_down_level_down_board)
                            depth_control_time = cur_time + config.request_period_sec

                        if big_bids[0]: # Если есть 3 крупные заявки на покупку
                            pass
                # ------------------------------Position opened____________________________________+
                else:
                    pass

    async def run(self):

        self.__async__client = await AsyncClient.create(api_key=api_key, api_secret=api_secret)
        self.__data_getter = DataGetter(self.__async__client)
        await self.__data_getter.get_exchange_info()
        self.__SYMBOLS = await self.__data_getter.get_all_futures()
        self.__bm = BinanceSocketManager(self.__async__client)

        for symbol in self.__SYMBOLS:
            task = asyncio.create_task(self.__task(symbol, config.tf, config.limit), name=symbol)
            self.__TASKS.append(task)
        print('All tasks are completed')

        for task in self.__TASKS:
            await task

        await self.__async__client.close_connection()
