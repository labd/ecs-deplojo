import logging


handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(
    logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))

logger = logging.getLogger('ecs-deplojo')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
