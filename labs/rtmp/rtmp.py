"""

"""

import logging
import socket
import random
import time
import struct

import socks
import pyamf
import pyamf.util.pure

import reader
import writer
import packet
import types

log = logging.getLogger(__name__)

# TODO: Possible speed enhancement when connecting to an RTMP server.


class InvalidFormat(Exception):
    """
    An exception raised in the event of a incorrectly constructed RTMP message or parameters passed in
    to a particular function in an unexpected format.
    """


class RtmpClient:
    """ Represents an RTMP client. """

    valid_connection = False

    def __init__(self, ip, port, app, tc_url, page_url, swf_url, proxy=None):
        """
        Initialise a new RTMP client connection object using the parameters that have been provided.

        :param ip:
        :param port:
        :param app:
        :param tc_url:
        :param page_url:
        :param swf_url:
        :param proxy:
        """
        # The class variables for carrying the connection.
        self.socket = None
        self.stream = None
        self.file = None
        self.reader = None
        self.writer = None

        # Connection socket parameters:
        self._ip = ip
        self._port = port

        # Connection object parameters:
        # - minimum connection parameters:
        self._app = app
        self._flash_ver = 'WIN 22,0,0,209'
        self._swf_url = swf_url
        self._tc_url = tc_url
        self._page_url = page_url
        # - other connection parameters:
        self._fpad = False
        self._capabilities = 239
        self._audio_codecs = 3575
        self._video_codecs = 252
        self._video_function = 1
        self._object_encoding = 0

        # Socket/data parameters:
        self._proxy = proxy
        self._shared_objects = []

    @staticmethod
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

    def connect(self, connect_params):
        """
        Connect to the server with the given connect parameters.
        :param connect_params:
        """
        if self._proxy:
            parts = self._proxy.split(':')
            ip = parts[0]
            port = int(parts[1])

            ps = socks.socksocket()
            ps.set_proxy(socks.HTTP, addr=ip, port=port)
            self.socket = ps
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # socket.SOL_TCP

        # Set socket options:
        #   - turn on TCP keep-alive (generally):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        # TODO: If we avoid using a file-object in the future, we can keep this in. However when using a file-object,
        #       non-blocking or timeout mode cannot be used since operations that cannot be completed immediately fail.
        #   - non-blocking socket:
        # Make the socket non-blocking. In the event that no data is returned in the socket, we can still
        # perform other actions without having to wait for any data. This prevents the connection from "blocking" until
        # an operation is complete.
        # self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        #   - alternative TCP keep-alive method (only for Windows):
        # An alternative method can also be used if you're using the Windows operating system
        # and the client is timing out, the next line can be uncommented to enable this method.
        # self.socket.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 10000, 3000))

        # Initialise basic socket and stream to record the data we receive.
        self.socket.connect((self._ip, self._port))
        self.file = self.socket.makefile()
        self.stream = FileDataTypeMixIn(self.file)

        # Perform the handshake with the server.
        self.handshake()

        # Set the read and write classes to the initialised stream.
        self.reader = reader.RtmpReader(self.stream)
        self.writer = writer.RtmpWriter(self.stream)

        # Start an RTMP connection to the server.
        self.connect_rtmp(connect_params)

        # Set that we have a valid connection after sending the connection packet.
        self.valid_connection = True

    def handshake(self):
        """ Perform the handshake sequence with the server. """
        self.stream.write_uchar(3)
        c1 = packet.HandshakePacket()
        c1.first = 0
        c1.second = 0
        c1.payload = self.create_random_bytes(1528)
        c1.encode(self.stream)
        self.stream.flush()

        self.stream.read_uchar()
        s1 = packet.HandshakePacket()
        s1.decode(self.stream)

        c2 = packet.HandshakePacket()
        c2.first = s1.first
        c2.second = s1.second
        c2.payload = s1.payload
        c2.encode(self.stream)
        self.stream.flush()

        s2 = packet.HandshakePacket()
        s2.decode(self.stream)

    # TODO: Convert to RTMPPacket.
    def connect_rtmp(self, connect_params):
        """
        Initiate an RTMP connection with the Flash Media Server (FMS) by sending an RTMP connection packet,
        with the appropriate header information.

        NOTE: The parameters must always be passed in as a list to allow various data to be present,
              e.g. RTMP objects, RTMP strings/numbers etc.

        :param connect_params: list of the various parameters we want to place into the connection message.
        """
        # The expected header format:
        # Format: 0
        # Channel ID: 3
        # Timestamp: 1
        # Body size = variable
        # Type ID: 20
        # Stream ID: 0

        if type(connect_params) is list:

            # Initialise an RTMPPacket for use.
            connection_packet = packet.RtmpPacket()

            rtmp_connect_msg = {
                # 'data_type': types.DT_COMMAND,

                'command':
                [
                    u'connect',
                    1,
                    {
                        'app': u'' + self._app,
                        'flashVer': u'' + self._flash_ver,
                        'swfUrl': u'' + self._swf_url,
                        'tcUrl': u'' + self._tc_url,
                        'fpad': self._fpad,
                        'capabilities': self._capabilities,
                        'audioCodecs': self._audio_codecs,
                        'videoCodecs': self._video_codecs,
                        'videoFunction': self._video_function,
                        'pageUrl': u'' + self._page_url,
                        'objectEncoding': self._object_encoding
                    }
                ]
            }

            # TODO: Handle multiple connection objects (dicts) or lists of information.
            # If the current connection parameter is a dictionary, we treat this as an
            # RTMP object, if this is a list we can treat each item in the list as its own.
            for parameter in connect_params:
                if type(parameter) is dict:
                    rtmp_connect_msg['command'].append(parameter)
                else:
                    rtmp_connect_msg['command'].extend(parameter)

            # Set up the connection packet's header.
            connection_packet.header.chunk_stream_id = types.RTMP_COMMAND_CHANNEL
            connection_packet.header.timestamp = 1
            connection_packet.header.data_type = types.DT_COMMAND
            connection_packet.header.stream_id = 0

            self.writer.write(rtmp_connect_msg, connection_packet)
            self.writer.flush()

        else:
            raise InvalidFormat('The extra connection parameters received was not in the expected format of a list. '
                                'Received as %s' % type(connect_params))

    def handle_packet(self, received_packet):
        """
        Handle packets based on data type.
        :param received_packet: RtmpPacket object with both the header information and decoded [AMF] body.
        """
        if received_packet.header.data_type == types.DT_USER_CONTROL and received_packet.body['event_type'] == \
                types.UC_STREAM_BEGIN:
            assert received_packet.body['event_type'] == types.UC_STREAM_BEGIN, received_packet.body
            assert received_packet.body['event_data'] == '\x00\x00\x00\x00', received_packet.body
            log.debug('Handled STREAM_BEGIN packet: %s' % received_packet.body)
            return True

        elif received_packet.header.data_type == types.DT_WINDOW_ACK_SIZE:
            # The window acknowledgement may actually vary, rather than one asserted by us,
            # we do not actually handle this specifically (for now).
            assert received_packet.body['window_ack_size'] == 2500000, received_packet.body
            self.send_window_ack_size(received_packet.body)
            log.debug('Handled WINDOW_ACK_SIZE packet with response to server.')
            return True

        elif received_packet.header.data_type == types.DT_SET_PEER_BANDWIDTH:
            assert received_packet.body['window_ack_size'] == 2500000, received_packet.body
            # TODO: Should we consider the other limit types: hard and soft (we can just assume dynamic)?
            assert received_packet.body['limit_type'] == 2, received_packet.body
            log.debug('Handled SET_PEER_BANDWIDTH packet: %s' % received_packet.body)
            return True

        elif received_packet.header.data_type == types.DT_SET_CHUNK_SIZE:
            assert 0 < received_packet.body['chunk_size'] <= 65536, received_packet.body
            self.reader.chunk_size = received_packet.body['chunk_size']
            log.debug('Handled SET_CHUNK_SIZE packet with new chunk size: %s' % self.reader.chunk_size)
            return True

        elif received_packet.header.data_type == types.DT_USER_CONTROL and received_packet.body['event_type'] == \
                types.UC_PING_REQUEST:
            self.send_pong_reply(received_packet.body)
            log.debug('Handled PING_REQUEST packet with response to server.')
            return True

        elif received_packet.header.data_type == types.DT_USER_CONTROL and received_packet.body['event_type'] == \
                types.UC_PONG_REPLY:
            unpacked_tpl = struct.unpack('>I', received_packet.body['event_data'])
            unpacked_response = unpacked_tpl[0]
            log.debug('Server sent PONG_REPLY: %s' % unpacked_response)
            return True

        else:
            return False

    # TODO: Convert to RTMPPacket.
    def call(self, procedure_name, parameters=None, transaction_id=0):
        """
        Runs a remote procedure call (RPC) on the receiving end.
        :param procedure_name: str
        :param parameters: list
        :param transaction_id: int
        """
        call_content = [procedure_name, transaction_id, parameters]
        if parameters:
            if type(parameters) is list:
                call_content.extend(parameters)
            elif type(parameters) is dict:
                call_content.append(parameters)

        remote_call = {
            'data_type': types.DT_COMMAND,
            'command': call_content
        }

        log.debug('Sending Remote Procedure Call: %s with content: %s' % (procedure_name, call_content))
        self.writer.write(remote_call)
        self.writer.flush()

    def shared_object_use(self, shared_object):
        """
        Use a shared object and add it to the managed list of shared objects (SOs).
        :param shared_object:
        """
        if shared_object not in self._shared_objects:
            so.use(self.reader, self.writer)
            self._shared_objects.append(so)

    # TODO: Convert to RTMPPacket.
    def send_window_ack_size(self, amf_data):
        """
        Send a WINDOW_ACK_SIZE message.
        :param amf_data: list the AMF data that was received from the server (including the window ack size).
        """
        ack_msg = {
            'data_type': types.DT_WINDOW_ACK_SIZE,
            'window_ack_size': amf_data['window_ack_size']
        }

        log.debug('Sending WINDOW_ACK_SIZE to server: %s' % ack_msg)
        self.writer.write(ack_msg)
        self.writer.flush()

    # TODO: Convert to RTMPPacket.
    def send_ping_request(self):
        """
        Send a PING request.
        NOTE: It is highly unlikely that the conversation between client and server for this
              message is from the client to the server. In fact we know it should be vice versa,
              though it seems to be that some servers reply to a client sending a PING request.
        """
        ping_request = {
            'data_type': types.DT_USER_CONTROL,
            'event_type': types.UC_PING_REQUEST,
            'event_data': struct.pack('>I', int(time.time()))
        }

        log.debug('Sending PING_REQUEST to server: %s' % ping_request)
        self.writer.write(ping_request)
        self.writer.flush()

    # TODO: Convert to RTMPPacket.
    def send_pong_reply(self, amf_data):
        """
        Send a PING response.
        :param amf_data: list the AMF data that was received from the server (including the event data).
        """
        pong_reply = {
            'data_type': types.DT_USER_CONTROL,
            'event_type': types.UC_PONG_REPLY,
            'event_data': amf_data['event_data']
        }

        log.debug('Sending PONG_REPLY to server: %s' % pong_reply)
        self.writer.write(pong_reply)
        self.writer.flush()

    def shutdown(self):
        """ Closes the socket connection. """
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except socket.error as se:
            log.error('socket error %s' % se)


class FileDataTypeMixIn(pyamf.util.pure.DataTypeMixIn):
    """
    Provides a wrapper for a file object that enables reading and writing of raw
    data types for the file.
    """

    def __init__(self, fileobject):
        self.fileobject = fileobject
        pyamf.util.pure.DataTypeMixIn.__init__(self)

    def read(self, length):
        return self.fileobject.read(length)

    def write(self, data):
        self.fileobject.write(data)

    def flush(self):
        self.fileobject.flush()

    @staticmethod
    def at_eof():
        return False


__all__ = [
    'pyamf',
    'RtmpClient',
    'FileDataTypeMixIn'
]
