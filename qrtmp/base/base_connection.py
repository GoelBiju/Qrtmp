"""
Base connection for Qrtmp, handles socket interactions.
"""

# TODO: This file is to be inherited or linked by a NetConnection class and the NetStream class
#       should link to the NetStream class.

import time
import sockets
import struct


class BaseConnection:
    """ The base connection class to handle the underlying socket connection to an RTMP server. """

    def __init__(self):
        """

        """
