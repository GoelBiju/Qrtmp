"""
Base connection for Qrtmp, handles socket interactions.
"""

# TODO: This file is to be inherited or linked by a NetConnection class and the NetStream class
#       should link to the NetStream class.

import socket

from qrtmp.util import socks
from qrtmp.base import data_wrapper
from qrtmp.consts.formats import handshake
from qrtmp.util import miscellaneous

from qrtmp.io import rtmp_reader, rtmp_writer


class BaseConnection:
    """ The base connection class to handle the underlying socket connection to an RTMP server. """

    _socket_module = socket

    _socket_object = None
    _socket_file = None

    _rtmp_stream = None

    rtmp_reader = None
    rtmp_writer = None

    def __init__(self):
        """
        Initialise the BaseConnection class with the IP address, PORT and PROXY class variables.
        """
        self._proxy = None

        self._ip = None
        self._port = None

    def _set_base_parameters(self, base_ip, base_port, base_proxy):
        """
        Set the base parameters in order connect to the server, this includes the IP, PORT and proxy.

        :param base_ip: str
        :param base_port: int
        :param base_proxy: str
        """
        self._proxy = base_proxy

        self._ip = base_ip
        self._port = base_port

        # print('Set base parameters:', self._ip, self._port, self._proxy)

    def _rtmp_handshake(self):
        """
        To begin an RTMP connection we must first request a handshake
        between the client and server.
        """
        # Initialise the handshake chunks we will use.
        c1 = handshake.HandshakeChunk()
        s1 = handshake.HandshakeChunk()
        c2 = handshake.HandshakeChunk()
        s2 = handshake.HandshakeChunk()

        # Handle sending the C1 chunk to the server.
        self._rtmp_stream.write_uchar(3)
        c1.first = 0
        c1.second = 0
        c1.payload = miscellaneous.create_random_bytes(1528)
        c1.encode(self._rtmp_stream)
        self._rtmp_stream.flush()

        # Handle reading the S1 chunk we receive from the server.
        self._rtmp_stream.read_uchar()
        s1.decode(self._rtmp_stream)

        # Handle sending the C2 chunk to the server.
        c2.first = s1.first
        c2.second = c2.second
        c2.payload = s1.payload
        c2.encode(self._rtmp_stream)
        self._rtmp_stream.flush()

        # Handle reading the S2 chunk received from the server.
        s2.decode(self._rtmp_stream)

        # print('RTMP Handshake completed.')

    def _rtmp_base_connect(self):
        """

        :return: boolean True/False
        """
        try:
            # If we are using a proxy for the connection, then make sure we setup
            # the socket to work with the proxy IP and port given.
            if self._proxy:
                proxy_address = self._proxy.split(':')[0]
                proxy_port = int(self._proxy.split(':')[1])

                proxy_socket = socks.socksocket()
                proxy_socket.set_proxy(socks.HTTP, addr=proxy_address, port=proxy_port)

                self._socket_object = proxy_socket
            else:
                # TODO: The socket was not initialised with the right variable name.
                self._socket_object = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # TODO: No connect attribute.
            # Connect the socket object to the IP and port provided.
            self._socket_object.connect((self._ip, self._port))

            # TODO: MAJOR - Data in a file or buffer like store (we will have to explore PyAMF)?
            # Make a socket file to store the data which we will receive from the socket.
            self._socket_file = self._socket_object.makefile()
            self._rtmp_stream = data_wrapper.SocketDataTypeMixInFile(self._socket_file)

            # Make an RTMP handshake which initialises RTMP communication between client and server.
            self._rtmp_handshake()

            # TODO: Placing the call to _set_rtmp_io in BaseConnection removes the _rtmp_strema being None.
            # Setup the RtmpReader and RtmpWriter to function firstly.
            self._set_rtmp_io()

            return True
        except Exception as ex:
            print(ex)
            return False

    # TODO: _rtmp_stream is None when setting up the reader and writer.
    def _set_rtmp_io(self):
        """
        Set the RTMP reader and RTMP writer classes to allow for RTMP messages
        from the DataTypeMixInFile to be read and interpreted to produce an RTMP output
        via writing to the socket.

        NOTE: The RTMP stream object must be initialised before these function can be called.
        """
        # print('RtmpStream in BaseConnection', self._rtmp_stream)
        self.rtmp_reader = rtmp_reader.RtmpReader(self._rtmp_stream)
        self.rtmp_writer = rtmp_writer.RtmpWriter(self._rtmp_stream)
