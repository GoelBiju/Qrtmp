""" Base connection for Qrtmp; handling socket interactions. """

# TODO: This file is to be inherited or linked by a NetConnection class and the NetStream class
#       should link to the NetStream class.

import logging
import socket

from qrtmp.base import data_wrapper
from qrtmp.formats import handshake
from qrtmp.io import rtmp_reader, rtmp_writer
from qrtmp.util import miscellaneous
from qrtmp.util import socks

log = logging.getLogger(__name__)


class BaseConnection:
    """ The base connection class to handle the underlying socket connection to an RTMP server. """

    def __init__(self):
        """
        Initialise the BaseConnection class with the IP address, PORT and PROXY class variables.
        """
        self._socket_module = socket

        self._socket_object = None
        self._socket_file = None

        self._rtmp_stream = None

        self.rtmp_reader = None
        self.rtmp_writer = None

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

        log.info('Set base parameters: %s, %s, %s' % (self._ip, self._port, self._proxy))

    def _rtmp_handshake(self):
        """
        To begin an RTMP connection we must first request a handshake
        between the client and server.
        """
        log.info('Beginning Rtmp Handshake with server.')

        # Initialise the handshake chunks we will use.
        c1 = handshake.HandshakeChunk()
        s1 = handshake.HandshakeChunk()
        c2 = handshake.HandshakeChunk()
        s2 = handshake.HandshakeChunk()
        log.info('Set up C1, S1, C2, S2 handshake chunk (packets).')

        # Handle sending the C1 chunk to the server.
        self._rtmp_stream.write_uchar(3)
        c1.first = 0
        c1.second = 0
        c1.payload = miscellaneous.create_random_bytes(1528)
        c1.encode(self._rtmp_stream)
        self._rtmp_stream.flush()
        log.info('Written C1 handshake chunk into RTMP stream.')

        # Handle reading the S1 chunk we receive from the server.
        self._rtmp_stream.read_uchar()
        s1.decode(self._rtmp_stream)
        log.info('Read S1 handshake chunk reply from server in RTMP stream.')

        # Handle sending the C2 chunk to the server.
        c2.first = s1.first
        c2.second = c2.second
        c2.payload = s1.payload
        c2.encode(self._rtmp_stream)
        self._rtmp_stream.flush()
        log.info('Written C2 handshake chunk into RTMP stream.')

        # Handle reading the S2 chunk received from the server.
        s2.decode(self._rtmp_stream)
        log.info('Read S2 handshake chunk reply from server in RTMP stream.')

    def _rtmp_base_connect(self):
        """

        :return: boolean True/False
        """
        log.info('Connecting RTMP BaseConnection.')

        try:
            # If we are using a proxy for the connection, then make sure we setup
            # the socket to work with the proxy IP and port given.
            if self._proxy:
                proxy_address = self._proxy.split(':')[0]
                proxy_port = int(self._proxy.split(':')[1])
                log.info('Proxy in use: {0} {1}'.format(proxy_address, proxy_port))

                proxy_socket = socks.socksocket()
                proxy_socket.set_proxy(socks.HTTP, addr=proxy_address, port=proxy_port)

                self._socket_object = proxy_socket
                log.info('Created socket object for proxy socket.')
            else:
                # TODO: The socket was not initialised with the right variable name.
                self._socket_object = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                log.info('Created socket object for SOCK_STREAM.')

            # TODO: No connect attribute.
            # Connect the socket object to the IP and port provided.
            self._socket_object.connect((self._ip, self._port))
            log.info('Connected socket object to IP ({0}) and PORT ({1}).'.format(self._ip, self._port))

            # TODO: MAJOR - Data in a file or buffer like store (we will have to explore PyAMF)?
            # Make a socket file to store the data which we will receive from the socket.
            self._socket_file = self._socket_object.makefile()
            self._rtmp_stream = data_wrapper.SocketDataTypeMixInFile(self._socket_file)
            log.info('Created socket fileobject and RTMP stream SocketDataTypeMixInFile.')

            # Make an RTMP handshake which initialises RTMP communication between client and server.
            self._rtmp_handshake()
            log.info('RTMP Handshake completed.')

            # TODO: Placing the call to _set_rtmp_io in BaseConnection removes the _rtmp_strema being None.
            # Setup the RtmpReader and RtmpWriter to function firstly.
            self._set_rtmp_io()
            log.info('Set up RTMP I/O (RtmpReader and RtmpWriter).')

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
        self.rtmp_reader = rtmp_reader.RtmpReader(self._rtmp_stream)
        self.rtmp_writer = rtmp_writer.RtmpWriter(self._rtmp_stream)
