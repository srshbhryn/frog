
import zmq

from frog import config

def main():

    context = zmq.Context()

    frontend = context.socket(zmq.XPUB)
    frontend.bind(config.HIGHWAY_XPUB_BIND_URI)

    backend = context.socket(zmq.XSUB)
    backend.bind(config.HIGHWAY_XSUB_BIND_URI)

    zmq.proxy(frontend, backend)

    # We never get here…
    frontend.close()
    backend.close()
    context.term()

if __name__ == "__main__":
    main()
