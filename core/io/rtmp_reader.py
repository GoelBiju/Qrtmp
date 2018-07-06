""" """

import logging
import struct
# import threading
import time

import pyamf
import pyamf.amf0
import pyamf.amf3

from core.protocol import rtmp_packet
from core.protocol.types import enum_rtmp_packet
from core.protocol.rtmp_packet_queue import PacketQueue

log = logging.getLogger(__name__)


class RtmpReader(object):
    """ """

    def __init__(self, rtmp_stream, rtmp_header_handler):
        """
        
        :param rtmp_stream:
        :param rtmp_header_handler:
        """
        self._reader_stream = rtmp_stream
        self._reader_header_handler = rtmp_header_handler
        self._previous_header = None
        self._packet_queue = PacketQueue()
        # self.total_time = 0

        self.chunk_size = 128

    def __iter__(self):
        """
        
        :return:
        """
        return self

    def decode_rtmp_stream(self):
        """
        
        :return:
        """
        msg_body_len = 0

        # Decode the latest header from the stream.
        decoded_header = self._reader_header_handler.decode_from_stream()
        decoded_body = pyamf.util.BufferedByteStream()
        # print('Decoded header: %s' % decoded_header)

        # If we get an invalid data type and an invalid body length then we use the previous
        # header, we could raise an error in this case.
        # TODO: Raise an error when decoding the header if this happens and do not assume previous header.
        if (decoded_header.data_type == -1) | (decoded_header.body_length == -1):
            decoded_header = self._previous_header
        self._previous_header = decoded_header

        while True:
            read_bytes = min(decoded_header.body_length - msg_body_len, self.chunk_size)
            decoded_body.append(self._reader_stream.read(read_bytes))
            msg_body_len += read_bytes

            if msg_body_len >= decoded_header.body_length:
                break

            # TODO: If we comment out assertions then we no longer use this.
            # Fetch the next header from the stream.
            # next_header = self._reader_header_handler.decode_from_stream()
            # Get the next header and body to parse.
            self._reader_header_handler.decode_from_stream()
            if decoded_header.timestamp >= 16777215:
                self._reader_stream.read_ulong()

            # TODO: I am not sure if these assertions work in the case when we have
            #       aggregate or audio/video messages.
            # assert next_header.timestamp == -1, (decoded_header, next_header)
            # assert next_header.body_length == -1, (decoded_header, next_header)
            # assert next_header.data_type == -1, (decoded_header, next_header)

            # if not next_header.stream_id == -1:
            #     raise AssertionError((decoded_header, next_header))

        assert decoded_header.body_length == msg_body_len, (decoded_header, msg_body_len)

        return decoded_header, decoded_body
        # self._generate_message(decoded_header, decoded_body)

    @staticmethod
    def read_shared_object_event(body_stream, decoder):
        """
        Helper method that reads one shared object event found inside a shared
        object message.

        :param body_stream:
        :param decoder:
        """
        so_body_type = body_stream.read_uchar()
        so_body_size = body_stream.read_ulong()
        event = {'type': so_body_type}

        if event['type'] == enum_rtmp_packet.SO_USE:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        elif event['type'] == enum_rtmp_packet.SO_RELEASE:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        elif event['type'] == enum_rtmp_packet.SO_CHANGE:
            start_pos = body_stream.tell()
            changes = {}

            while body_stream.tell() < start_pos + so_body_size:
                attrib_name = decoder.readString()
                attrib_value = decoder.readElement()
                assert attrib_name not in changes, (attrib_name, changes.keys())
                changes[attrib_name] = attrib_value

            assert body_stream.tell() == start_pos + so_body_size, (
             body_stream.tell(), start_pos, so_body_size)
            event['data'] = changes

        elif event['type'] == enum_rtmp_packet.SO_SEND_MESSAGE:
            start_pos = body_stream.tell()
            msg_params = []

            while body_stream.tell() < start_pos + so_body_size:
                msg_params.append(decoder.readElement())

            assert body_stream.tell() == start_pos + so_body_size, (
             body_stream.tell(), start_pos, so_body_size)
            event['data'] = msg_params

        elif event['type'] == enum_rtmp_packet.SO_CLEAR:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        elif event['type'] == enum_rtmp_packet.SO_REMOVE:
            event['data'] = decoder.readString()

        elif event['type'] == enum_rtmp_packet.SO_USE_SUCCESS:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        else:
            assert False, event['type']

        return event

    def generate_message(self, decoded_header, decoded_body):
        """
        Given the decoded packet header and body an RTMP Packet
        can be created with this function.
        
        :param decoded_header:
        :param decoded_body:
        :return:
        """
        # Set up a basic packet given our decoded header.
        received_packet = rtmp_packet.RtmpPacket(decoded_header)

        # Set this packet as an inbound packet.
        received_packet.is_inbound = True

        # TODO: Implement aggregate headers.
        if received_packet.header.data_type == enum_rtmp_packet.DT_AGGREGATE_MESSAGE:
            # The chunk stream on which the sub-messages follow (decoded from header).
            chunk_stream_id = received_packet.get_chunk_stream_id()

            # Decoding algorithm from rtmp-lite project.
            aggregate_data = decoded_body.read()

            # base_timestamp = 0
            # set_timestamp = False

            while len(aggregate_data) > 0:
                sub_message_type = ord(aggregate_data[0])

                # Ensure we do not encounter invalid messages.
                if sub_message_type == 0:
                    print('A sub-type of 0 was encountered within aggregate message.')
                    break
                elif sub_message_type == enum_rtmp_packet.DT_AUDIO_MESSAGE or \
                        sub_message_type == enum_rtmp_packet.DT_VIDEO_MESSAGE:
                    print('A/V sub-message, type: %s' % sub_message_type)
                else:
                    print('Unknown sub-message, type: %s' % sub_message_type)

                sub_message_size = struct.unpack('!I', '\x00' + aggregate_data[1:4])[0]
                sub_message_time = struct.unpack('!I', aggregate_data[4:8])[0]
                sub_message_time |= (ord(aggregate_data[7]) << 24)

                # if not set_timestamp:
                #     base_timestamp = sub_message_time
                #     set_timestamp = True

                # TODO: Is the stream id correct here.
                sub_message_stream_id = struct.unpack('<I', aggregate_data[8:12])[0]

                # Generate the message header based on these details.
                sub_packet = rtmp_packet.RtmpPacket()
                sub_packet.header.chunk_stream_id = chunk_stream_id
                sub_packet.header.body_length = sub_message_size
                # print('read aggregate size:', sub_message_size)

                sub_packet.set_type(sub_message_type)
                sub_packet.set_timestamp(sub_message_time)
                sub_packet.set_stream_id(sub_message_stream_id)

                # Read the sub message data by skipping past the header.
                aggregate_data = aggregate_data[11:]
                sub_message_data = aggregate_data[:sub_message_size]
                # Set the packet body data.
                # print('actual data length:', len(sub_message_data))
                sub_packet.body_buffer = sub_message_data

                # Skip past the message data to parse back-pointer.
                aggregate_data = aggregate_data[sub_message_size:]
                back_pointer = struct.unpack('!I', aggregate_data[0:4])[0]
                # TODO: Figure out why it always outputs that back-pointer and sub message size are not equal.
                # Solution - Place + 11 to message size.
                if back_pointer != (sub_message_size + 11):
                    print('Warning: Aggregate sub-message back-pointer=%r != %r' % (back_pointer, sub_message_size))

                # Skip past back-pointer to read next sub-message.
                aggregate_data = aggregate_data[4:]

                # Test parsing the audio/video data information.
                add = self._parse_av_info(sub_message_type, sub_message_data)

                # Push the new sub-packet into the RtmpPacket queue.
                if add is True:
                    # new_timestamp = received_packet.get_timestamp() + sub_message_time - base_timestamp
                    # sub_packet.set_timestamp(new_timestamp)
                    # print('New timestamp set for aggregate:', sub_packet.get_timestamp())

                    # self.total_time += new_timestamp
                    # print('Final timestamp set:', self.total_time)
                    self._packet_queue.push(sub_packet)
                    # print('Added sub-packet to queue.')
        else:
            if received_packet.header.data_type == enum_rtmp_packet.DT_SET_CHUNK_SIZE:
                received_packet.body = {
                    'chunk_size': decoded_body.read_ulong()
                }

            elif received_packet.header.data_type == enum_rtmp_packet.DT_ABORT:
                received_packet.body = {
                    'chunk_stream_id': decoded_body.read_ulong()
                }

            elif received_packet.header.data_type == enum_rtmp_packet.DT_ACKNOWLEDGE_BYTES:
                received_packet.body = {
                    'sequence_number': decoded_body.read_ulong()
                }

            elif received_packet.header.data_type == enum_rtmp_packet.DT_USER_CONTROL:
                received_packet.body = {
                    'event_type': decoded_body.read_ushort(),
                    'event_data': decoded_body.read()
                }

            elif received_packet.header.data_type == enum_rtmp_packet.DT_WINDOW_ACKNOWLEDGEMENT_SIZE:
                received_packet.body = {
                    'window_acknowledgement_size': decoded_body.read_ulong()
                }

            elif received_packet.header.data_type == enum_rtmp_packet.DT_SET_PEER_BANDWIDTH:
                received_packet.body = {
                    'window_acknowledgement_size': decoded_body.read_ulong(),
                    'limit_type': decoded_body.read_uchar()
                }

            elif received_packet.header.data_type == enum_rtmp_packet.DT_AUDIO_MESSAGE:
                # TODO: Read whole data and not control first when putting into file.
                # received_packet.body = {
                #     'control': None,
                #     'audio_data': decoded_body.read()
                # }

                # if len(decoded_body) is not 0:
                #     received_packet.body['control'] = decoded_body.read_uchar()
                #     received_packet.body['audio_data'] = decoded_body.read()

                if received_packet.header.body_length > 0:
                    # received_packet.header.timestamp = 0
                    received_packet.body_buffer = decoded_body.read()
                    add = self._parse_av_info(received_packet.header.data_type, received_packet.body_buffer)

                    if add is not True:
                        return None
                    # else:
                    #     if received_packet.get_timestamp() is not 0:
                    #         self.total_time += received_packet.get_timestamp()
                # else:
                #     received_packet.body_buffer = ''
                else:
                    return None

            elif received_packet.header.data_type == enum_rtmp_packet.DT_VIDEO_MESSAGE:
                # TODO: Read whole data instead of control first and then remaining body.
                # received_packet.body = {
                #     'control': None,
                #     'video_data': decoded_body.read()
                # }

                # if len(decoded_body) is not 0:
                #     received_packet.body['control'] = decoded_body.read_uchar()
                #     received_packet.body['video_data'] = decoded_body.read()

                if received_packet.header.body_length > 0:
                    # received_packet.header.timestamp = 0
                    received_packet.body_buffer = decoded_body.read()
                    add = self._parse_av_info(received_packet.header.data_type, received_packet.body_buffer)

                    if add is not True:
                        return None
                    # else:
                    #     if received_packet.get_timestamp() is not 0:
                    #         self.total_time += received_packet.get_timestamp()
                # else:
                #     received_packet.body_buffer = ''
                else:
                    return None

            elif received_packet.header.data_type == enum_rtmp_packet.DT_AMF3_COMMAND:
                decoder = pyamf.amf3.Decoder(decoded_body)

                received_packet.body = {
                    'command_name': decoder.readElement(),
                    'transaction_id': decoder.readElement(),
                    'response': []
                }

                while not decoded_body.at_eof():
                    received_packet.body['response'].append(decoder.readElement())

                received_packet.body_is_amf = True

            elif received_packet.header.data_type == enum_rtmp_packet.DT_METADATA_MESSAGE:
                decoder = pyamf.amf0.Decoder(decoded_body)

                received_packet.body = {
                    'data_name': decoder.readElement(),
                    'data_content': []
                }

                while not decoded_body.at_eof():
                    received_packet.body['data_content'].append(decoder.readElement())

            elif received_packet.header.data_type == enum_rtmp_packet.DT_COMMAND:
                decoder = pyamf.amf0.Decoder(decoded_body)

                command_message = {
                    'command_name': decoder.readElement(),
                    'transaction_id': decoder.readElement(),
                    'command_object': decoder.readElement(),
                    'response': []
                }

                while not decoded_body.at_eof():
                    command_message['response'].append(decoder.readElement())

                received_packet.body = command_message
                received_packet.body_is_amf = True

            else:
                # assert None, received_packet
                print('Packet was not able to be generated.')
                return None

        # print('Received Packet: %s' % repr(received_packet))
        return received_packet
        # self._packet_queue.push(received_packet)

    def queued_packet(self):
        """
        Returns the packet at the front of the queue.

        :return: RtmpPacket object
        """
        return self._packet_queue.pop()

    def message_queue_empty(self):
        """
        Checks if the current queue is empty or not.

        :return: Boolean
        """
        return self._packet_queue.empty()

    @staticmethod
    def _parse_av_info(message_type, message_data):
        """

        :param message_type:
        :param message_data:
        """
        add = False

        if message_type == enum_rtmp_packet.DT_AUDIO_MESSAGE:
            codec_id = ((ord(message_data[0]) & 0xff) & 0xf0) >> 4
            print('Audio Data - Codec ID: ', codec_id)
            if codec_id == 0x0a:
                print('AAC codec in audio.')
            add = True

        elif message_type == enum_rtmp_packet.DT_VIDEO_MESSAGE:
            first_byte = ord(message_data[0]) & 0xff
            codec_id = first_byte & 0x0F
            print('Video Data - Codec ID: ', codec_id)

            # If codec used in video data is AVC..
            if codec_id == 0x07:
                print('AVC codec in video.')
                second_byte = ord(message_data[1]) & 0xff
                config = (second_byte == 0)
                end_of_sequence = (second_byte == 2)
                print('Config & end of sequence: ', config, end_of_sequence)

            # Find the frame-type used in the video data.
            frame_type = (first_byte & 0xf0) >> 4
            if frame_type == 0x01:
                print('Keyframe received in video data.')
                add = True
            elif frame_type == 0x02:
                print('Inter frame received in video data.')
                add = True
            elif frame_type == 0x03:
                print('Disposable frame received in video data.')
            elif frame_type == 0x05:
                print('Video Info frame received in video data.')
            else:
                print('Unknown video frame type received: %s' % frame_type)

        return add
