import asyncio

from frog.tradecollector import NobitexTradeCollector


def main():
    asyncio.run(NobitexTradeCollector().run())


if __name__ == '__main__':
    main()
