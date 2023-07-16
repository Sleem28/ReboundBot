from enums import  ClusterPatternType


class ClusterBar:
    def __init__(self):
        self.__open = 0
        self.__close = 0
        self._high = 0
        self._low = 0
        self.__price_levels = dict()
        self.__digits = -1

    def set_level(self, price: float, side_buy: bool, volume: float):
        """
        Set a level and a volume to the dictionary with levels
        :param price: deal price
        :param side_buy: deal side, buy or sell
        :param volume: deal volume
        """
        self.__close = price

        if self.__open == 0:
            self.__open = price

        if self.__digits == -1:
            self.__digits = self.__set_digits(price)

        if self.__price_levels.keys().__contains__(price):
            if not side_buy:
                self.__price_levels[price]['buy_vol'] = self.__price_levels[price]['buy_vol'] + volume
            else:
                self.__price_levels[price]['sell_vol'] = self.__price_levels[price]['sell_vol'] + volume
        else:
            if not side_buy:
                self.__price_levels[price] = {'buy_vol': volume, 'sell_vol': 0}
            else:
                self.__price_levels[price] = {'buy_vol': 0, 'sell_vol': volume}

    def print_cluster_bar(self, levels_qty=1, print_symbol_qty=2):
        """
        Show the cluster bar
        """
        self.__price_levels = dict(sorted(self.__price_levels.items(), reverse=True))

        str_counter = 0
        total_counter = 1
        bar_len = len(self.__price_levels.keys())
        str_qty = levels_qty if bar_len >= levels_qty else bar_len

        avg_price = 0
        avg_volume = 0
        avg_delta = 0

        poc_price = self.get_poc_and_delta()[0]
        print_poc = False
        print_open = False
        print_close = False
        for price, volumes in self.__price_levels.items():
            if str_counter <= str_qty:
                total_counter += 1
                str_counter += 1
                avg_price += price
                avg_volume += self.__price_levels[price]['buy_vol'] + self.__price_levels[price]['sell_vol']
                avg_delta += self.__price_levels[price]['buy_vol'] + self.__price_levels[price]['sell_vol'] * -1
            if str_counter >= str_qty or total_counter == bar_len:
                #print(f'Price: {round(avg_price/str_counter, self.__digits)}, Volume: {avg_volume}, Delta: {avg_delta}')
                signs_qty = (int(avg_volume//print_symbol_qty)) + 1
                if avg_price <= poc_price and not print_poc:
                    print(f'p{"=" * signs_qty}')
                    print_poc = True
                elif avg_price <= self.__open and not print_open:
                    print(f'0{"-" * signs_qty}')
                    print_open = True
                elif avg_price <= self.__close and not print_close:
                    print(f'c{"-" * signs_qty}')
                    print_close = True
                else:
                    print(f' {"-" * signs_qty}')
                avg_price = 0
                avg_volume = 0
                avg_delta = 0
                str_counter = 0

    def __get_max_volume(self) -> float:
        values = dict(self.__price_levels.values())
        print(values)
        max_vol = max(values['buy_vol'] + values['sell_vol'])
        return max_vol


    def get_ohlc(self) -> tuple:
        """
        Get current ohlc of the cluster bar.
        :return: a tuple with an open, a close, a high and a low of the cluster bar.
        """
        c_open = self.__open
        c_close = self.__close
        c_high = max(list(self.__price_levels.keys()))
        c_low = min(list(self.__price_levels.keys()))

        return c_open, c_high, c_low, c_close,

    def get_poc_and_delta(self) -> tuple:
        """
        Get a tuple with the point of control and the delta of the point of control
        """
        max_vol = 0
        max_price = 0
        delta = 0

        for price, volumes in self.__price_levels.items():
            volume = volumes['buy_vol'] + volumes['sell_vol']
            if volume > max_vol:
                max_vol = volume
                max_price = price
                delta = volumes['buy_vol'] + volumes['sell_vol'] * -1

        return max_price, max_vol, delta,

    def check_pattern(self) -> ClusterPatternType:
        """
        Looks for the pok to be in the top or bottom wick. And the wick was at least half a candle high.
        :return: the type of pattern.
        """
        open, high, low, close = self.get_ohlc()
        poc_price, poc_vol, poc_delta = self.get_poc_and_delta()
        half_price = (high + low) * 0.5
        up_wick_down_price = close if close > open else open
        down_wick_up_price = close if close < open else open

        if poc_price > up_wick_down_price and up_wick_down_price <= half_price and poc_delta > 0:
            return ClusterPatternType.TYPE_SELL
        elif poc_price < down_wick_up_price and down_wick_up_price >= half_price and poc_delta < 0:
            return ClusterPatternType.TYPE_BUY
        else:
            return ClusterPatternType.TYPE_NONE

    def clear_cluster_bar(self):
        self.__price_levels.clear()
        self.__open = 0
        self.__close = 0
        self._high = 0
        self._low = 0

    def __set_digits(self, price: float):
        """
        Calculate a quantity of digits in the price
        :param price: instrument price
        :return: digits
        """
        digits = 0
        while price % 1 != 0:
            digits += 1
            price *= 10
        return digits
