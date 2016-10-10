"""
Qrtmp Library
Version: 0.0.3
"""

import logging
import random
import socket
import struct
import time

import pyamf
import pyamf.util.pure

from core import rtmp_reader, rtmp_writer
from core.structures import packet
from util import socks
from util import types

log = logging.getLogger(__name__)

# TODO: Logging with string formatting of RtmpPackets (__repr__) does not work.
# TODO: Speed enhancement when connecting to an RTMP server.
# TODO: Allow us to get the transaction id from the RtmpClient, and then process messages (wait for reply) according to
#       the transaction id.
# TODO: Implement live debugging options - similar to super debug, printing important information on key functions.
# TODO: Remove usage of 'message' dicts, we will be creating RtmpPackets from everywhere, this is more convenient.
# TODO: Allow the use of the status.py module to define the properties object and information object fields
#       returned from the server in a "_result" or "_error" RPC packet.
# TODO: NetConnection/NetStream classes and make RtmpClient inherit those and deal with packets that way.
# TODO: RtmpReader and RtmpWriter RPC command message read/write methods are not similar.


# TODO: Make sure the main message sending methods only work with a valid connection, otherwise we pause
#       the use of the library until a valid connection is established.
# TODO: RtmpClient should inherit functions from a NetConnection and NetStream class.
#       NetConnection can deal with handling streams at a basic level and NetStream can allow for
#       stream based messages e.g. 'publish' or 'closeStream' to be sent.
class RtmpClient:
    """ Represents an RTMP client. """

    # The class variables for carrying the connection.
    socket = None
    stream = None
    file = None
    reader = None
    writer = None

    valid_connection = False

    # Default flash versions for various operating systems:
    windows_flash_version = 'WIN 23,0,0,162'
    mac_flash_version = 'MAC 23,0,0,162'
    linux_flash_version = 'LNX 11,2,202,635'

    # TODO: Ability to setup an option after initialisation - maybe convenience methods for all (otherwise datatype
    #       issue when coercing a NoneType to unicode?
    # TODO: Use kwargs here instead.
    def __init__(self, ip, port=1935, proxy=None, **kwargs):
        """
        Initialise a new RTMP client connection object using the parameters that have been provided.

        :param ip: str the I.P. address to connect to the server with.
        :param port: (default 1935)
        :param proxy: (default None)

        :param **kwargs: arguments available:
                - kwarg app:
                - kwarg swf_url:
                - kwarg tc_url:
                - kwarg page_url:
                - kwarg flash_ver:
                - kwarg fpad:
                - kwarg capabilities:
                - kwarg audio_codecs:
                - kwarg video_codecs:
                - kwarg video_function:
                - kwarg object_encoding:
        """
        # Connection object parameters:
        #   - minimum connection parameters:
        self._ip = ip
        self._port = port

        #   - other connection parameters:
        # NOTE: The following should not be changed once initialised (datatype errors may occur otherwise).
        # TODO: Raise some warnings in the event that the key arguments are their defaults to make the user
        #       aware that they are connecting 'plainly'.
        self._app = kwargs.get('app', u'None')
        self._swf_url = kwargs.get('swf_url', u'None')
        self._tc_url = kwargs.get('tc_url', u'None')
        self._page_url = kwargs.get('page_url', u'None')
        self._fpad = kwargs.get('fpad', u'False')

        # NOTE: These can be freely changed before calling connect().
        self.flash_ver = kwargs.get('flash_ver', u'None')
        self.capabilities = kwargs.get('capabilities', 239)
        self.audio_codecs = kwargs.get('audio_codecs', 3575)  # 3575
        self.video_codecs = kwargs.get('video_codecs', 252)  # 252
        self.video_function = kwargs.get('video_function', 1)  # 1
        self.object_encoding = kwargs.get('object_encoding', 0)

        #   - custom connection parameters:
        self._custom_connection_parameters = []

        # Socket/data parameters:
        self._proxy = proxy
        self._shared_objects = []

        # RPC - Command message parameters:
        # NOTE: This indicates the outstanding command to which the response we receive refers;
        #       the transaction id for the remote call procedure we make to the server is the same
        #       transaction id we receive from the server. This value could be adjusted on a packet basis
        #       to provide flexibility when handling many requests or responses. It can also be used to keep
        #       a log of all the messages received on a particular transaction id or wait for the next response
        #       on the transaction id.
        self._transaction_id = 0

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

    def connect(self):  # connect_params
        """ Connect to the server with the given connect parameters. """
        # :param connect_params:
        if self._proxy:
            parts = self._proxy.split(':')
            ip = parts[0]
            port = int(parts[1])

            ps = socks.socksocket()
            ps.set_proxy(socks.HTTP, addr=ip, port=port)
            self.socket = ps
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Initialise basic socket and stream file-object to record the data we receive.
        self.socket.connect((self._ip, self._port))

        # TODO: Make file object optional and by default read from the socket and use the
        #       buffered byte stream (this inherits the functions from the StringIOProxy & FileDataTypeMixIn).
        self.file = self.socket.makefile()
        self.stream = FileDataTypeMixIn(self.file)

        # Initialise empty buffered byte stream.
        # self.stream = pyamf.util.BufferedByteStream('')

        # TODO: Figure out a way of reading/writing data from the socket and appending that into the stream object.
        # Perform the handshake with the server.
        self.handshake()

        # Set the read and write classes to the initialised stream.
        self.reader = rtmp_reader.RtmpReader(self.stream)
        self.writer = rtmp_writer.RtmpWriter(self.stream)

        # Request an RTMP connection with the server.
        self.rtmp_connect()

        # TODO: We should only be setting this to true after we have received the connection success
        #       message on transaction id 1 (same as the id we sent the connect message on).
        # Set that we have a valid connection after sending the connection packet.
        self.valid_connection = True

        # TODO: Test reading data out manually.
        # while True:
        #     data = self.socket.recv(self.reader.chunk_size)
        #     print(data)

        # TODO: Need a status handler, this should only be true and returned after
        #       receiving NetConnection.Connection.Sucess with the status or False with the status.
        return self.valid_connection

    def set_socket_options(self):
        """
        Setup custom socket options.

        """
        # TODO: Allow for a function to wrap the socket options.
        # Set socket options:
        # TODO: Server sends keep-alive request every 30 seconds, we send one every 25 seconds.
        #       All keep-alive requests, from the client or server, are replied to with a keep-alive ACK.
        #   - turn on TCP keep-alive (generally):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        #   - allow us to re-use this address next time:
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # TODO: Implement all the keep-alive functions.

        # TODO: If we avoid using a file-object in the future, we can keep this in. However when using a file-object,
        #       non-blocking or timeout mode cannot be used since operations that cannot be completed immediately fail.
        #   - non-blocking socket:
        # Make the socket non-blocking. In the event that no data is returned in the socket, we can still
        # perform other actions without having to wait for any data. This prevents the connection from "blocking" until
        # an operation is complete.
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        #   - alternative TCP keep-alive method (only for Windows):
        # An alternative method can also be used if you're using the Windows operating system
        # and the client is timing out, the next line can be uncommented to enable this method.
        self.socket.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 10000, 25000))

    def handshake(self):
        """ Perform the handshake sequence with the server. """
        # Initialise all the handshake packet we will be sending.
        c1 = packet.HandshakePacket()
        s1 = packet.HandshakePacket()
        c2 = packet.HandshakePacket()
        s2 = packet.HandshakePacket()

        # Handle the C1 chunk.
        self.stream.write_uchar(3)
        c1.first = 0
        c1.second = 0
        c1.payload = self.create_random_bytes(1528)
        c1.encode(self.stream)
        self.stream.flush()

        # Handle the S1 chunk.
        self.stream.read_uchar()
        s1.decode(self.stream)

        # Handle the C2 chunk.
        c2.first = s1.first
        c2.second = s1.second
        c2.payload = s1.payload
        c2.encode(self.stream)
        self.stream.flush()

        # Handle the S2 chunk.
        s2.decode(self.stream)

    def custom_connect_params(self, *args):
        """
        Allow the custom connection parameters to be setup and placed into the list
        to be set into the connection packet.

        NOTE: The parameters must always be passed in as a list to allow various data to be present,
              e.g. RTMP objects, RTMP strings/numbers etc.

        :param args: *args the arguments that needs to be placed into the custom connection parameters list
                      to help build the final connection packet.
        """
        for conn_arg in args:
            self._custom_connection_parameters.append(conn_arg)

    # TODO: Convert to RTMPPacket.
    def rtmp_connect(self):
        """
        Initiate an RTMP connection with the Flash Media Server (FMS) by sending an RTMP connection packet,
        with the appropriate header information.
        """
        # The expected header format:
        # Format: 0
        # Channel ID: 3
        # Timestamp: 0
        # Body size ~ variable size depending on connection body
        # Type ID: 20
        # Stream ID: 0

        # Initialise an RTMPPacket for use.
        connection_packet = packet.RtmpPacket()

        # Set up the connection packet's header:
        #   - initial connection timestamp is set to zero:
        connection_packet.header.timestamp = 0
        #   - this is an AMF0 COMMAND message:
        connection_packet.header.data_type = types.DT_COMMAND
        #   - the connection packet is always sent on the NetConnection stream - Stream Id 0:
        connection_packet.header.stream_id = 0

        # TODO: Why are we not using the call function here? RtmpWriter is expecting another format.
        # TODO: The transaction id here as '1' could be set as a class variable which can be set from the
        #       outside as well on RPC commands.
        # TODO: We need to use the command object here, however not anywhere else (should we just merge it?)
        connection_packet.body = {'command_name': u'connect', 'transaction_id': self._transaction_id + 1,
                                  'command_object': [
                                      {
                                          'app': self._app,  # u'' + self.app
                                          'flashVer': self.flash_ver,  # u'' + self.flash_ver
                                          'swfUrl': self._swf_url,  # u'' + self.swf_url
                                          'tcUrl': self._tc_url,  # u'' + self.tc_url
                                          'fpad': self._fpad,
                                          'capabilities': self.capabilities,
                                          'audioCodecs': self.audio_codecs,
                                          'videoCodecs': self.video_codecs,
                                          'videoFunction': self.video_function,
                                          'pageUrl': self._page_url,  # u'' + self.page_url
                                          'objectEncoding': self.object_encoding
                                      }
                                  ], 'options': []}

        # TODO: Handle multiple connection objects (dicts) or lists of information.
        # If the current connection parameter is a dictionary, we treat this as an
        # RTMP object, if this is a list we can treat each item in the list as its own.
        if len(self._custom_connection_parameters) is not 0:
            for parameter in self._custom_connection_parameters:
                if type(parameter) is dict:
                    connection_packet.body['options'].append(parameter)
                else:
                    connection_packet.body['options'].extend(parameter)

        self.writer.setup_packet(connection_packet)

    # TODO: Should handle packet be automatically called or manually from the loop.
    def handle_packet(self, received_packet):
        """
        Handle packets based on data type.
        :param received_packet: RtmpPacket object with both the header information and decoded [AMF] body.
        """
        if received_packet.header.data_type == types.DT_USER_CONTROL and received_packet.body['event_type'] == \
                types.UC_STREAM_BEGIN:
            # TODO: There should a 'safe' connection established in the event we get a NetConnection.Connection.Sucess.
            assert received_packet.body['event_type'] == types.UC_STREAM_BEGIN, received_packet.body
            # TODO: We can assert the fact that there is a 4-byte empty binary data after the event type,
            #       this will not be labelled as 'event_data' in the RTMP body however it is present anyway.
            # TODO: Assertion issue when we receive anything else, e.g. '\x00\x00\x00\x01';
            #       Handle: onStatus(NetStream.Play.Reset), Stream is Recorded (1), Stream Begin (1),
            #               onStatus(NetStream.Play.Start), RtmpSampleAccess(), NetStream.Data.Start, onMetaData().
            #               Buffer Ready - User Control Message 0x20.
            # assert received_packet.body['event_data'] == '\x00\x00\x00\x00', received_packet.body
            log.debug('Handled STREAM_BEGIN packet: %s' % received_packet.body)
            return True

        elif received_packet.header.data_type == types.DT_WINDOW_ACKNOWLEDGEMENT_SIZE:
            # The window acknowledgement may actually vary, rather than one asserted by us,
            # we do not actually handle this specifically (for now).
            assert received_packet.body['window_acknowledgement_size'] == 2500000, received_packet.body
            self.send_window_ack_size(received_packet.body)
            log.debug('Handled WINDOW_ACK_SIZE packet with response to server.')
            return True

        elif received_packet.header.data_type == types.DT_SET_PEER_BANDWIDTH:
            assert received_packet.body['window_acknowledgement_size'] == 2500000, received_packet.body
            # TODO: Should we consider the other limit types: hard and soft (we can just assume dynamic - 2)?
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
            self.send_ping_response(received_packet.body)
            # TODO: Little-endian unpack order.
            timestamp_unpacked = struct.unpack('>I', received_packet.body['event_data'])
            timestamp = timestamp_unpacked[0]
            print('Ping request timestamp: ' + str(timestamp))
            log.debug('Handled PING_REQUEST packet with response to server.')
            return True

        elif received_packet.header.data_type == types.DT_USER_CONTROL and received_packet.body['event_type'] == \
                types.UC_PING_RESPONSE:
            # TODO: Little-endian unpack order.
            unpacked_tpl = struct.unpack('>I', received_packet.body['event_data'])
            unpacked_response = unpacked_tpl[0]
            print('Ping response timestamp: ' + str(unpacked_response))
            log.debug('Server sent PING_RESPONSE: %s' % unpacked_response)
            return True

        else:
            return False

    # TODO: Remove stream_id and override_csid slowly.
    # TODO: Monitor the response on the same transaction id and get the transaction id logs of messages?
    # TODO: Handle command object as a list or dictionary.
    # TODO: createStream requests have a transaction id of 1 (1 more than the transaction id of NetConnection);
    #       this most likely refers to the latest used - FMS might not recognise it if we send on 0 as it is for
    #       NetConnection, NetStream is separate? Anything other than 0 could be if a expect a response from the server.
    # TODO: Tokenize these calls so that if we expect a reply, then we know the reply to get.
    def call(self, procedure_name, parameters=None, transaction_id=None, command_object=None,
             stream_id=0, override_csid=None):
        """
        Runs a remote procedure call (RPC) on the receiving end.
        :param procedure_name: str
        :param parameters: list
        :param transaction_id: int
        :param command_object: list
        :param stream_id: int
        :param override_csid: int
        """
        # TODO: Allow various forms of parameters to be provided e.g. within parameters maybe a list?
        #       Is this possible?

        if transaction_id is None:
            transaction_id = self._transaction_id

        # TODO: Alter the way in which we send the RPC content so that we can separate the command name, transaction id,
        #       the command object and the optional arguments (as specified in the specification).
        optional_parameters = []
        if parameters:
            if type(parameters) is list:
                optional_parameters.extend(parameters)
            elif type(parameters) is dict:
                optional_parameters.append(parameters)

        # TODO: Rename 'command'.
        remote_call = self.writer.new_packet()

        remote_call.set_type(types.DT_COMMAND)
        remote_call.set_stream_id(stream_id)
        remote_call.body = {
            'command_name': procedure_name,
            'transaction_id': transaction_id,
            # TODO: Avoid using this type of way of wrapping an object. If it isn't iterable we can just assume.
            'command_object': None,
            'options': optional_parameters
        }

        log.debug('Sending Remote Procedure Call: %s with content:', remote_call.body)

        print('Command Name: ', procedure_name)
        print('Stream Id of RPC:', remote_call.header.stream_id)
        self.writer.setup_packet(remote_call)

    def shared_object_use(self, shared_object):
        """
        Use a shared object and add it to the managed list of shared objects (SOs).
        :param shared_object:
        """
        if shared_object not in self._shared_objects:
            shared_object.use(self.reader, self.writer)
            self._shared_objects.append(shared_object)

    # Default essential messages:
    # TODO: Convert to RtmpPacket.
    def send_window_ack_size(self, amf_data):
        """
        Send a WINDOW_ACK_SIZE message.
        :param amf_data: list the AMF data that was received from the server (including the window ack size).
        """
        ack = self.writer.new_packet()

        ack.set_type(types.DT_WINDOW_ACKNOWLEDGEMENT_SIZE)
        ack.body = {
            'window_acknowledgement_size': amf_data['window_acknowledgement_size']
        }

        log.debug('Sending WINDOW_ACKNOWLEDGEMENT_SIZE to server:', ack)

        self.writer.setup_packet(ack)

    def send_set_buffer_length(self, stream_id, buffer_length):
        """
        Send a SET_BUFFER_LENGTH User Control Message.

        NOTE: This USER_CONTROL_MESSAGE relies on the packing of two bits of binary data,
              the stream id of the stream joined with the buffer length.

        EXAMPLE: struct.pack('>I', 0) will give us our final packed stream id - in this case \x00\x00\x00\x00(4-byte),
                 struct.pack('>I', buffer_length*1000) will give us our final buffer length (4-byte),
                 Joining these together will result in our final 8-byte packed event data (body).

        :param stream_id: int the id of the stream in which we are setting the buffer time for.
        :param buffer_length: int the number of milliseconds that the client will take to buffer over any data
                              coming from the server in the stream. E.g. a 'buffer_length' of 3 would denote
                              3000 ms (milliseconds) of buffer time.
        """
        set_buffer = self.writer.new_packet()

        packed_stream_id = struct.pack('>I', stream_id)
        packed_buffer_length = struct.pack('>I', buffer_length)

        set_buffer.set_type(types.DT_USER_CONTROL)
        set_buffer.body = {
            'event_type': types.UC_SET_BUFFER_LENGTH,
            'event_data': packed_stream_id + packed_buffer_length
        }

        log.debug('Sending SET_BUFFER_LENGTH (USER_CONTROL_MESSAGE) to server:', set_buffer)

        self.writer.setup_packet(set_buffer)

    # TODO: Convert to RtmpPacket.
    def send_ping_request(self):
        """
        Send a PING request.
        NOTE: It is highly unlikely that the conversation between client and server for this
              message is from the client to the server. In fact we know it should be vice versa,
              though it seems to be that some servers reply to a client sending a PING request.
        """
        ping_request = self.writer.new_packet()

        ping_request.header.data_type = types.DT_USER_CONTROL
        ping_request.body = {
            'event_type': types.UC_PING_REQUEST,
            'event_data': struct.pack('>I', int(time.time()))
        }

        log.debug('Sending PING_REQUEST to server: ', ping_request)

        self.writer.setup_packet(ping_request)

    # TODO: Convert to RtmpPacket.
    def send_ping_response(self, amf_data):
        """
        Send a PING response.
        :param amf_data: list the AMF data that was received from the server (including the event data).
        """
        ping_response = self.writer.new_packet()

        ping_response.header.data_type = types.DT_USER_CONTROL
        ping_response.body = {
            'event_type': types.UC_PING_RESPONSE,
            'event_data': amf_data['event_data']
        }

        log.debug('Sending PING_RESPONSE to server: ', ping_response)

        self.writer.setup_packet(ping_response)

    def shutdown(self):
        """ Closes the socket connection. """
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except socket.error as se:
            log.error('Socket error: %s' % se)


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

# TODO: If the socket is a file object and FileDataTypeMixIn inherited read/write, we can just alter
#       that to read data.
# TODO: Move this to it's own file, we will be retrieving data from this.
# TODO: We will have to enclose all BufferedByteStream actions with a recv/send to make sure
#       the data is present to do these actions.
# class RtmpByteStream(pyamf.util.pure.BufferedByteStream):
#     """
#     This is a wrapper for the buffered-bytestream class within PyAMF, which inherits
#     the functions from the StringIOProxy and the FileDataTypeMixIn file-object.
#
#     We will abstract the process of reading or writing data within the socket in this class.
#     """
#
#     def __init__(self, socket_object, buf_size=128):
#         """
#         To initialise we will need the socket object to be provided
#         :param socket_object:
#         :param buf_size: int (default 128) the buffer size to read/write data in the socket.
#         """
#         self.socket = socket_object
#         self.buf_size = int(buf_size)
#
#     def set_internal_buf_size(self, new_buf_size):
#         """
#         Set the amount of data we want to read from the socket usually.
#         :param new_buf_size:
#         """
#         self.buf_size = new_buf_size
#
#     def read(self, length=-1):
#         """
#         Override the default file-object read function and get the data from socket
#         with respect to our buffer size.
#         """


__all__ = [
    'pyamf',
    'RtmpClient',
    'RtmpByteStream',
    'FileDataTypeMixIn'
]