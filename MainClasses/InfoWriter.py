import os


class InfoWriter:

    def write_info(self, symbol: str, info: str):
        path = os.path.join('reports', f'{symbol}.txt')
        with open(path, 'a', encoding='utf-8') as f:
            f.write(info)
