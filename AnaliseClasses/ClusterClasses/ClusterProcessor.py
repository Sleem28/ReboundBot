
class ClusterProcessor:

    def __init__(self, symbol: str, tf: str):
        self.__name = f'Symbol: {symbol}, TF: {tf}'
        self.__cluster_counter = 1
        self.__cluster_list = []