""" The base for a creating a NetConnection. """

import logging
import socket
import socks
import random

from core.protocol import rtmp_handshake
from core.protocol import rtmp_header

from core.io import data_mix
from core.io import rtmp_reader
from core.io import rtmp_writer

log = logging.getLogger(__name__)


class BaseConnection(object):
    """ """

    def __init__(self):
        """

        """
        self._socket_module = socket
        self._socket_object = None

        self._ip = None
        self._port = None
        self._proxy = None

        self._socket_file = None
        self._rtmp_stream = None

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

        print('Set base parameters: %s, %s, %s' % (self._ip, self._port, self._proxy))
        log.info('Set base parameters: %s, %s, %s' % (self._ip, self._port, self._proxy))

    def _rtmp_handshake(self):
        """
        To begin an RTMP connection we must first request a handshake
        between the client and server.
        """
        print('Beginning RTMP handshake with server.')
        c1 = rtmp_handshake.HandshakeChunk()
        s1 = rtmp_handshake.HandshakeChunk()
        c2 = rtmp_handshake.HandshakeChunk()
        s2 = rtmp_handshake.HandshakeChunk()

        print('C1, S1, C2, S2 handshake chunks (packets) initialised.')
        self._rtmp_stream.write_uchar(3)
        print('done')
        c1.first = 0
        c1.second = 0
        c1.payload = self._create_random_bytes(1528)
        print('done')
        c1.encode(self._rtmp_stream)
        print('done')
        self._rtmp_stream.flush()
        print('done')

        print('Wrote C1 handshake chunk into RTMP stream.')
        self._rtmp_stream.read_uchar()
        s1.decode(self._rtmp_stream)
        print('Read S1 handshake chunk reply from server in RTMP stream.')

        c2.first = s1.first
        c2.second = c2.second
        c2.payload = s1.payload
        c2.encode(self._rtmp_stream)
        self._rtmp_stream.flush()
        print('Wrote C2 handshake chunk into RTMP stream.')

        s2.decode(self._rtmp_stream)
        print('Read S2 handshake chunk reply from server in RTMP stream.')

    def _rtmp_base_connect(self):
        """

        """
        print('Connecting RTMP BaseConnection.')

        try:
            if self._proxy:
                proxy_address = self._proxy.split(':')[0]
                proxy_port = int(self._proxy.split(':')[1])
                print('Proxy in use: {0} {1}'.format(proxy_address, proxy_port))

                proxy_socket = socks.socksocket()
                proxy_socket.set_proxy(socks.HTTP, addr=proxy_address, port=proxy_port)
                self._socket_object = proxy_socket
                print('Created socket object for proxy socket.')
            else:
                # self._socket_object = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket_object = socket.create_connection((self._ip, self._port))
                # self._socket_object.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                print('Created socket object for communication.')

            # self._socket_object.connect((self._ip, self._port))
            print('Connected socket object to IP ({0}) and PORT ({1}).'.format(self._ip, self._port))

            self._socket_file = self._socket_object.makefile()
            self._rtmp_stream = data_mix.BaseConnectionDataMix(self._socket_file)
            print('Created socket fileobject and RTMP stream (BaseConnectionDataMix object).')

            self._rtmp_handshake()
            print('RTMP Handshake completed.')

            self._rtmp_header_handler = rtmp_header.RtmpHeaderHandler(self._rtmp_stream)
            print('Set up RTMP Header (RtmpHeaderHandler)')

            self._rtmp_reader = rtmp_reader.RtmpReader(self._rtmp_stream, self._rtmp_header_handler)
            self._rtmp_writer = rtmp_writer.RtmpWriter(self._rtmp_stream, self._rtmp_header_handler)
            print('Set up RTMP I/O (RtmpReader and RtmpWriter).')

            return True
        except Exception as err:
            print(err)
            return False

    def _rtmp_base_disconnect(self):
        """ """
        try:
            self._socket_object.shutdown(self._socket_module.SHUT_RDWR)
            self._socket_object.close()
            print('Socket object has been shutdown and closed.')
        except self._socket_module.error as socket_error:
            print('Socket Error: {0}'.format(socket_error))
            return False

    @staticmethod
    def _create_random_bytes(length):
        """
        Creates random bytes for the handshake.
        :param length:
        """
        ran_bytes = ''
        i, j = (0, 255)
        for x in range(0, length):
            ran_bytes += chr(random.randint(i, j))

        return ran_bytes
