import time
# import logging
import struct

from qrtmp.base.base_connection import BaseConnection

# TODO: Can we avoid importing types and use it any other way via RtmpWriter (possibly?)
from qrtmp.consts.formats import types
from qrtmp.io.net_connection import messages


# TODO: We should make it clear if we are talking about packets or messages.

class NetConnection(BaseConnection):
    """
    The base of the RTMP connection, NetConnection allows RTMP communication
    between the client and server.

    :inherits: qrtmp.base.base_connection.BaseConnection
    """
    # Setup the basic RTMP parameters required to connect.
    _app = None

    # Setup other RTMP parameters.
    _swf_url = None
    _tc_url = None
    _page_url = None
    _fpad = None

    # Setup the basic RTMP connection message parameters.
    flash_ver = None
    capabilities = None
    audio_codecs = None
    video_codecs = None
    video_function = None
    object_encoding = None

    # Allow for extra RTMP connection message parameters to be used.
    _extra_rtmp_parameters = []

    # Default flash versions for various operating systems:
    windows_flash_version = 'WIN 23,0,0,162'
    mac_flash_version = 'MAC 23,0,0,162'
    linux_flash_version = 'LNX 11,2,202,635'

    # TODO: Find more about shared objects.
    # _shared_objects = []

    # TODO: Should transaction id be in RtmpWriter?
    # Setup a transaction id in order to communicate RTMP messages between
    # the client and server.
    # _transaction_id = None

    # Initialise the NetConnection messages variable.
    messages = None

    # Initialise working states for the functions in this class.
    active_connection = False
    handle_messages = True

    def set_rtmp_server(self, ip_address, connection_port=1935, proxy_address=None):
        """
        This function serves as the first access point to using the application.

        :param ip_address: str
        :param connection_port: int (default 1935)
        :param proxy_address: str (default boolean None)
        """
        self._set_base_parameters(base_ip=ip_address, base_port=connection_port, base_proxy=proxy_address)

    # TODO: Set flashVer and fpad to 'None' otherwise a Null value might cause the server to
    #       reject the connection request.
    def set_rtmp_parameters(self, app, **kwargs):
        """
        Allow the RTMP basic parameters to be set.

        :param app: str the RTMP application on the server.
        :param kwargs: (arguments available):
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
        # This is the application name, this is necessary in order for the client
        # to make use of the RTMP application on the server.
        self._app = app

        # These are the basic parameters which should be provided if they exist.
        self._swf_url = kwargs.get('swf_url', 'None')
        self._tc_url = kwargs.get('tc_url', 'None')
        self._page_url = kwargs.get('page_url', 'None')
        self._fpad = kwargs.get('fpad', 'None')

        # NOTE: These can be freely changed before calling connect().
        self.flash_ver = kwargs.get('flash_ver', 'None')
        self.capabilities = kwargs.get('capabilities', 239.0)
        # TODO: Should the audio and video codecs always be these values or do they change?
        self.audio_codecs = kwargs.get('audio_codecs', 3575.0)
        self.video_codecs = kwargs.get('video_codecs', 252.0)
        self.video_function = kwargs.get('video_function', 1.0)
        self.object_encoding = kwargs.get('object_encoding', 0.0)

        # self._transaction_id = 0

    def set_extra_rtmp_parameters(self, *args):
        """
        Allows extra RTMP parameters to be used when connecting to the RTMP application.

        :param args: (types):
            -

        :return _extra_rtmp_parameters: list all the extra rtmp parameters which are ready to be sent
                                        along in the RTMP connection message.
        """
        for connection_argument in args:
            self._extra_rtmp_parameters.append(connection_argument)

        return self._extra_rtmp_parameters

    def create_connection_message(self):
        """
        Creates the final RTMP "connect" message from the parameters given to the NetConnection class.
        It returns the RtmpPacket message which is ready to be sent by the RtmpWriter when the client desires to.

        NOTES: The RTMP "connect" message usually follows these RTMP header rules:

                - the "format" of the header is 0 (so a full header is sent),
                - the "chunk stream/channel id" is 3 (this is the usually the channel on
                  which NetConnection messages are sent),
                - the "timestamp" is set to 0 as it is the first RTMP message to be sent across to the server,
                - the "body size" is dependent on the contents of the connection message,
                - the "(message) type id" is 20 (0x14 in hexadecimal) which indicates an AMF0 Command message,
                - the "stream id" is set to 0 as zero is the normal stream id for NetConnection messages.

        :return connection_message: RtmpPacket object
        """
        # Initialise an new packet to use from the RtmpWriter to send the RTMP "connect" message.
        connection_message = self.rtmp_writer.new_packet()

        # Set up the connect message's RTMP header.
        #   - initial connection timestamp is set to zero:
        connection_message.set_timestamp(0)
        #   - this is an AMF0 COMMAND message:
        connection_message.set_type(types.DT_COMMAND)
        #   - the connection message is always sent on the NetConnection stream (a stream id 0):
        connection_message.set_stream_id(0)

        # Create the connection message body.
        connection_message.body = {
            'command_name': 'connect',
            'transaction_id': self.rtmp_writer.transaction_id + 1,
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
            ],
            'options': []
        }

        # If the variables inside the extra connection parameters list are dictionaries,
        # we can treat these as RTMP objects, if these are also a list we can treat each item
        # in the list as its own AMF element (which PyAMF can decode by type to find out what they should
        # be in AMF format).
        if len(self._extra_rtmp_parameters) is not 0:
            for parameter in self._extra_rtmp_parameters:
                if type(parameter) is dict:
                    connection_message.body['options'].append(parameter)
                else:
                    connection_message.body['options'].extend(parameter)

        # Return the prepared connection message to which ever function called it.
        return connection_message

    # TODO: The rtmp_base_connect must be called first here.
    def rtmp_connect(self):
        """ Attempt to make an RTMP connection given the parameters and base connected. """
        # Setup the base with the parameters given and proceed to sending the connection message.
        base_connect = self._rtmp_base_connect()

        if base_connect:
            # Get the RTMP "connect" message and send write it into the stream using the RtmpWriter.
            connect_message = self.create_connection_message()

            # Setup the packet and write the message into the RTMP stream.
            self.rtmp_writer.setup_packet(connect_message)

            # Call the NetConnection messages function to be initialised to be used.
            self.initialise_net_connection_messages()

            return True
        else:
            print('The BaseConnection was not successful:', base_connect)

    def initialise_net_connection_messages(self):
        """
        Initialises the NetConnection default messages for use by the client.
        The RtmpWriter class is required in order for the messages to be accessed and used.
        """
        self.messages = messages.NetConnectionMessages(self.rtmp_writer)

    def set_handle_messages(self, new_option):
        """
        Enables/disables the handling of default RTMP messages automatically by providing True/False
        as the new option.

        :param new_option: boolean True/False stating if we should automatically handle default packets/messages.
        """
        try:
            self.handle_messages = bool(new_option)
        except TypeError:
            print('Handle messages can only be True/False.')

    # TODO: We need to say if read_packet returned None, otherwise we have a NoneType received_packet which can cause
    #       issues in other code further.
    def read_packet(self):
        """
        Abstracts the process of decoding the data and then generating an RtmpPacket using the decoded header and body.

        :return received_packet: RtmpPacket object (with the header and body).
        """
        # TODO: Should _rtmp_stream be accessed directly?
        if not self._rtmp_stream.at_eof():
            decoded_header, decoded_body = self.rtmp_reader.decode_rtmp_stream()

            received_packet = self.rtmp_reader.generate_packet(decoded_header, decoded_body)

            if received_packet is not None:
                # Handle default RTMP messages automatically.
                if self.handle_messages:
                    handled_state = self.handle_packet(received_packet)
                    if handled_state is True:
                        received_packet.handled = True

                return received_packet
            else:
                print('No packet was read from the stream.')
        else:
            raise StopIteration

    # TODO: Connect handle_packet with io.net_connection.commands
    def handle_packet(self, received_packet):
        """
        Handles default RTMP packets based on their data-type.

        :param received_packet:
        :return True/False: boolean depending on if the packet was handled correctly.
        """
        if received_packet.header.data_type == types.DT_USER_CONTROL and received_packet.body['event_type'] == \
                types.UC_STREAM_BEGIN:

            # log.debug('Handled STREAM_BEGIN packet: %s' % received_packet.body)
            return True

        elif received_packet.header.data_type == types.DT_WINDOW_ACKNOWLEDGEMENT_SIZE:

            assert received_packet.body['window_acknowledgement_size'] == 2500000, received_packet.body

            self.messages.send_window_ack_size(received_packet.body)
            # log.debug('Handled WINDOW_ACK_SIZE packet with response to server.')
            return True

        elif received_packet.header.data_type == types.DT_SET_PEER_BANDWIDTH:

            assert received_packet.body['window_acknowledgement_size'] == 2500000, received_packet.body
            assert received_packet.body['limit_type'] == 2, received_packet.body

            # log.debug('Handled SET_PEER_BANDWIDTH packet: %s' % received_packet.body)
            return True

        elif received_packet.header.data_type == types.DT_SET_CHUNK_SIZE:

            assert 0 < received_packet.body['chunk_size'] <= 65536, received_packet.body

            print('New chunk size received.')
            new_chunk_size = received_packet.body['chunk_size']

            # Set RtmpReader chunk size to the new chunk size received.
            self.rtmp_reader.chunk_size = new_chunk_size
            # log.debug('Set RtmpReader chunk to size to:', self.rtmp_reader.chunk_size)

            # Set RtmpWriter chunk size to the new chunk size received.
            self.rtmp_writer.chunk_size = new_chunk_size
            # log.debug('Set RtmpWriter chunk to size to:', self.rtmp_writer.chunk_size)

            # log.debug('Handled SET_CHUNK_SIZE packet with new chunk size: %s' % new_chunk_size)
            return True

        elif received_packet.header.data_type == types.DT_USER_CONTROL and received_packet.body['event_type'] == \
                types.UC_PING_REQUEST:

            self.messages.send_ping_response(received_packet.body)
            timestamp_unpacked = struct.unpack('>I', received_packet.body['event_data'])
            timestamp = timestamp_unpacked[0]
            print('Ping request timestamp: ' + str(timestamp))
            # log.debug('Handled PING_REQUEST packet with response to server.')
            return True

        elif received_packet.header.data_type == types.DT_USER_CONTROL and received_packet.body['event_type'] == \
                types.UC_PING_RESPONSE:

            unpacked_tpl = struct.unpack('>I', received_packet.body['event_data'])
            unpacked_response = unpacked_tpl[0]
            print('Ping response timestamp: ' + str(unpacked_response))
            # log.debug('Server sent PING_RESPONSE: %s' % unpacked_response)
            return True

        else:
            return False

    # def shared_object_use(self, shared_object):
    #     """
    #     Use a shared object and add it to the managed list of shared objects (SOs).
    #     :param shared_object:
    #     """
    #     if shared_object not in self._shared_objects:
    #         shared_object.use(self.rtmp_reader, self.rtmp_writer)
    #         self._shared_objects.append(shared_object)

    def disconnect(self):
        """

        """
        try:
            # TODO: We may need to pass socket.SHUT_RDWR for it work.
            self._socket_object.shutdown(self._socket_module.SHUT_RDWR)
            self._socket_object.close()
        except self._socket_module.error as socket_error:
            print('Socket Error: {0}'.format(socket_error))
