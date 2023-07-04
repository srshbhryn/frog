import time
import logging
from multiprocessing import Queue, Process


from frog import bookwatch, interpolator, core
from frog.utils import Store
from frog.state import init


def main():
    order_book_queue = Queue()
    interpolation_store = Store()
    book_watch_process = Process(target=bookwatch.main, args=(order_book_queue,))
    interpolator_process = Process(target=interpolator.main, args=(interpolation_store,))
    book_watch_process.daemon = True
    book_watch_process.start()
    interpolator_process.daemon = True
    interpolator_process.start()
    core.main(
        order_book_queue, interpolation_store
    )

if __name__ == '__main__':
    logging.basicConfig(
        format='%(module)s %(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    init()
    main()
