"""
Qrtmp's NetConnection library which handles the main connection to an RTMP server.

Version 0.3.5
"""

import logging
import struct

from qrtmp.base.base_connection import BaseConnection
from qrtmp.formats import types
from qrtmp.io.net_connection import messages

log = logging.getLogger(__name__)

# TODO: If we don't reload the class, the same class variables will be used in new code if we try
#       to initialise it again.


# TODO: We should make it clear if we are talking about packets or messages.
class NetConnection(BaseConnection):
    """
    The base of the RTMP connection, NetConnection allows RTMP communication
    between the client and server.

    :inherits: qrtmp.base.base_connection.BaseConnection
    """

    # TODO: Add another __init__ function here.
    def __init__(self):
        """
        Initialise the NetConnection variables along with the BaseConnection variables.
        """
        BaseConnection.__init__(self)

        # TODO: Will we need these variables?
        # Parameter access variables.
        # self._stored_rtmp_server = False
        # self._stored_rtmp_parameters = False
        # self._stored_extra_rtmp_parameters = False

        # Setup the basic RTMP parameters required to connect.
        self._app = None

        # Setup other RTMP parameters.
        self._swf_url = None
        self._tc_url = None
        self._page_url = None
        self._fpad = None

        # Setup the basic RTMP connection message parameters.
        self.flash_ver = None
        self.capabilities = None
        self.audio_codecs = None
        self.video_codecs = None
        self.video_function = None
        self.object_encoding = None

        # Allow for extra RTMP connection message parameters to be used.
        self._extra_rtmp_parameters = []

        # Default flash versions for various operating systems:
        self.windows_flash_version = 'WIN 24,0,0,186'
        self.mac_flash_version = 'MAC 24,0,0,186'
        self.linux_flash_version = 'LNX 11,2,202,635'

        # TODO: Find more about shared objects.
        # self._shared_objects = []

        # TODO: Should transaction id be in RtmpWriter?
        # Setup a transaction id in order to communicate RTMP messages between
        # the client and server.
        # self._transaction_id = None

        # Initialise the NetConnection messages variable.
        self.messages = None

        # Initialise working states for the functions in this class.
        self._handle_messages = True
        self._handle_messages_return = False

        # Initialise the connections state.
        self.active_connection = False

    # TODO: Make functions to clear all the important variables before connecting.

    # TODO: Prevent setting the rtmp server, parameters, extra parameters if the connection is being used.
    def set_rtmp_server(self, ip_address, connection_port=1935, proxy_address=None):
        """
        This function serves as the first access point to using the application.

        :param ip_address: str
        :param connection_port: int (default 1935)
        :param proxy_address: str (default boolean None)
        """
        if not self.active_connection:
            # If the RTMP server has already been stored, then we can reset this.
            # if self._stored_rtmp_server:
            #     self.reset_rtmp_server()

            self._set_base_parameters(base_ip=ip_address, base_port=connection_port, base_proxy=proxy_address)
            log.info('Set RTMP server parameters: ip address ({0}), connection port ({1}) and proxy address ({2}).'
                     .format(ip_address, connection_port, proxy_address))
            # self._stored_rtmp_server = True
        else:
            log.warning('You cannot modify the RTMP parameters while there is an active connection. Disconnect first.')
            return False

    # def reset_rtmp_server(self):
    #     """
    #     Resets the PROXY, IP and PORT variables.
    #
    #     This function can be called from the outside for a new NetConnection and new server parameters.
    #     """
    #     self._proxy = None
    #
    #     self._ip = None
    #     self._port = None
    #
    #     # Reset the RTMP server stored variable.
    #     self._stored_rtmp_server = False
    #
    #     log.info('Reset RTMP server parameters.')

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
        if not self.active_connection:
            # Reset the RTMP parameters if they have already been stored.
            # if self._stored_rtmp_parameters:
            #     self.reset_rtmp_parameters()

            # This is the application name, this is necessary in order for the client
            # to make use of the RTMP application on the server.
            self._app = app

            # These are the basic parameters which should be provided if they exist.
            self._swf_url = kwargs.get('swf_url', 'None')
            self._tc_url = kwargs.get('tc_url', 'None')
            self._page_url = kwargs.get('page_url', 'None')
            self._fpad = kwargs.get('fpad', 'None')

            # NOTE: These can be freely changed before calling rtmp_connect().
            self.flash_ver = kwargs.get('flash_ver', 'None')
            self.capabilities = kwargs.get('capabilities', 239.0)
            # TODO: Should the audio and video codecs always be these values or do they change?
            self.audio_codecs = kwargs.get('audio_codecs', 3575.0)
            self.video_codecs = kwargs.get('video_codecs', 252.0)
            self.video_function = kwargs.get('video_function', 1.0)
            self.object_encoding = kwargs.get('object_encoding', 0.0)

            # Set the stored RTMP parameters as we have stored new parameters.
            # self._stored_rtmp_parameters = True
        else:
            log.warning('You cannot modify the RTMP parameters while there is an active connection.')
            return False

    # def reset_rtmp_parameters(self):
    #     """
    #     Resets the RTMP parameters variables.
    #
    #     This function can be called from the outside for a new NetConnection or new RTMP parameters.
    #     """
    #     self._app = None
    #
    #     self._swf_url = None
    #     self._tc_url = None
    #     self._page_url = None
    #     self._fpad = None
    #
    #     self.flash_ver = None
    #     self.capabilities = None
    #     self.audio_codecs = None
    #     self.video_codecs = None
    #     self.video_function = None
    #     self.object_encoding = None
    #
    #     # Reset the stored RTMP parameters variable as the parameters have been reset.
    #     self._stored_rtmp_parameters = False
    #
        log.info('Reset RTMP parameters.')

    # TODO: Work out the logic here, we do not want to delete what is given into the function.
    #       At the moment client's cannot add more extra parameters with another call without deleting what is there.
    # TODO: Issue when calling two NetConnection objects, the extra parameter data of both are used.
    def set_extra_rtmp_parameters(self, *args):
        """
        Allows extra RTMP parameters to be used when connecting to the RTMP application.

        :param args: (types):
            -

        :return _extra_rtmp_parameters: list all the extra rtmp parameters which are ready to be sent
                                        along in the RTMP connection message.
        """
        if not self.active_connection:
            # if len(self._extra_rtmp_parameters) is not 0:
            #     self.reset_extra_rtmp_parameters()

            log.info('Adding extra RTMP parameters.')
            for connection_argument in args:
                self._extra_rtmp_parameters.append(connection_argument)
                log.info('Set extra RTMP parameter: {0}'.format(connection_argument))
            log.info('Finished extra RTMP parameters.')

            # self._stored_extra_rtmp_parameters = True
        else:
            log.warning('You cannot modify the extra RTMP parameters while there is an active connection.')
            return False

    # def reset_extra_rtmp_parameters(self):
    #     """
    #     Resets extra RTMP parameters.
    #
    #     This function can also be called from the outside in the event a new connection should be made with the same
    #     NetConnection object or if you want to store new parameters.
    #     """
    #     self._extra_rtmp_parameters = []
    #
    #     # Resets the stored extra RTMP parameters variable as we have reset any stored parameters.
    #     self._stored_extra_rtmp_parameters = False
    #
    #     log.info('Reset extra RTMP parameters.')

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
        log.info('Creating RTMP "connect" message.')
        # Initialise an new packet to use from the RtmpWriter to send the RTMP "connect" message.
        connection_message = self.rtmp_writer.new_packet()

        # Set up the connect message's RTMP header.
        #   - initial connection timestamp is set to zero:
        connection_message.set_timestamp(0)
        #   - this is an AMF0 COMMAND message:
        connection_message.set_type(types.DT_COMMAND)
        #   - the connection message is always sent on the NetConnection stream (stream id 0):
        connection_message.set_stream_id(0)
        log.info('Generated connection message header: {0}'.format(connection_message.header))

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
        log.info('Generated connection message body: {0}'.format(connection_message.body))

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
            log.info('Added extra RTMP parameters into connection message.')

        # Return the prepared connection message to which ever function called it.
        return connection_message

    # TODO: The rtmp_base_connect must be called first here.
    def rtmp_connect(self):
        """ Attempt to make an RTMP connection given the parameters and base connected. """
        # Setup the base with the parameters given and proceed to sending the connection message.
        base_connect = self._rtmp_base_connect()

        if base_connect:
            log.info('The BaseConnection is connected.')

            # Get the RTMP "connect" packet and send write it into the stream using the RtmpWriter.
            connect_packet = self.create_connection_message()

            # print('sending connect packet')
            # Setup the packet and write the message into the RTMP stream.
            self.rtmp_writer.send_packet(connect_packet)
            log.info('Sent RTMP "connect" message/packet.')
            # print('sent packet')

            # Call the NetConnection messages function to be initialised for use by the client.
            self.initialise_net_connection_messages()

            # TODO: We should only return true to allow the reading of packets once NetConnection.Success has been
            #       received from the server.
            self.active_connection = True
            log.info('RTMP connection is active.')
        else:
            log.error('The BaseConnection (base connect - {0}) was not successful.'.format(base_connect))
            return False

    def initialise_net_connection_messages(self):
        """
        Initialises the NetConnection default messages for use by the client.
        The RtmpWriter class is required in order for the messages to be accessed and used.
        """
        self.messages = messages.NetConnectionMessages(self.rtmp_writer)
        log.info('Initialised NetConnectionMessages.')

    def set_handle_messages(self, new_option):
        """
        Enables/disables the handling of default RTMP messages automatically by providing True/False
        as the new option.

        :param new_option: boolean True/False stating if we should automatically handle default packets/messages.
        """
        try:
            self._handle_messages = bool(new_option)
            log.info('Changed handle messages to: {0}'.format(new_option))
        except TypeError:
            log.error('Handle messages can only be True/False.')
            return None

    def return_handled_message(self, new_option):
        """
        Allows the client to choose if a handled packet should be return anyway by the read_packet() function.

        :param new_option: boolean True/False stating if we should return the handled packet.
        """
        try:
            self._handle_messages_return = bool(new_option)
            log.info('Changed handle messages return to: {0}'.format(new_option))
        except TypeError:
            log.error('Handle messages return can only be True/False.')
            return None

    # TODO: We need to say if read_packet returned None, otherwise we have a NoneType received_packet which can cause
    #       issues in other code further.
    def read_packet(self):
        """
        Abstracts the process of decoding the data and then generating an RtmpPacket using the decoded header and body.

        :return received_packet: RtmpPacket object (with the header and body).
        """
        # TODO: Should _rtmp_stream be accessed directly?
        if not self._rtmp_stream.at_eof():
            # Get the decoded header and body from the RTMP stream.
            decoded_header, decoded_body = self.rtmp_reader.decode_rtmp_stream()
            # Generate an RtmpPacket with the header and body.
            received_packet = self.rtmp_reader.generate_packet(decoded_header, decoded_body)

            if received_packet is not None:
                # Handle default RTMP messages automatically.
                if self._handle_messages:
                    handled_state = self.handle_packet(received_packet)
                    # If the message is handled we can set it's handled attribute.
                    if handled_state is True:
                        received_packet.handled = True
                        # If the client doesn't want to receive the handled packet,
                        # we can read the next packet.
                        if not self._handle_messages_return:
                            return self.read_packet()

                log.info('Received Packet: {0}'.format(received_packet))
                return received_packet
            else:
                log.warning('No packet was read from the stream.')
                print('No packet was read from stream.')
        else:
            raise StopIteration

    # TODO: Raise warning if we receive a SET_CHUNK_SIZE and handle_packet has
    #       not been enabled?
    # TODO: Connect handle_packet with io.net_connection.commands
    def handle_packet(self, received_packet):
        """
        Handles default RTMP packets based on their data-type.

        :param received_packet:
        :return True/False: boolean depending on if the packet was handled correctly.
        """
        log.info('Handling received packet: {0}'.format(received_packet))

        if received_packet.header.data_type == types.DT_USER_CONTROL and received_packet.body['event_type'] == \
                types.UC_STREAM_BEGIN:

            log.info('Handled STREAM_BEGIN packet: %s' % received_packet.body)
            return True

        elif received_packet.header.data_type == types.DT_WINDOW_ACKNOWLEDGEMENT_SIZE:
            assert received_packet.body['window_acknowledgement_size'] == 2500000, received_packet.body

            self.messages.send_window_ack_size(received_packet.body)

            log.info('Handled WINDOW_ACK_SIZE packet with response to server.')
            return True

        elif received_packet.header.data_type == types.DT_SET_PEER_BANDWIDTH:
            assert received_packet.body['window_acknowledgement_size'] == 2500000, received_packet.body
            assert received_packet.body['limit_type'] == 2, received_packet.body

            log.info('Handled SET_PEER_BANDWIDTH packet: %s' % received_packet.body)
            return True

        elif received_packet.header.data_type == types.DT_SET_CHUNK_SIZE:
            assert 0 < received_packet.body['chunk_size'] <= 65536, received_packet.body

            new_chunk_size = received_packet.body['chunk_size']

            # Set RtmpReader chunk size to the new chunk size received.
            self.rtmp_reader.chunk_size = new_chunk_size
            log.debug('Set RtmpReader chunk to size to: {0}'.format(self.rtmp_reader.chunk_size))

            # Set RtmpWriter chunk size to the new chunk size received.
            self.rtmp_writer.chunk_size = new_chunk_size
            log.debug('Set RtmpWriter chunk to size to: {0}'.format(self.rtmp_writer.chunk_size))

            log.info('Handled SET_CHUNK_SIZE packet with new chunk size received.')
            return True

        elif received_packet.header.data_type == types.DT_USER_CONTROL and received_packet.body['event_type'] == \
                types.UC_PING_REQUEST:

            self.messages.send_ping_response(received_packet.body)
            timestamp_unpacked = struct.unpack('>I', received_packet.body['event_data'])
            timestamp = timestamp_unpacked[0]
            log.debug('Received ping request timestamp: %s' % str(timestamp))

            log.info('Handled PING_REQUEST packet with response to server.')
            return True

        # NOTE: Receiving a PING_RESPONSE User Control RTMP message is unlikely, though some servers may respond with
        #       with this if we send a PING_REQUEST User Control RTMP message initially.
        elif received_packet.header.data_type == types.DT_USER_CONTROL and received_packet.body['event_type'] == \
                types.UC_PING_RESPONSE:

            unpacked_tpl = struct.unpack('>I', received_packet.body['event_data'])
            unpacked_response = unpacked_tpl[0]
            log.debug('Received ping response timestamp: %s' % str(unpacked_response))

            log.info('Handled PING_RESPONSE from server.')
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
        Attempts to call a remote procedure call (RPC) on the RTMP server.

        :param procedure_name: str
        :param parameters: list
        :param transaction_id: int
        :param command_object: list
        :param amf3: boolean True/False
        """
        # :param stream_id: int

        # TODO: Rename 'command'.
        remote_call = self.rtmp_writer.new_packet()

        # TODO: Calls should be sent on NetConnection, NetStream messages can be sent specifically via
        #       NetStream messages.
        # remote_call.set_stream_id(stream_id)
        remote_call.set_stream_id(0)

        # TODO: Should the transaction id be customisable here?
        if transaction_id is None:
            transaction_id = self.rtmp_writer.transaction_id

        # TODO: Alter the way in which we send the RPC content so that we can separate the
        #       command name, transaction id, the command object and the optional arguments
        #       (as specified in the specification).
        optional_parameters = []
        if parameters:
            if type(parameters) is list:
                optional_parameters.extend(parameters)
            elif type(parameters) is dict:
                optional_parameters.append(parameters)

        # TODO: Option to switch between an AMF0 encoded command or AMF3 encoded command.
        if not amf3:
            remote_call.set_type(types.DT_COMMAND)
        else:
            remote_call.set_type(types.DT_AMF3_COMMAND)

        remote_call.body = {
            'command_name': procedure_name,
            'transaction_id': transaction_id,
            # TODO: Avoid using this type of way of wrapping an object. If it isn't iterable we can just assume.
            # TODO: We are assuming the command object is provided as a whole dictionary.
            'command_object': command_object,
            'options': optional_parameters
        }

        log.debug('Sending Remote Procedure Call: %s with content:', remote_call.body)
        self.rtmp_writer.send_packet(remote_call)

    # def shared_object_use(self, shared_object):
    #     """
    #     Use a shared object and add it to the managed list of shared objects (SOs).
    #     :param shared_object:
    #     """
    #     if shared_object not in self._shared_objects:
    #         shared_object.use(self.rtmp_reader, self.rtmp_writer)
    #         self._shared_objects.append(shared_object)

    def disconnect(self):
        """ Disconnect from the socket and stops the RTMP connection. """
        log.info('Disconnecting NetConnection.')

        # Stop the active NetConnection.
        self.active_connection = False
        log.info('Active connection is off.')

        # Reset the connection variables.
        # self.reset_rtmp_server()
        # self.reset_rtmp_parameters()
        # self.reset_extra_rtmp_parameters()
        # log.info('Reset NetConnection class variables.')

        try:
            # TODO: We may need to pass socket.SHUT_RDWR for it work.
            self._socket_object.shutdown(self._socket_module.SHUT_RDWR)
            self._socket_object.close()
            log.info('Socket object has been shutdown and closed.')
        except self._socket_module.error as socket_error:
            log.error('Socket Error: {0}'.format(socket_error))
            return False
