from MainClasses import MainProcessor
import asyncio


if __name__ == '__main__':
    mp = MainProcessor()
    asyncio.run(mp.run())

