"""
Qrtmp Library
Version: 0.1.0
"""

import logging
import random
import socket
import struct
import time

import pyamf
import pyamf.util.pure

from qrtmp.consts import packet
from qrtmp.consts.packet_types import types
from qrtmp.io import rtmp_reader
from qrtmp.io import rtmp_writer
from qrtmp.util import socks

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


# class NetStreamPlay(object):
#     """ A class for holding a NetStream play stream information. """

class NetConnection:
    """ An instance to handle all NetConnecton based functionality. """

    def __init__(self):
        """

        """
        pass


class NetStream:
    """ An instance to handle all NetStream based functionality. """

    def __init__(self):
        """

        """
        pass


# TODO: Make sure the main message sending methods only work with a valid connection, otherwise we pause
#       the use of the library until a valid connection is established.
# TODO: RtmpClient should inherit functions from a NetConnection and NetStream class.
#       NetConnection can deal with handling streams at a basic level and NetStream can allow for
#       stream based messages e.g. 'publish' or 'closeStream' to be sent.
class RtmpClient:
    """ Represents an RTMP client. """

    # The class variables for carrying the connection:
    socket = None
    stream = None
    socket_file = None
    reader = None
    writer = None

    # Client defaults:
    valid_connection = False
    handle_default_messages = True

    # Default flash versions for various operating systems:
    windows_flash_version = 'WIN 23,0,0,162'
    mac_flash_version = 'MAC 23,0,0,162'
    linux_flash_version = 'LNX 11,2,202,635'

    # Default publish types:
    publish_live = 'live'
    publish_record = 'record'
    publish_append = 'append'

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
        self.audio_codecs = kwargs.get('audio_codecs', 3575)
        self.video_codecs = kwargs.get('video_codecs', 252)
        self.video_function = kwargs.get('video_function', 1)
        self.object_encoding = kwargs.get('object_encoding', 0)

        #   - custom connection parameters:
        self._custom_connection_parameters = []

        # Socket/data parameters:
        self._proxy = proxy
        self._shared_objects = []

        # RPC - Command message parameters:
        # TODO: Monitor the transaction ids used.
        # NOTE: This indicates the outstanding command to which the response we receive refers;
        #       the transaction id for the remote call procedure we make to the server is the same
        #       transaction id we receive from the server. This value could be adjusted on a packet basis
        #       to provide flexibility when handling many requests or responses. It can also be used to keep
        #       a log of all the messages received on a particular transaction id or wait for the next response
        #       on the transaction id.
        self._transaction_id = 0

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

    def connect(self):
        """ Connect to the server with the given connect parameters. """
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
        self.socket_file = self.socket.makefile()
        self.stream = FileDataTypeMixIn(self.socket_file)

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
        #       receiving NetConnection.Connection. Success with the status or False with the status.
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

    def set_handle_default_messages(self, new_option):
        """

        :param new_option: bool True/False
        """
        self.handle_default_messages = bool(new_option)

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
                                          'app': self._app,
                                          'flashVer': self.flash_ver,
                                          'swfUrl': self._swf_url,
                                          'tcUrl': self._tc_url,
                                          'fpad': self._fpad,
                                          'capabilities': self.capabilities,
                                          'audioCodecs': self.audio_codecs,
                                          'videoCodecs': self.video_codecs,
                                          'videoFunction': self.video_function,
                                          'pageUrl': self._page_url,
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

    # TODO: Not properly decoding headers may result in the loop decoding here until a restart.
    # TODO: Read packet and the actual decoding of the packet should be in two different sections.
    def read_packet(self):
        """
        Abstracts the process of decoding the data and then generating an RtmpPacket using the decoded header and body.
        :return: RtmpPacket (with header and body).
        """
        if not self.stream.at_eof():
            decoded_header, decoded_body = self.reader.decode_stream()
            # print('--> Decoding new header and body...')
            # print(decoded_header, decoded_body)
            # print('--> Generating new RtmpPacket...')
            received_packet = self.reader.generate_packet(decoded_header, decoded_body)

            # Handle default packet messages.
            if self.handle_default_messages:
                handled_status = self.handle_packet(received_packet)
                if handled_status is True:
                    received_packet.handled = True
                # print(received_packet)
            return received_packet
        else:
            # TODO: Is this the right raise error to call?
            raise StopIteration

    # TODO: Should handle packet be automatically called or manually from the loop.
    # Handle the packet by the internal parser:
    # Some typical RTMP messages we may need to handle include that of:
    #   - 'Window Acknowledgement Size'
    #   - 'Set Peer Bandwidth'
    #   - 'Stream Begin'
    #   - 'Set Chunk Size'
    #   - '_result' (NetConnection.Connect.Success)
    def handle_packet(self, received_packet):
        """
        Handle packets based on data type.
        :param received_packet: RtmpPacket object with both the header information and decoded [AMF] body.
        """
        if received_packet.header.data_type == types.DT_USER_CONTROL and received_packet.body['event_type'] == \
                types.UC_STREAM_BEGIN:
            # TODO: There should a 'safe' connection established in the event we get a NetConnection.Connection.Sucess.
            # assert received_packet.body['event_type'] == types.UC_STREAM_BEGIN, received_packet.body
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

    def shared_object_use(self, shared_object):
        """
        Use a shared object and add it to the managed list of shared objects (SOs).
        :param shared_object:
        """
        if shared_object not in self._shared_objects:
            shared_object.use(self.reader, self.writer)
            self._shared_objects.append(shared_object)

    # Set Chunk Size Message - default:
    # TODO: Should we change the RtmpReader and RtmpWriter chunk sizes manually here?
    def send_set_chunk_size(self, new_chunk_size):
        """
        Send a SET_CHUNK_SIZE RTMP message.
        NOTE: We automatically adjust the RtmpWriter's chunk size to accommodate to
              the new chunk size.

        :param new_chunk_size: int the new chunk size to set the RtmpWriter to work with and to
                               tell the server.
        """
        set_chunk_size = self.writer.new_packet()

        set_chunk_size.set_type(types.DT_SET_CHUNK_SIZE)
        set_chunk_size.set_stream_id(types.RTMP_CONNECTION_CHANNEL)
        set_chunk_size.body = {
            'chunk_size': int(new_chunk_size)
        }

        log.debug('Sending SET_CHUNK_SIZE to server:', set_chunk_size)

        self.writer.setup_packet(set_chunk_size)

        # Set the RtmpWriter chunk size to the new chunk size.
        self.writer.chunk_size = new_chunk_size

        log.debug('Set RtmpWriter chunk to size to:', new_chunk_size)

    # User Control Message - default:
    def send_set_buffer_length(self, stream_id, buffer_length):
        """
        Send a SET_BUFFER_LENGTH User Control Message.

        NOTE: This USER_CONTROL_MESSAGE relies on the packing of two bits of binary data,
              the stream id of the stream joined with the buffer length.

        EXAMPLE: struct.pack('>I', 0) will give us our final packed stream id - in this case \x00\x00\x00\x00 (4-byte),
                 struct.pack('>I', buffer_length) will give us our final buffer length (4-byte),
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

        log.debug('Sending PING_REQUEST (USER_CONTROL_MESSAGE) to server: ', ping_request)

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

        log.debug('Sending PING_RESPONSE (USER_CONTROL_MESSAGE) to server: ', ping_response)

        self.writer.setup_packet(ping_response)

    # Standard default messages:
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

    # TODO: Remove stream_id and override_csid slowly.
    # TODO: Monitor the response on the same transaction id and get the transaction id logs of messages?
    # TODO: Handle command object as a list or dictionary.
    # TODO: createStream requests have a transaction id of 1 (1 more than the transaction id of NetConnection);
    #       this most likely refers to the latest used - FMS might not recognise it if we send on 0 as it is for
    #       NetConnection, NetStream is separate? Anything other than 0 could be if a expect a response from the server.
    # TODO: Tokenize these calls so that if we expect a reply, then we know the reply to get.
    # TODO: Establish a token system for this as well, so we know which onStatus, _result or _error message.
    #       matches to which message sent.
    # TODO: StreamId should not also be a parameter for this method as well, should be handled by
    #       the inheriting class.
    # TODO: Allow various forms of parameters to be provided e.g. within parameters maybe a list?
    #       Is this possible?
    # TODO: Fix issue with the parameters going into the transaction id due the transaction id field in function
    #       stated first.
    def call(self, procedure_name, parameters=None, transaction_id=None, command_object=None, amf3=False):
        """
        Runs a remote procedure call (RPC) on the receiving end.
        :param procedure_name: str
        :param parameters: list
        :param transaction_id: int
        :param command_object: list
        :param amf3: bool True/False
        """
        # :param stream_id: int
        if transaction_id is None:
            transaction_id = self._transaction_id

        # TODO: Alter the way in which we send the RPC content so that we can separate the
        #       command name, transaction id, the command object and the optional arguments
        #       (as specified in the specification).
        optional_parameters = []
        if parameters:
            if type(parameters) is list:
                optional_parameters.extend(parameters)
            elif type(parameters) is dict:
                optional_parameters.append(parameters)

        # TODO: Rename 'command'.
        remote_call = self.writer.new_packet()

        # TODO: Option to switch between an AMF0 encoded command or AMF3 encoded command.
        if not amf3:
            remote_call.set_type(types.DT_COMMAND)
        else:
            remote_call.set_type(types.DT_AMF3_COMMAND)

        # remote_call.set_stream_id(stream_id)
        remote_call.set_stream_id(0)

        remote_call.body = {
            'command_name': procedure_name,
            'transaction_id': transaction_id,
            # TODO: Avoid using this type of way of wrapping an object. If it isn't iterable we can just assume.
            # TODO: We are assuming the command object is provided as a whole dictionary.
            'command_object': command_object,
            'options': optional_parameters
        }

        log.debug('Sending Remote Procedure Call: %s with content:', remote_call.body)

        self.writer.setup_packet(remote_call)

    # TODO: Move to NetStream class - these four methods are specifically sent on the RTMP STREAM CHANNEL.
    # TODO: Establish a token system for this as well, so we know which onStatus, _result or _error message.
    #       matches to which message sent.
    # TODO: Keep a record of the latest stream id in use and the transaction id.
    def send_create_stream(self, command_object=None):
        """
        Send a 'createStream' request on the RTMP stream channel.
        :param command_object: dict (default None) if there is any command information to be sent.
        """
        create_stream = self.writer.new_packet()

        create_stream.set_chunk_stream_id(types.RTMP_STREAM_CHANNEL)
        create_stream.set_type(types.DT_COMMAND)
        create_stream.body = {
            'command_name': 'createStream',
            'transaction_id': self._transaction_id + 2,
            'command_object': command_object,
            'options': []
        }

        log.debug('Sending createStream to server:', create_stream)

        self.writer.setup_packet(create_stream)

    def send_receive_audio(self, stream_id, receive):
        """
        Send a 'receiveAudio' request on the RTMP stream channel.

        :param stream_id: int the id on which we would like to send the receive request.
        :param receive: bool True/False if we want to receive audio or not.
        """
        receive_audio = self.writer.new_packet()

        receive_audio.set_chunk_stream_id(types.RTMP_STREAM_CHANNEL)
        receive_audio.set_type(types.DT_COMMAND)
        receive_audio.set_stream_id(stream_id)
        receive_audio.body = {
            'command_name': 'receiveAudio',
            'transaction_id': self._transaction_id,
            'command_object': None,
            'options': [receive]
        }

        log.debug('Sending receiveAudio to the server:', receive_audio)

        self.writer.setup_packet(receive_audio)

    def send_receive_video(self, stream_id, receive):
        """
        Send a 'receiveVideo' request on the RTMP stream channel.

        :param stream_id: int the id on which we would like to send the receive request.
        :param receive: bool True/False if we want to receive video or not.
        """
        receive_video = self.writer.new_packet()

        receive_video.set_chunk_stream_id(types.RTMP_STREAM_CHANNEL)
        receive_video.set_type(types.DT_COMMAND)
        receive_video.set_stream_id(stream_id)
        receive_video.body = {
            'command_name': 'receiveVideo',
            'transaction_id': self._transaction_id,
            'command_object': None,
            'options': [receive]
        }

        log.debug('Sending receiveVideo to the server:', receive_video)

        self.writer.setup_packet(receive_video)

    def send_play(self, stream_id, stream_name, start=-2, duration=-1, reset=False):
        """
        Send a 'play' request on the RTMP stream channel.

        NOTE: When passing the stream name into the function, make sure the appropriate file-type
              precedes the stream name (unless it is an FLV file) and the file extension. E.g. the
              playback of 'sample.m4v' on the server is issued with a stream name of 'mp4:sample.m4v'
              in the 'play' request.

              Like wise:
                    'BigBuckBunny_115k.mov' -> 'mp4:BigBuckBunny_115k.mov'
                    MP3 or ID3 tags do not need the file extension: 'sample.mp3' -> 'mp3:sample'
                    FLV files can be played back without file-type or file extension:
                        'stream_123.flv' -> 'stream_123'

        :param stream_id: int
        :param stream_name: str the stream name of the file you want to request playback for (READ ABOVE)
        :param start: int (default -2)
        :param duration: int (default -1)
        :param reset: bool (default False)
        """
        play_stream = self.writer.new_packet()

        play_stream.set_chunk_stream_id(types.RTMP_STREAM_CHANNEL)
        play_stream.set_type(types.DT_COMMAND)
        play_stream.set_stream_id(stream_id)
        play_stream.body = {
            'command_name': 'play',
            'transaction_id': self._transaction_id,
            'command_object': None,
            # TODO: Support start, duration and reset parameters.
            'options': [stream_name, start]
        }

        # Add the specific duration to play the stream for (if it is not set to play until it finishes).
        if duration is not -1:
            play_stream.body['options'].append(duration)
        # Add the reset option if it is not set to False (and is instead True).
        if reset is not False:
            play_stream.body['options'].append(reset)

        log.debug('Sending play to the server:', play_stream)

        self.writer.setup_packet(play_stream)

    # def send_play2(self):
    #     """
    #     Send a 'play2' request on the RTMP stream channel.
    #
    #     Properties include: len(number) - duration of playback in seconds.
    #                         offset(number) - absolute stream time at which server switches between streams of
    #                                          different bit-rates for Flash Media Server dynamic streaming
    #                         oldStreamName(string) - name of the old stream or the stream to transition from
    #                         start(number) - start time in seconds
    #                         streamName(string) - name of the new stream to transition to or to play
    #                         transition(string) - mode in which the stream name is played or transitioned to.
    #
    #     NOTE: These are all AMF3 encoded values in AS3 object.
    #     """

    def send_seek(self, stream_id, time_point):
        """
        Send a 'seek' request on the RTMP stream channel.

        :param stream_id: int the stream id in which we want to send the seek request.
        :param time_point: float the point in the playlist (in milliseconds) to seek to.
        """
        seek_stream = self.writer.new_packet()

        seek_stream.set_chunk_stream_id(types.RTMP_STREAM_CHANNEL)
        seek_stream.set_type(types.DT_COMMAND)
        seek_stream.set_stream_id(stream_id)
        seek_stream.body = {
            'command_name': 'seek',
            'transaction_id': self._transaction_id,
            'command_object': None,
            'options': [stream_id, time_point]
        }

        log.debug('Sending seek to the server:', seek_stream)

        self.writer.setup_packet(seek_stream)

    def send_pause(self, stream_id, pause_flag, time_point=0.0):
        """
        Send a 'pause' request on the RTMP stream channel.

        :param stream_id: int
        :param pause_flag: bool (True/False) whether the stream should be paused or resumed.
        :param time_point: float the point at which the stream should be paused or resumed.
        """
        pause_stream = self.writer.new_packet()

        pause_stream.set_chunk_stream_id(types.RTMP_STREAM_CHANNEL)
        pause_stream.set_type(types.DT_COMMAND)
        pause_stream.set_stream_id(stream_id)
        pause_stream.body = {
            'command_name': 'pause',
            'transaction_id': self._transaction_id,
            'command_object': None,
            'options': [pause_flag, time_point]
        }

        log.debug('Sending pause to the server:', pause_stream)

        self.writer.setup_packet(pause_stream)

    def send_publish(self, stream_id, publish_name, publish_type):
        """
        Send a 'publish' request on the RTMP stream channel.
        :param stream_id: int
        :param publish_name:
        :param publish_type:
        """
        publish_stream = self.writer.new_packet()

        publish_stream.set_chunk_stream_id(types.RTMP_STREAM_CHANNEL)
        publish_stream.set_type(types.DT_COMMAND)
        publish_stream.set_stream_id(stream_id)
        publish_stream.body = {
            'command_name': 'publish',
            'transaction_id': self._transaction_id,
            'command_object': None,
            'options': [str(publish_name), publish_type]
        }

        log.debug('Sending publish request:', publish_stream)

        self.writer.setup_packet(publish_stream)

    def send_close_stream(self, stream_id):
        """
        Send a 'closeStream' request on the RTMP stream channel.
        :param stream_id: int
        """
        close_stream = self.writer.new_packet()

        close_stream.set_chunk_stream_id(types.RTMP_STREAM_CHANNEL)
        close_stream.set_type(types.DT_COMMAND)
        close_stream.set_stream_id(stream_id)
        close_stream.body = {
            'command_name': 'closeStream',
            'transaction_id': self._transaction_id,
            'command_object': None,
            'options': []
        }

        log.debug('Sending closeStream request:', close_stream)

        self.writer.setup_packet(close_stream)

    def send_delete_stream(self, deletion_stream_id):
        """
        Send a 'deleteStream' request on the RTMP stream channel.
        :param deletion_stream_id: int
        """
        delete_stream = self.writer.new_packet()

        # TODO: Does 'deleteStream' have to be sent on the command stream?
        delete_stream.set_chunk_stream_id(types.RTMP_COMMAND_CHANNEL)
        delete_stream.set_type(types.DT_COMMAND)
        # TODO: Stream id on which chunk stream id 3 - connection channel - is running on.
        #       This should really be sent with a header format of 1 since it is usually sent
        #       whenever you want to delete the stream, which is after messages are already
        #       flowing in the stream.
        delete_stream.set_stream_id(types.RTMP_CONNECTION_CHANNEL)
        delete_stream.body = {
            'command_name': 'deleteStream',
            'transaction_id': self._transaction_id,
            'command_object': None,
            'options': [deletion_stream_id]
        }

        log.debug('Sending deleteStream request:', delete_stream)

        self.writer.setup_packet(delete_stream)

    def disconnect(self):
        """ Closes the socket connection between the client and server. """
        try:
            log.info('Closing/disconnecting socket connection.')
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
    # 'RtmpByteStream',
    'FileDataTypeMixIn'
]
