""" Commands that are available by default to send on NetConnection stream. """

import time
import struct

from qrtmp.consts.formats import types


# TODO: Simplify this with a class, possibly link with the parameters from NetConnection.
class NetConnectionMessages:

    def __init__(self, rtmp_writer):
        """

        :param rtmp_writer: RtmpWriter object
        """
        self._rtmp_writer = rtmp_writer

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
        set_chunk_size = self._rtmp_writer.new_packet()

        set_chunk_size.set_type(types.DT_SET_CHUNK_SIZE)
        set_chunk_size.set_stream_id(types.RTMP_CONNECTION_CHANNEL)
        set_chunk_size.body = {
            'chunk_size': int(new_chunk_size)
        }

        # log.debug('Sending SET_CHUNK_SIZE to server:', set_chunk_size)
        self._rtmp_writer.setup_packet(set_chunk_size)

    # User Control Message - default:
    def send_set_buffer_length(self, stream_id, buffer_length):
        """
        Send a SET_BUFFER_LENGTH User Control Message.

        NOTE: This USER_CONTROL_MESSAGE relies on the packing of two bits of binary data,
              the stream id of the stream joined with the buffer length.

        Example:
            struct.pack('>I', 0) will give us our final packed stream id - in this case \x00\x00\x00\x00 (4-byte),
            struct.pack('>I', buffer_length) will give us our final buffer length (4-byte),
            Joining these together will result in our final 8-byte packed event data (body).

        ;param new_packet:
        :param stream_id: int the id of the stream in which we are setting the buffer time for.
        :param buffer_length: int the number of milliseconds that the client will take to buffer over any data
                              coming from the server in the stream. E.g. a 'buffer_length' of 3 would denote
                              3000 ms (milliseconds) of buffer time.
        """
        set_buffer = self._rtmp_writer.new_packet()

        packed_stream_id = struct.pack('>I', stream_id)
        packed_buffer_length = struct.pack('>I', buffer_length)

        set_buffer.set_type(types.DT_USER_CONTROL)
        set_buffer.body = {
            'event_type': types.UC_SET_BUFFER_LENGTH,
            'event_data': packed_stream_id + packed_buffer_length
        }

        # log.debug('Sending SET_BUFFER_LENGTH (USER_CONTROL_MESSAGE) to server:', set_buffer)
        self._rtmp_writer.setup_packet(set_buffer)

    # TODO: Convert to RtmpPacket.
    def send_ping_request(self):
        """
        Send a PING request.

        NOTE: It is highly unlikely that the conversation between client and server for this
              message is from the client to the server. In fact we know it should be vice versa,
              though it seems to be that some servers reply to a client sending a PING request.
        """
        ping_request = self._rtmp_writer.new_packet()

        ping_request.set_type(types.DT_USER_CONTROL)
        ping_request.body = {
            'event_type': types.UC_PING_REQUEST,
            'event_data': struct.pack('>I', int(time.time()))
        }

        # log.debug('Sending PING_REQUEST (USER_CONTROL_MESSAGE) to server: ', ping_request)
        self._rtmp_writer.setup_packet(ping_request)

    # TODO: Convert to RtmpPacket.
    def send_ping_response(self, amf_data):
        """
        Send a PING response.

        :param amf_data: list the AMF data that was received from the server (including the event data).
        """
        ping_response = self._rtmp_writer.new_packet()

        ping_response.set_type(types.DT_USER_CONTROL)
        ping_response.body = {
            'event_type': types.UC_PING_RESPONSE,
            'event_data': amf_data['event_data']
        }

        # log.debug('Sending PING_RESPONSE (USER_CONTROL_MESSAGE) to server: ', ping_response)
        self._rtmp_writer.setup_packet(ping_response)

    # Standard default messages:
    # TODO: Convert to RtmpPacket.
    def send_window_ack_size(self, amf_data):
        """
        Send a WINDOW_ACK_SIZE message.

        :param amf_data: list the AMF data that was received from the server (including the window ack size).
        """
        window_ack_size = self._rtmp_writer.new_packet()

        window_ack_size.set_type(types.DT_WINDOW_ACKNOWLEDGEMENT_SIZE)
        window_ack_size.body = {
            'window_acknowledgement_size': amf_data['window_acknowledgement_size']
        }

        # log.debug('Sending WINDOW_ACKNOWLEDGEMENT_SIZE to server:', ack)
        self._rtmp_writer.setup_packet(window_ack_size)

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
        remote_call = self._rtmp_writer.new_packet()

        # TODO: Calls should be sent on NetConnection, NetStream messages can be sent specifically via
        #       NetStream messages.
        # remote_call.set_stream_id(stream_id)
        remote_call.set_stream_id(0)

        # TODO: Should the transaction id be customisable here?
        if transaction_id is None:
            transaction_id = self._rtmp_writer.transaction_id

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

        # log.debug('Sending Remote Procedure Call: %s with content:', remote_call.body)
        self._rtmp_writer.setup_packet(remote_call)

    # TODO: Move to NetStream class - these four methods are specifically sent on the RTMP STREAM CHANNEL.
    # TODO: Establish a token system for this as well, so we know which onStatus, _result or _error message.
    #       matches to which message sent.
    # TODO: Keep a record of the latest stream id in use and the transaction id.
    def send_create_stream(self, command_object=None):
        """
        Send a 'createStream' request on the RTMP stream channel.

        :param command_object: dict (default None) if there is any command information to be sent.
        """
        create_stream = self._rtmp_writer.new_packet()

        create_stream.set_chunk_stream_id(types.RTMP_STREAM_CHANNEL)
        create_stream.set_type(types.DT_COMMAND)
        create_stream.body = {
            'command_name': 'createStream',
            'transaction_id': self._rtmp_writer.transaction_id + 2,
            'command_object': command_object,
            'options': []
        }

        # log.debug('Sending createStream to server:', create_stream)
        self._rtmp_writer.setup_packet(create_stream)

    def send_close_stream(self, stream_id):
        """
        Send a 'closeStream' request on the RTMP stream channel.

        :param stream_id: int
        """
        close_stream = self._rtmp_writer.new_packet()

        close_stream.set_chunk_stream_id(types.RTMP_STREAM_CHANNEL)
        close_stream.set_type(types.DT_COMMAND)
        close_stream.set_stream_id(stream_id)
        close_stream.body = {
            'command_name': 'closeStream',
            'transaction_id': self._rtmp_writer.transaction_id,
            'command_object': None,
            'options': []
        }

        # log.debug('Sending closeStream request:', close_stream)
        self._rtmp_writer.setup_packet(close_stream)
