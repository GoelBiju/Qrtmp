#

import random


def create_random_bytes(length):
    """
    Creates random bytes for the handshake.
    :param length:
    """
    ran_bytes = ''
    i, j = 0, 0xff
    for x in xrange(0, length):
        ran_bytes += chr(random.randint(i, j))
    return ran_bytes
