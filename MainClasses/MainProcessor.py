import asyncio
import time
import pandas as pd
from AnaliseClasses import ClusterBar
from enums import ClusterPatternType
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
        tf_level_sec = Analiser.tf_level_to_sec(config.level_tf)
        tf_cluster_sec = Analiser.tf_level_to_sec(config.cluster_tf)
        self.__is_position_open = False

        last_up_level: Level = None
        last_up_level_up_board = 0
        last_up_level_down_board = 0
        price_into_up_level = False

        last_down_level: Level = None
        last_down_level_up_board = 0
        last_down_level_down_board = 0
        price_into_down_level = False

        control_time_cluster_bar = 0
        tf_cluster_sec = Analiser.tf_level_to_sec(config.cluster_tf)
        cluster_bar = ClusterBar()
        cluster_pattern = ClusterPatternType.TYPE_NONE

        first_big_order_price = 0.0
        second_big_order_price = 0.0
        third_big_order_price = 0.0
        big_order_stay_time = 0

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
                side = bool(futures_agg_trade[futures_agg_trade.index == 'm']['data'].values[0])
                volume = float(futures_agg_trade[futures_agg_trade.index == 'q']['data'].values[0])

                # ------------------------------Work with clusters_________________________________+
                cluster_bar.set_level(cur_price, side, volume)  # Заполняем кластер бар все время

                if cur_time > control_time_cluster_bar: # Раз в период проверим кластер бар на торможение
                    cluster_pattern = cluster_bar.check_pattern()
                    control_time_cluster_bar = cur_time - (cur_time % tf_cluster_sec) + tf_cluster_sec
                    cluster_bar.clear_cluster_bar()
                # ------------------------------Not open position__________________________________+
                if not self.__is_position_open:
                    # ----------------------------- Level control---------------------------------+
                    if cur_time >= control_time_levels:
                        last_levels = await lvl_proc.find_levels(symbol, config.level_tf, config.limit)
                        if control_time_levels == 0:
                            lvl_proc.FIRST_RUN_LEVEL_FIND = False
                        control_time_levels = cur_time - (cur_time % tf_level_sec) + tf_level_sec

                        last_up_level: Level = last_levels[0]
                        last_down_level: Level = last_levels[1]

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
                    if price_into_up_level and last_up_level.level_touch_counter == 0:
                        # print(f'Price near up level {symbol} {last_up_level.level_price} {last_up_level.level_date} {last_up_level.level_touch_counter}')
                        if cur_time >= depth_control_time:
                            big_asks = await self.__data_getter.get_large_applications(symbol=symbol,
                                                                                       order_type='asks',
                                                                                       up_board_price=last_up_level_up_board,
                                                                                       down_board_price=last_up_level_down_board)
                            depth_control_time = cur_time + config.request_period_sec
                            is_big_asks = big_asks[0]
                            big_ask_orders = big_asks[1]

                            # Если есть 3 крупные заявки на продажу в рэйндже
                            if is_big_asks and Analiser.big_orders_in_range(big_ask_orders, last_up_level_down_board,
                                                                            'up_level'):
                                big_order_stay_time += config.request_period_sec
                            else:
                                big_order_stay_time = 0
                        # Если ордера стоят на месте более минуты
                        if big_order_stay_time >= config.validate_order_sec:
                            print()
                            print(f'Found big sell orders by {symbol} {big_ask_orders} lvl price: {last_up_level.level_price} {last_up_level.level_date} {last_up_level.level_touch_counter}')
                            print(cluster_pattern)
#TODO Писать условия для входа и логировать. Потом тестить.

                    # _______________________________Price into a down level___________________________________________+
                    elif price_into_down_level and last_down_level.level_touch_counter == 0:
                        # print(f'Price near down level {symbol} {last_down_level.level_price} {last_down_level.level_date} {last_down_level.level_touch_counter}')
                        if cur_time >= depth_control_time:
                            big_bids = await self.__data_getter.get_large_applications(symbol=symbol,
                                                                                       order_type='bids',
                                                                                       up_board_price=last_down_level_up_board,
                                                                                       down_board_price=last_down_level_down_board)
                            depth_control_time = cur_time + config.request_period_sec
                            is_big_bids = big_bids[0]
                            big_bid_orders = big_bids[1]

                            # Если есть 3 крупные заявки на покупку в рэйндже
                            if is_big_bids and Analiser.big_orders_in_range(big_bid_orders, last_down_level_up_board,
                                                                            'down_level'):
                                big_order_stay_time += config.request_period_sec
                            else:
                                big_order_stay_time = 0
                        # Если ордера стоят на месте более минуты
                        if big_order_stay_time >= config.validate_order_sec:
                            print()
                            print(f'Found big buy orders by {symbol} {big_bid_orders} lvl price: {last_down_level.level_price} {last_down_level.level_date} {last_down_level.level_touch_counter}')
                            print(cluster_pattern)
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
            task = asyncio.create_task(self.__task(symbol, config.level_tf, config.limit), name=symbol)
            self.__TASKS.append(task)
        print('All tasks are completed')
        # task = asyncio.create_task(self.__task('JASMYUSDT', config.level_tf, config.limit), name='JASMYUSDT')
        # self.__TASKS.append(task)

        for task in self.__TASKS:
            await task

        await self.__async__client.close_connection()
