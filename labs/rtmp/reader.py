"""
Provides classes for creating RTMP (Real Time Message Protocol) for servers and clients.

TODO: Info.
prekageo - https://github.com/prekageo/rtmp-python/
nortxort - https://github.com/nortxort/pinylib/

RTMP general information: http://www.adobe.com/devnet/rtmp.html
RTMP Specification V1.0: http://wwwimages.adobe.com/content/dam/Adobe/en/devnet/rtmp/pdf/rtmp_specification_1.0.pdf
"""

import logging

import pyamf
import pyamf.amf0
import pyamf.amf3
# import pyamf.util.pure
import types
import packet
# from rtmp import rtmp_protocol_header
import rtmp_protocol_header

log = logging.getLogger(__name__)


class RtmpReader:
    """ This class reads RTMP messages from a stream. """

    # Default read chunk size.
    chunk_size = 128

    def __init__(self, stream):
        """
        Initialize the RTMP reader and set it to read from the specified stream.
        """
        self.stream = stream
        self.previous_header = None

    def __iter__(self):
        return self

    def next_packet(self):
        """ Reads one RTMP message from the stream and returns it in a packet format. """
        if self.stream.at_eof():
            raise StopIteration

        # Read the message into body_stream.
        # The message may span a number of chunks (each one with its own header).
        message_body = []
        msg_body_len = 0
        header = rtmp_protocol_header.decode(self.stream)
        log.debug('next_packet() header %s' % header)

        # if header.data_type == types.DT_NONE:
        if header.data_type == -1:
            header = self.previous_header
        self.previous_header = header

        while True:
            # Read the byte difference.
            read_bytes = min(header.body_length - msg_body_len, self.chunk_size)

            # Compare the message body length with the bytes read.
            message_body.append(self.stream.read(read_bytes))
            msg_body_len += read_bytes
            if msg_body_len >= header.body_length:
                break

            # Decode the next header in the stream.
            next_header = rtmp_protocol_header.decode(self.stream)

            # TODO: Evaluate the need for this. Is this consistent with all RTMP implementations?
            # WORKAROUND: Even though the RTMP specification states that the extended timestamp
            #             field DOES NOT follow type 3 chunks, it seems that Flash player 10.1.85.3
            #             and Flash Media Server 3.0.2.217 send and expect this field here.
            if header.timestamp >= 0x00ffffff:
                self.stream.read_ulong()

            assert next_header.timestamp == -1, (header, next_header)
            assert next_header.body_length == -1, (header, next_header)
            assert next_header.data_type == -1, (header, next_header)
            assert next_header.stream_id == -1, (header, next_header)

        assert header.body_length == msg_body_len, (header, msg_body_len)
        body_stream = pyamf.util.BufferedByteStream(''.join(message_body))

        # TODO: Include in the ret, distinctly, the header and the body.
        # Decode the message based on the datatype present in the header.
        # Initialise an RTMP packet instance, to store the information we received,
        # by providing the header.
        received_packet = packet.RtmpPacket(header)

        # Given the header message type id (data_type), let us decode the message body appropriately.
        # if received_packet.header.data_type == types.DT_NONE:
        #     log.warning('WARNING: Header with no data type received.')
        #     return self.next_packet()

        if received_packet.header.data_type == types.DT_SET_CHUNK_SIZE:

            received_packet.body = {'chunk_size': body_stream.read_ulong()}

        elif header.data_type == types.DT_USER_CONTROL:

            received_packet.body = {
                'event_type': body_stream.read_ushort(),
                'event_data': body_stream.read()
            }

        elif received_packet.header.data_type == types.DT_ABORT:

            received_packet.body = {'chunk_stream_id': body_stream.read_ulong()}

        elif received_packet.header.data_type == types.DT_ACKNOWLEDGEMENT:

            # TODO: Make sure we can parse this acknowledgment packet.
            #       The header has a format of 3 and typically it arrives on chunk stream id 2.
            #       The body consists of a 'Sequence number' - 7+ (59 bytes) in length.

            received_packet.body = {'sequence_number': body_stream.read_ulong()}

        elif received_packet.header.data_type == types.DT_WINDOW_ACK_SIZE:

            received_packet.body = {'window_ack_size': body_stream.read_ulong()}

        elif received_packet.header.data_type == types.DT_SET_PEER_BANDWIDTH:

            received_packet.body = {
                'window_ack_size': body_stream.read_ulong(),
                'limit_type': body_stream.read_uchar()
            }

        elif received_packet.header.data_type == types.DT_SHARED_OBJECT:

            decoder = pyamf.amf0.Decoder(body_stream)
            obj_name = decoder.readString()
            curr_version = body_stream.read_ulong()
            flags = body_stream.read(8)

            # A shared object message may contain a number of events.
            events = []
            while not body_stream.at_eof():
                so_event = self.read_shared_object_event(body_stream, decoder)
                events.append(so_event)

            received_packet.body = {
                'obj_name': obj_name,
                'curr_version': curr_version,
                'flags': flags,
                'events': events
            }

        elif received_packet.header.data_type == types.DT_AMF3_SHARED_OBJECT:

            decoder = pyamf.amf3.Decoder(body_stream)
            obj_name = decoder.readString()
            curr_version = body_stream.read_ulong()
            flags = body_stream.read(8)

            # A shared object message may contain a number of events.
            events = []
            while not body_stream.at_eof():
                so_event = self.read_shared_object_event(body_stream, decoder)
                events.append(so_event)

            received_packet.body = {
                'obj_name': obj_name,
                'curr_version': curr_version,
                'flags': flags,
                'events': events
            }

        elif received_packet.header.data_type == types.DT_COMMAND:

            decoder = pyamf.amf0.Decoder(body_stream)
            commands = []

            while not body_stream.at_eof():
                commands.append(decoder.readElement())

            received_packet.body = {'command': commands}

        elif received_packet.header.data_type == types.DT_AMF3_COMMAND:

            decoder = pyamf.amf3.Decoder(body_stream)
            commands = []

            while not body_stream.at_eof():
                commands.append(decoder.readElement())

            received_packet.body = {'command': commands}

        elif received_packet.header.data_type == types.DT_DATA_MESSAGE:

            received_packet.body = {'metadata': message_body}

        elif received_packet.header.data_type == types.DT_AUDIO_MESSAGE:

            received_packet.body = {
                'control': body_stream.read_uchar(),
                'audio_data': body_stream.read()
            }

        elif received_packet.header.data_type == types.DT_VIDEO_MESSAGE:

            received_packet.body = {
                'control': body_stream.read_uchar(),
                'video_data': body_stream.read()
            }

        else:
            assert False, received_packet.header

        log.debug('Received RtmpPacket() %r', received_packet)

        # print('Header received: %s' % repr(received_packet))
        return received_packet

    @staticmethod
    def read_shared_object_event(body_stream, decoder):
        """
        Helper method that reads one shared object event found inside a shared
        object RTMP message.
        :param body_stream:
        :param decoder:
        """
        so_body_type = body_stream.read_uchar()
        so_body_size = body_stream.read_ulong()

        event = {'type': so_body_type}
        if event['type'] == types.SO_USE:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        elif event['type'] == types.SO_RELEASE:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        elif event['type'] == types.SO_CHANGE:
            start_pos = body_stream.tell()
            changes = {}
            while body_stream.tell() < start_pos + so_body_size:
                attrib_name = decoder.readString()
                attrib_value = decoder.readElement()
                assert attrib_name not in changes, (attrib_name, changes.keys())
                changes[attrib_name] = attrib_value
            assert body_stream.tell() == start_pos + so_body_size,\
                (body_stream.tell(), start_pos, so_body_size)
            event['data'] = changes

        elif event['type'] == types.SO_SEND_MESSAGE:
            start_pos = body_stream.tell()
            msg_params = []
            while body_stream.tell() < start_pos + so_body_size:
                msg_params.append(decoder.readElement())
            assert body_stream.tell() == start_pos + so_body_size,\
                (body_stream.tell(), start_pos, so_body_size)
            event['data'] = msg_params

        elif event['type'] == types.SO_CLEAR:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        elif event['type'] == types.SO_REMOVE:
            event['data'] = decoder.readString()

        elif event['type'] == types.SO_USE_SUCCESS:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        else:
            assert False, event['type']

        return event
