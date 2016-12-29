""" Commands that are available by default to send on NetConnection stream. """

import logging
import struct
import time

from qrtmp.formats import types

log = logging.getLogger(__name__)


# TODO: Simplify this with a class, possibly link with the parameters from NetConnection.
class NetConnectionMessages:

    def __init__(self, rtmp_writer):
        """
        Initialise the NetConnection messages class with the RtmpWriter object.

        :param rtmp_writer: RtmpWriter object to write the preset NetConnection messages with.
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

        set_chunk_size.body = {
            'chunk_size': int(new_chunk_size)
        }

        log.debug('Sending SET_CHUNK_SIZE to server:', set_chunk_size)
        self._rtmp_writer.send_packet(set_chunk_size)

    # User Control Message - default:
    def send_set_buffer_length(self, stream_id, buffer_length):
        """
        Send a SET_BUFFER_LENGTH User Control Message.

        NOTE: This User Control message relies on the packing of two bits of binary data,
              the stream id of the stream joined with the buffer length.

        Example:
            struct.pack('>I', 0) will give us our final packed stream id - in this case \x00\x00\x00\x00 (4-byte),
            struct.pack('>I', buffer_length) will give us our final buffer length (4-byte),
            Joining these together will result in our final 8-byte packed event data (body).

        :param stream_id: int the id of the stream in which we are setting the buffer time for.
        :param buffer_length: int the number of milliseconds that the client will take to buffer over any data
                              coming from the server in the stream. E.g. a 'buffer_length' of 3 would denote
                              3000 ms (milliseconds) of buffer time.
        """
        set_buffer_length = self._rtmp_writer.new_packet()

        packed_stream_id = struct.pack('>I', stream_id)
        packed_buffer_length = struct.pack('>I', buffer_length)

        set_buffer_length.set_type(types.DT_USER_CONTROL)
        set_buffer_length.body = {
            'event_type': types.UC_SET_BUFFER_LENGTH,
            'event_data': packed_stream_id + packed_buffer_length
        }

        log.debug('Sending SET_BUFFER_LENGTH (User Control RTMP message) to server:', set_buffer_length)
        self._rtmp_writer.send_packet(set_buffer_length)

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

        log.debug('Sending PING_REQUEST (User Control RTMP message) to server: ', ping_request)
        self._rtmp_writer.send_packet(ping_request)

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

        log.debug('Sending PING_RESPONSE (User Control RTMP message) to server: ', ping_response)
        self._rtmp_writer.send_packet(ping_response)

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

        log.debug('Sending WINDOW_ACKNOWLEDGEMENT_SIZE to server:', window_ack_size)
        self._rtmp_writer.send_packet(window_ack_size)

    # TODO: Establish a token system for this as well, so we know which onStatus, _result or _error message.
    #       matches to which message sent.
    # TODO: Keep a record of the latest stream id in use and the transaction id.
    def send_create_stream(self, command_object=None):
        """
        Send a 'createStream' request on the RTMP connection channel.

        :param command_object: dict (default None) any command information to be sent.
        """
        create_stream = self._rtmp_writer.new_packet()

        create_stream.set_type(types.DT_COMMAND)
        create_stream.body = {
            'command_name': 'createStream',
            'transaction_id': self._rtmp_writer.transaction_id + 2,
            'command_object': command_object,
            'options': []
        }

        log.debug('Sending createStream to server:', create_stream)
        self._rtmp_writer.send_packet(create_stream)

    def send_close_stream(self, close_stream_id, command_object=None):
        """
        Send a 'closeStream' request on the stream given by the stream id, this will be the same as
        the stream id in which a publish RTMP message was sent on.

        :param command_object: dict (default None) any command information to be sent.
        :param close_stream_id: int the stream id of the stream to close.
        """
        close_stream = self._rtmp_writer.new_packet()

        close_stream.set_type(types.DT_COMMAND)
        close_stream.set_stream_id(close_stream_id)
        close_stream.body = {
            'command_name': 'closeStream',
            'transaction_id': self._rtmp_writer.transaction_id,
            'command_object': command_object,
            'options': []
        }

        log.debug('Sending closeStream request:', close_stream)
        self._rtmp_writer.send_packet(close_stream)
