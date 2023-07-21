import time
from multiprocessing import Queue, Process, Pipe, set_start_method, RawValue, Manager
import logging


from frog import bookwatch, interpolator, core
from frog.state import init



def main():
    order_book_queue = Queue()
    interpolation_queue = Queue(maxsize=3)
    interpolation_queue.put(None)

    book_watch_process = Process(target=bookwatch.main, args=(order_book_queue,))
    interpolator_process = Process(target=interpolator.main, args=(interpolation_queue,))

    book_watch_process.daemon = True
    book_watch_process.start()
    interpolator_process.daemon = True
    interpolator_process.start()

    core.main(
        order_book_queue, interpolation_queue,
    )


if __name__ == '__main__':
    logging.basicConfig(
        format='%(filename)s %(lineno)d\t%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    init()
    main()
