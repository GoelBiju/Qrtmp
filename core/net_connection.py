""" The class for an instance of a net connection in Qrtmp. """

import logging
import time
import struct

from core import base_connection
from core.protocol.types import enum_rtmp_packet

log = logging.getLogger(__name__)


class NetConnection(base_connection.BaseConnection):
    """ """

    def __init__(self):
        """ """
        super(NetConnection, self).__init__()

        self._rtmp_header_handler = None

        self._app = None
        self._swf_url = None
        self._tc_url = None
        self._page_url = None
        self._fpad = None
        self.flash_ver = None
        self.capabilities = None
        self.audio_codecs = None
        self.video_codecs = None
        self.video_function = None
        self._amf0_object_encoding = 0
        self._amf3_object_encoding = 3

        self._use_amf3 = None
        self._extra_rtmp_parameters = []
        self.windows_flash_version = 'WIN 26,0,0,151'
        self.mac_flash_version = 'MAC 24,0,0,186'
        self.linux_flash_version = 'LNX 11,2,202,635'

        self.messages = None
        self._handle_messages = None
        self._handle_messages_return = None
        self._active_connection = False

    def active(self):
        """ """
        return self._active_connection

    def set_rtmp_server(self, ip_address, connection_port=1935, proxy_address=None):
        """
        
        :param self:
        :param ip_address:
        :param connection_port:
        :param proxy_address:
        :return:
        """
        if not self._active_connection:
            self._set_base_parameters(base_ip=ip_address, base_port=connection_port, base_proxy=proxy_address)
            print('Set RTMP server parameters: ip address ({0}), connection port ({1}) and proxy address ({2}).'
                  .format(ip_address, connection_port, proxy_address))
        else:
            print('You cannot modify the RTMP parameters while the connection is active. Disconnect it first.')
            return False

    def set_rtmp_parameters(self, app, **kwargs):
        """
        
        :param self:
        :param app:
        :param kwargs:
        :return:
        """
        if not self._active_connection:
            self._app = app
            self._swf_url = kwargs.get('swf_url', 'None')
            self._tc_url = kwargs.get('tc_url', 'None')
            self._page_url = kwargs.get('page_url', 'None')
            self._fpad = kwargs.get('fpad', False)
            self.flash_ver = kwargs.get('flash_ver', 'None')
            self.capabilities = kwargs.get('capabilities', 15)
            self.audio_codecs = kwargs.get('audio_codecs', 4071)
            self.video_codecs = kwargs.get('video_codecs', 252)
            self.video_function = kwargs.get('video_function', 1)
            self._use_amf3 = bool(kwargs.get('use_amf3', False))
        else:
            print('You cannot modify the RTMP parameters while the connection is active.')
            return False

    def set_extra_rtmp_parameters(self, *args):
        """
        
        :param self:
        :param args:
        :return:
        """
        if not self._active_connection:
            print('Adding extra RTMP parameters.')
            for connection_argument in args:
                self._extra_rtmp_parameters.append(connection_argument)
                print('Set extra RTMP parameter: {0}'.format(connection_argument))
            print('Finished setting extra RTMP parameters.')
        else:
            print('You cannot add extra RTMP parameters while a connection is active.')
            return False

    def create_connection_message(self):
        """
        
        :return:
        """
        print('Creating RTMP "connect" message.')
        connection_message = self._rtmp_writer.new_packet()
        connection_message.set_timestamp(0)
        connection_message.set_type(enum_rtmp_packet.DT_COMMAND)
        connection_message.set_stream_id(0)
        print('Generated connection message header: {0}'.format(connection_message.header))

        if self._use_amf3:
            object_encoding = self._amf3_object_encoding
        else:
            object_encoding = self._amf0_object_encoding
        if self._proxy is not None:
            proxy_in_use = True
        else:
            proxy_in_use = False

        connection_message.body = {
            'command_name': 'connect',
            'transaction_id': self._rtmp_writer.transaction_id + 1,
            'command_object': [
                {'app': self._app,
                 'flashVer': self.flash_ver,
                 'swfUrl': self._swf_url,
                 'tcUrl': self._tc_url,
                 'fpad': proxy_in_use,
                 'capabilities': self.capabilities,
                 'audioCodecs': self.audio_codecs,
                 'videoCodecs': self.video_codecs,
                 'videoFunction': self.video_function,
                 'pageUrl': self._page_url,
                 'objectEncoding': object_encoding}
            ],
            'options': []
        }
        print('Generated connection message body: {0}'.format(connection_message.body))

        if len(self._extra_rtmp_parameters) is not 0:
            print('Adding extra RTMP parameters to RTMP connection message.')
            for parameter in self._extra_rtmp_parameters:
                if type(parameter) is dict:
                    connection_message.body['options'].append(parameter)
                else:
                    connection_message.body['options'].extend(parameter)

            print('Added extra RTMP parameters into connection message.')
        return connection_message

    def rtmp_connect(self):
        """ """
        base_connect = self._rtmp_base_connect()

        if base_connect:
            print('The BaseConnection is connected.')

            connect_packet = self.create_connection_message()
            self._rtmp_writer.setup_packet(connect_packet)
            print('Sent RTMP "connect" message/packet.')

            self._initialise_net_connection_messages()
            print('Initialised the NetConnection default messages.')

            # Start the decoding process in the rtmp reader.
            # self._rtmp_reader.start_decode()

            self._active_connection = True
            print('RTMP connection is active.')
        else:
            print('The BaseConnection (base connect - {0}) was not successful.'.format(base_connect))
            return False

    def _initialise_net_connection_messages(self):
        """ """
        self.messages = NetConnectionMessages(self._rtmp_writer)

    def set_handle_messages(self, new_option):
        """
        
        :param new_option:
        :return:
        """
        try:
            self._handle_messages = bool(new_option)
            print('Changed handle messages to: {0}'.format(new_option))
        except TypeError:
            print('Handle messages can only be True/False.')

    def return_handled_message(self, new_option):
        """
        
        :param new_option:
        :return:
        """
        try:
            self._handle_messages_return = bool(new_option)
            print('Changed handle messages return to: {0}'.format(new_option))
        except TypeError:
            print 'Handle messages return can only be True/False.'

    def read_message(self):
        """
        
        :return:
        """
        # TODO: at_eof should be checked when decoding body and header in the reader,
        #       here we need to check if the queue is empty or not.
        if not self._rtmp_stream.at_eof():
            if self._rtmp_reader.message_queue_empty():
                # TODO: Shall we have a loop for continuously decoding the rtmp stream or
                #       have the read message only read and wait. With a queue an internal loop.
                packet_header, packet_body = self._rtmp_reader.decode_rtmp_stream()
                # TODO: Get the next message from the front of the packet queue.
                received_message = self._rtmp_reader.generate_message(packet_header, packet_body)

                if received_message is not None:
                    if self._handle_messages:
                        handled_state = self.handle_message(received_message)

                        if handled_state is True:
                            received_message.handled = True
                            if not self._handle_messages_return:
                                return self.read_message()

                    # print('Received message: {0}').format(received_message)
                    return received_message
                print('No message was read from the stream.')
            else:
                return self._rtmp_reader.queued_packet()
        else:
            raise StopIteration

    def handle_message(self, received_message):
        """
        
        :param received_message:
        :return:
        """
        print('Handling received message: {0}').format(received_message)

        if received_message.header.data_type == enum_rtmp_packet.DT_USER_CONTROL and received_message.body['event_type'] == enum_rtmp_packet.UC_STREAM_BEGIN:
            print 'Handled STREAM_BEGIN message: %s' % received_message.body
            return True
        if received_message.header.data_type == enum_rtmp_packet.DT_WINDOW_ACKNOWLEDGEMENT_SIZE:
            print 'Handled WINDOW_ACK_SIZE message: %s' % received_message.body['window_acknowledgement_size']
            return True
        if received_message.header.data_type == enum_rtmp_packet.DT_SET_PEER_BANDWIDTH:
            assert received_message.body['window_acknowledgement_size'] == 2500000, received_message.body
            assert received_message.body['limit_type'] == 2, received_message.body
            client_ack_size = received_message.body['window_acknowledgement_size']
            self.messages.send_window_ack_size(client_ack_size)
            print 'Handled SET_PEER_BANDWIDTH message with response to server - ACK size %s' % client_ack_size
            return True
        if received_message.header.data_type == enum_rtmp_packet.DT_USER_CONTROL and received_message.body['event_type'] == enum_rtmp_packet.UC_PING_REQUEST:
            self.messages.send_ping_response(received_message.body)
            timestamp_unpacked = struct.unpack('>I', received_message.body['event_data'])
            timestamp = timestamp_unpacked[0]
            print 'Received PING REQUEST timestamp: %s' % str(timestamp)
            print 'Handled PING REQUEST message with a response to the server.'
            return True

        if received_message.header.data_type == enum_rtmp_packet.DT_SET_CHUNK_SIZE:
            new_chunk_size = int(received_message.body['chunk_size'])
            self._rtmp_reader.chunk_size = new_chunk_size

            print('Received SET CHUNK SIZE: %s' % new_chunk_size)
            print('Handled SET CHUNK SIZE message by setting RTMP Reader to the new chunk size.')
            return True

        return False

    def call(self, procedure_name, parameters=None, command_object=None, response_expected=True):
        """
        
        :param procedure_name:
        :param parameters:
        :param command_object:
        :param response_expected: If a response if expected a transaction id of 0 is sent.
        :return:
        """
        remote_call = self._rtmp_writer.new_packet()
        remote_call.set_stream_id(0)
        if response_expected:
            transaction_id = self._rtmp_writer.transaction_id
        else:
            transaction_id = 0
        optional_parameters = []
        if parameters:
            if type(parameters) is list:
                optional_parameters.extend(parameters)
            elif type(parameters) is dict:
                optional_parameters.append(parameters)
        if self._use_amf3:
            remote_call.set_type(enum_rtmp_packet.DT_AMF3_COMMAND)
        else:
            remote_call.set_type(enum_rtmp_packet.DT_COMMAND)
        remote_call.body = {'command_name': procedure_name, 
           'transaction_id': transaction_id, 
           'command_object': command_object, 
           'options': optional_parameters}
        print (
         'Sending Remote Procedure Call: %s with content:', remote_call.body)
        self._rtmp_writer.setup_packet(remote_call)

    def play(self, stream_name):
        """

        :param stream_name:
        :return:
        """
        play_call = self._rtmp_writer.new_packet()

        play_call.set_stream_id(1)
        play_call.set_type(enum_rtmp_packet.DT_COMMAND)

        play_call.body = {
            'command_name': 'play',
            'transaction_id': self._rtmp_writer.transaction_id,
            'command_object': None,
            'options': [stream_name, -2000]
        }

        print('Sending play message:', play_call.body)
        self._rtmp_writer.setup_packet(play_call)

    def rtmp_disconnect(self):
        """
        
        :return:
        """
        print 'Disconnecting NetConnection.'
        self._active_connection = False
        print 'Active connection is off.'
        self._rtmp_base_disconnect()


class NetConnectionMessages(object):

    def __init__(self, stream_writer):
        """
        
        :param stream_writer:
        """
        self._message_writer = stream_writer

    def send_set_chunk_size(self, new_chunk_size):
        """
        
        :param new_chunk_size:
        :return:
        """
        set_chunk_size = self._message_writer.new_packet()
        set_chunk_size.set_type(enum_rtmp_packet.DT_SET_CHUNK_SIZE)
        set_chunk_size.body = {'chunk_size': int(new_chunk_size)}
        print (
         'Sending SET CHUNK SIZE to RTMP server:', set_chunk_size)
        self._message_writer.setup_packet(set_chunk_size)

    def send_set_buffer_length(self, stream_id, buffer_length):
        """
        
        :param stream_id:
        :param buffer_length:
        :return:
        """
        set_buffer_length = self._message_writer.new_packet()
        packed_stream_id = struct.pack('>I', stream_id)
        packed_buffer_length = struct.pack('>I', buffer_length)
        set_buffer_length.set_type(enum_rtmp_packet.DT_USER_CONTROL)
        set_buffer_length.body = {'event_type': enum_rtmp_packet.UC_SET_BUFFER_LENGTH, 
           'event_data': packed_stream_id + packed_buffer_length}
        print (
         'Sending SET BUFFER LENGTH (User Control RTMP message) to server:', set_buffer_length)
        self._message_writer.setup_packet(set_buffer_length)

    def send_ping_request(self):
        """
        
        :return:
        """
        ping_request = self._message_writer.new_packet()
        ping_request.set_type(enum_rtmp_packet.DT_USER_CONTROL)
        ping_request.body = {'event_type': enum_rtmp_packet.UC_PING_REQUEST, 
           'event_data': struct.pack('>I', int(time.time()))}
        print (
         'Sending PING REQUEST (User Control RTMP message) to server:', ping_request)
        self._message_writer.setup_packet(ping_request)

    def send_ping_response(self, amf_data):
        """
        
        :param amf_data:
        :return:
        """
        ping_response = self._message_writer.new_packet()
        ping_response.set_type(enum_rtmp_packet.DT_USER_CONTROL)
        ping_response.body = {'event_type': enum_rtmp_packet.UC_PING_RESPONSE, 
           'event_data': amf_data['event_data']}
        print (
         'Sending PING RESPONSE (User Control RTMP message) to server:', ping_response)
        self._message_writer.setup_packet(ping_response)

    def send_window_ack_size(self, ack_size):
        """
        
        :param ack_size:
        :return:
        """
        window_ack_size = self._message_writer.new_packet()
        window_ack_size.set_type(enum_rtmp_packet.DT_WINDOW_ACKNOWLEDGEMENT_SIZE)
        window_ack_size.body = {'window_acknowledgement_size': ack_size}
        print (
         'Sending WINDOW_ACKNOWLEDGEMENT_SIZE to server:', window_ack_size)
        self._message_writer.setup_packet(window_ack_size)