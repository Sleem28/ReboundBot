import asyncio
import time
from datetime import datetime
from .InfoWriter import InfoWriter
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

    def __init__(self):
        self.__info_writer = InfoWriter()

    async def __task(self, symbol: str):
        # ------------------------------------------Global variables----------------------------------------------------+
        control_time_levels = 0                                  # Control time for searching levels.
        depth_control_time = 0                                   # Control time for searching big orders.
        lvl_proc = LevelProcessor(self.__data_getter)            # Level processor. Each task must have its own copy.
        tf_level_sec = Analiser.tf_level_to_sec(config.level_tf) # Level timeframe in seconds
        self.__is_position_open = False                          # The open position's flag

        last_up_level: Level                                     # Last up level from levels' array
        last_up_level_up_board = 0                               # The up board's price of the up level
        last_up_level_down_board = 0                             # The down board's price of the up level
        price_into_up_level = False                              # Flag of the price being in the up level

        last_down_level: Level                                   # Last down level from levels' array
        last_down_level_up_board = 0                             # The up board's price of the down level
        last_down_level_down_board = 0                           # The down board's price of the down level
        price_into_down_level = False                            # Flag of the price being in the down level

        last_cluster_bar: ClusterBar                             # Saved cluster bar
        control_time_cluster_bar = 0                             # Control time for saving the cluster bar
        tf_cluster_sec = Analiser.tf_level_to_sec(config.cluster_tf) # The cluster bar's timeframe
        cluster_bar = ClusterBar()                               # Current cluster bar
        cluster_pattern = ClusterPatternType.TYPE_NONE           # The type of one of cluster patterns

        first_big_order_price = 0.0                              # The price of the first big order
        second_big_order_price = 0.0                             # The price of the second big order
        third_big_order_price = 0.0                              # The price of the third big order

        first_control_order = 0.0                                # First standing control order
        second_control_order = 0.0                               # Second standing control order
        third_control_order = 0.0                                # Third standing control order

        big_order_stay_time = 0                                  # Time of standing big orders
        check_new_orders = False                                 # Flag of new founded big orders

        wrote_lvl_price = 0                                      # Price of the wrote level
        # --------------------------------------------------------------------------------------------------------------+

        async with self.__bm.aggtrade_futures_socket(symbol=symbol) as ts:
            print(f'{symbol} initialized.')
            while True:  # the main loop
                cur_time = time.time()
                req = await ts.recv()
                try:
                    futures_agg_trade = pd.DataFrame(req)
                except ValueError:
                    print(f'Error during reading agg trades {symbol} {req = }')
                    continue

                cur_price = float(futures_agg_trade[futures_agg_trade.index == 'p']['data'].values[0])
                side = bool(futures_agg_trade[futures_agg_trade.index == 'm']['data'].values[0]) # True - Sell, False - Buy
                volume = float(futures_agg_trade[futures_agg_trade.index == 'q']['data'].values[0])

                # ------------------------------Work with clusters_________________________________+
                cluster_bar.set_level(cur_price, side, volume)  # Fill the cluster bar all the time

                if cur_time > control_time_cluster_bar:         # Once a period save the current cluster bar
                    control_time_cluster_bar = cur_time - (cur_time % tf_cluster_sec) + tf_cluster_sec
                    last_cluster_bar = cluster_bar              # Copy the current cluster bar to last cluster bar
                    cluster_bar.clear_cluster_bar()             # Clear the current cluster bar
                # ------------------------------Not open position__________________________________+
                if not self.__is_position_open:
                    # ----------------------------- Level control---------------------------------+
                    if cur_time >= control_time_levels:
                        last_levels = await lvl_proc.find_levels(symbol, config.level_tf, config.limit)  # Get last up and down levels

                        if control_time_levels == 0:  # First run
                            lvl_proc.first_run()      # Set the first run flag in the class as false

                        control_time_levels = cur_time - (cur_time % tf_level_sec) + tf_level_sec

                        last_up_level: Level = last_levels[0]
                        last_down_level: Level = last_levels[1]

                    # _______________________Looking for the current price is near the up level________________________+
                    if last_up_level is not None:
                        last_up_level_up_board, last_up_level_down_board = Analiser.calc_level_board(last_up_level)  # Calculate the boards of the level
                        if last_up_level_down_board < cur_price < last_up_level_up_board:  # If the current price is between level boards
                            price_into_up_level = True
                        else:
                            price_into_up_level = False
                    # _______________________Looking for the current price is near the down level______________________+
                    if last_down_level is not None:
                        last_down_level_up_board, last_down_level_down_board = Analiser.calc_level_board(last_down_level) # Calculate the boards of the level
                        if last_down_level_down_board < cur_price < last_down_level_up_board:  # If the current price is between level boards
                            price_into_down_level = True
                        else:
                            price_into_down_level = False
                    # --------------------------------------Level conditions--------------------------------------------+
                    # Check the current price, whether it is between the level boundaries. And how many touches the level has.
                    up_lvl_conditions = True if price_into_up_level and last_up_level.level_touch_counter == 0 else False
                    down_lvl_conditions = True if price_into_down_level and last_down_level.level_touch_counter == 0 else False
                    # TODO пишем дальше описание и делаем схемы
                    # ___________________________Price into an up or down level________________________________________+
                    if up_lvl_conditions or down_lvl_conditions:

                        last_level = last_up_level if up_lvl_conditions else last_down_level
                        cluster_pattern_type = ClusterPatternType.TYPE_SELL if up_lvl_conditions else ClusterPatternType.TYPE_BUY
                        order_type = 'asks' if up_lvl_conditions else 'bids'
                        lvl_type = 'up_level' if up_lvl_conditions else 'down_level'
                        signal_type = 'SELL' if up_lvl_conditions else 'BUY'

                        up_board_price = last_up_level_up_board if up_lvl_conditions else last_down_level_up_board
                        down_board_price = last_up_level_down_board if up_lvl_conditions else last_down_level_down_board
                        analizer_lvl_board = last_up_level_down_board if up_lvl_conditions else last_down_level_up_board

                        if cur_time >= depth_control_time:
                            check_new_orders = False
                            big_orders_tpl = await self.__data_getter.get_large_applications(symbol=symbol,
                                                                                             order_type=order_type,
                                                                                             up_board_price=up_board_price,
                                                                                             down_board_price=down_board_price)
                            depth_control_time = cur_time + config.request_period_sec
                            is_big_orders = big_orders_tpl[0]
                            big_orders = big_orders_tpl[1]

                            # Если есть 3 крупные заявки в рэйндже
                            if is_big_orders and Analiser.big_orders_in_range(big_orders, analizer_lvl_board, lvl_type):
                                big_order_stay_time += config.request_period_sec
                            else:
                                big_order_stay_time = 0

                        # Если ордера стоят на месте более минуты
                        if big_order_stay_time >= config.validate_order_sec and not check_new_orders:
                            orders_prices = list(big_orders.keys())

                            first_big_order_price = orders_prices[0]
                            second_big_order_price = orders_prices[1]
                            third_big_order_price = orders_prices[2]

                            # Запишем в файл если было касание ценой первого уровня
                            if cur_price == first_big_order_price:
                                msg = f'Touch first order\n' \
                                      f'Instrument: {symbol}\nTouch order date: {datetime.now()}\nSignal type: {signal_type}\n' \
                                      f'Level price: {last_level.level_price}, ' \
                                      f'level date: {last_level.level_date}' \
                                      f'First order price: {first_big_order_price}'
                                self.__info_writer.write_info(symbol, msg)

                            if first_big_order_price != first_control_order or \
                                    second_big_order_price != second_control_order or \
                                    third_big_order_price != third_control_order:

                                first_control_order = first_big_order_price
                                second_control_order = second_big_order_price
                                third_control_order = third_big_order_price

                                first_order_usdt = big_orders[first_big_order_price] * first_big_order_price
                                second_order_usdt = big_orders[second_big_order_price] * second_big_order_price
                                third_order_usdt = big_orders[third_big_order_price] * third_big_order_price

                                found_cluster_pattern = True if cluster_pattern == cluster_pattern_type else False

                                e_info = f'Instrument: {symbol}\nSignal date: {datetime.now()}\nSignal type: {signal_type}\n' \
                                         f'Level price: {last_level.level_price}, ' \
                                         f'level date: {last_level.level_date}\nTouch quantity: ' \
                                         f'{last_level.level_touch_counter}\n1 order: {first_big_order_price} {first_order_usdt}USDT\n' \
                                         f'2 order: {second_big_order_price} {second_order_usdt}USDT\n' \
                                         f'3 order: {third_big_order_price} {third_order_usdt}USDT\n' \
                                         f'Cluster pattern: {f"Found {signal_type}" if found_cluster_pattern else "None"}\n\n'
                                print(e_info)
                                # if found_cluster_pattern:
                                #     last_cluster_bar.print_cluster_bar()

                                self.__info_writer.write_info(symbol, e_info)

                            check_new_orders = True
                    # TODO Сделать анализ последних 5 свечей Н1 на рост объема при подходе к уровню
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
            task = asyncio.create_task(self.__task(symbol), name=symbol)
            self.__TASKS.append(task)
        print('All tasks are completed')
        # task = asyncio.create_task(self.__task('JASMYUSDT'), name='JASMYUSDT')
        # self.__TASKS.append(task)

        for task in self.__TASKS:
            await task

        await self.__async__client.close_connection()
