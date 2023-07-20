import multiprocessing

from frog.tradestore import sotre_main, service_main


if __name__ == '__main__':
    multiprocessing.Process(target=service_main, args=(), daemon=True).start()
    sotre_main()
