import pandas
from binance import AsyncClient
import asyncio
import config
from asyncio.exceptions import TimeoutError
import pandas as pd


class DataGetter:
    """Get a different data form binance servers."""
    __WEIGHT = 0
    __WEIGHT_LIMIT = 1150  # Requests limit per a minute
    __SYMBOL_COUNTER = 0
    __exchange_info = {}

    def __init__(self, client: AsyncClient):
        self.__client = client

    async def get_exchange_info(self):
        """
        Get an exchange info from a server
        :return: - json with the full exchange info
        """
        req_limit = 10
        req_counter = 0
        req_type = 'exchange'
        loop = asyncio.get_running_loop()
        while req_counter < req_limit:
            try:
                req = await self.__client.futures_exchange_info()
                loop.call_soon(asyncio.create_task, self.__set_weight(req_type))
                self.__exchange_info = req
                return
            except TimeoutError as e:
                print(f'Error during getting an exchange info. {e}')
                print(f'Error: {e}')
                req_counter += 1
                continue

    async def get_all_futures(self, ) -> list:
        """
        This method finds symbol names from client.futures_exchange_info()
        @return: the list with the futures names
        """
        try:
            df = pd.DataFrame(self.__exchange_info['symbols'])
            df = df[df.symbol.str.contains('USDT')]
            lst = list(df['symbol'])
            return lst
        except pd.errors.DataError as e:
            print(f'Error during getting symbol names {e}')
            print(f'Error: {e}')
            return []

    async def get_candles(self, symbol: str, tf: str, limit: int) -> pd.DataFrame:
        """
        Get klines from the server and convert them to the pandas dataframe
        :param symbol: - one of the futures names
        :param tf: - timeframe
        :param limit: - quantity of candles
        :return: - dataframe
        """
        req_limit = 10
        req_counter = 0
        req_type = 'kline'
        loop = asyncio.get_running_loop()
        # print(f'Cur weight {DataGetter.__WEIGHT}')
        while req_counter < req_limit:
            if DataGetter.__WEIGHT >= DataGetter.__WEIGHT_LIMIT:
                print(f'Requests weight is more than limit {DataGetter.__WEIGHT}')
                await asyncio.sleep(60)
                continue
            try:
                req = await self.__client.futures_klines(symbol=symbol, interval=tf, limit=limit)
                print(f'Kline data got by {symbol} {req_counter = }')
                try:
                    df = pandas.DataFrame(req)
                    df = df.iloc[:, :6]
                    df.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
                    df.Time = pd.to_datetime(df.Time, unit='ms')
                    loop.call_soon(asyncio.create_task, self.__set_weight(req_type, limit))
                    return df
                except Exception as e:
                    print(f'Error during getting klines info {req}')
                    print(f'Error: {e}')
                    req_counter += 1
                    continue
            except TimeoutError:
                print(f'{symbol} The error during getting a data from a server.')
                await asyncio.sleep(1)
                req_counter += 1
                continue

    async def __set_weight(self, req_type: str, limit=1) -> None:
        """
        Add a weight to the weight counter for different requests
        :param limit: - quantity
        :param req_type: - request's type
        """
        weight = 0
        if req_type == 'kline':
            if limit >= 1 and limit < 100:
                weight = 1
            elif limit >= 100 and limit < 500:
                weight = 2
            elif limit >= 500 and limit < 1000:
                weight = 5
            elif limit >= 1000:
                weight = 10
        elif req_type == 'exchange':
            weight = 1
        elif req_type == 'order book':
            if limit == 50:
                weight = 2
            elif limit == 100:
                weight = 5
            elif limit == 500:
                weight = 10
            elif limit == 1000:
                weight = 20

        DataGetter.__WEIGHT += weight
        await asyncio.sleep(60)
        DataGetter.__WEIGHT -= weight

    async def weight(self):
        """
        Weight getter
        :return: - current weight
        """
        return DataGetter.__WEIGHT

    async def __get_tick_size(self, symbol) -> float:
        """
        Get a tick size by symbol
        :param symbol:  futures pair
        :return:  tick size
        """
        result = '0'
        df = pd.DataFrame(self.__exchange_info['symbols'])
        df = df[~df.symbol.str.contains('_')]
        symbol_info = df[df.symbol.str.contains(symbol)]
        try:
            result = float(symbol_info.filters[symbol_info.index.values[0]][0]['tickSize'])
        except KeyError as e:
            print(f'{symbol} {e}')
            return result
        return result

    async def __get_order_book_limit(self, level_qty) -> int:
        if 0 < level_qty <= 50:
            return 50
        elif 50 < level_qty <= 100:
            return 100
        elif 100 < level_qty <= 500:
            return 500
        elif level_qty > 500:
            return 1000

    async def get_order_book(self, symbol: str,
                             up_board_price=0.0,
                             down_board_price=0.0):
        """
        Get order book by symbol between the level's boards
        :param symbol: futures pair name
        :param up_board_price: up board of the level
        :param down_board_price: down board of the level
        :return: json order book
        """
        level_height = up_board_price - down_board_price
        tick_size = await self.__get_tick_size(symbol)
        levels_qty = level_height // tick_size
        limit = await self.__get_order_book_limit(levels_qty)

        req_limit = 10
        req_counter = 0
        req_type = 'order book'
        loop = asyncio.get_running_loop()

        while req_counter < req_limit:
            if DataGetter.__WEIGHT >= DataGetter.__WEIGHT_LIMIT:
                print(f'Requests weight is more than limit {DataGetter.__WEIGHT}')
                await asyncio.sleep(60)
                continue
            try:
                req = await self.__client.futures_order_book(symbol=symbol, limit=limit)
                print(f'Order book data got by {symbol}')
                loop.call_soon(asyncio.create_task, self.__set_weight(req_type, limit))
                return req
            except TimeoutError as e:
                print(f'{symbol} The error during getting an order book data from the server.')
                await asyncio.sleep(1)
                req_counter += 1
                if req_counter == req_limit:
                    await asyncio.sleep(300)
                    req_counter = 0
                    continue
                continue

    async def get_large_applications(self, symbol: str,
                                     order_type: str,
                                     up_board_price=0.0,
                                     down_board_price=0.0) -> tuple:
        """
        The method is searching large applications in order book
        :param symbol: futures pair
        :param order_type: The side of the glass, asks or bids.
        :param up_board_price: the price of the up board of a level
        :param down_board_price: the price of the down board of a level
        :return: the price levels which have big applications
        """
        while True:
            try:
                book = await self.get_order_book(symbol, up_board_price, down_board_price)
                book_df = pd.DataFrame(book['bids']) if order_type == 'bids' else pd.DataFrame(book['asks'])
                book_df.columns = ['price', 'qty']
                book_df = book_df.astype(float)
                book_df = book_df.loc[book_df.price * book_df.qty > config.min_vol_order]
                book_df = book_df.set_index('price')
                book_dict = book_df.qty.to_dict()
                if len(book_dict) < config.min_orders_qty:
                    return False, {}
                else:
                    return True, book_dict
            except ValueError as e:
                print(f'{symbol} {e}')
                await asyncio.sleep(1)
                continue
