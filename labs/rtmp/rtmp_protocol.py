# -*- coding: utf-8 -*-

"""
Provides classes for creating RTMP (Real Time Message Protocol) for servers and clients.

This is an edited version of the old library developed by prekageo and mixed with edits from nortxort.
prekageo - https://github.com/prekageo/rtmp-python/
nortxort - https://github.com/nortxort/pinylib/

NOTE:
    Some minor modifications by GoelBiju (https://github.com/GoelBiju/)
    RTMP general information: http://www.adobe.com/devnet/rtmp.html
    RTMP Specification V1.0: http://wwwimages.adobe.com/content/dam/Adobe/en/devnet/rtmp/pdf/rtmp_specification_1.0.pdf
"""

import socket

import logging
import random
import time     # Ping
import struct   # Ping

import pyamf.amf0
import pyamf.amf3
import pyamf.util.pure

import rtmp_protocol_header
import types
import socks

# TODO: Tackle continuing the format of the header appropriately depending on he chunk stream & how we set the header
#       type/format via the attributes present or the format read.

# TODO: A fundamental issue when returning streamIds is that we should not be forcefully returning a stream id,
#       instead returning one if it is present in the header. This applies to all fields, return what we receive
#       and not forcefully choose what to show/return.

# TODO: Produce an rtmp packet class when receiving rtmp packets.

log = logging.getLogger(__name__)


# Default channels.
RTMP_STREAM_CHANNEL = 0x08
RTMP_COMMAND_CHANNEL = 0x03
CONTROL_CHANNEL = 0x02

# Default acknowledgement limit types.
HARD = 0
SOFT = 1
DYNAMIC = 2


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


class HandshakePacket(object):
    """
    A handshake packet.

    @ivar first: The first 4 bytes of the packet, represented as an unsigned long.
    @type first: 32bit unsigned int.
    @ivar second: The second 4 bytes of the packet, represented as an unsigned long.
    @type second: 32bit unsigned int.
    @ivar payload: A blob of data which makes up the rest of the packet.
                   This must be C{HANDSHAKE_LENGTH} - 8 bytes in length.
    @type payload: C{str}
    @ivar timestamp: Timestamp that this packet was created (in milliseconds).
    @type timestamp: C{int}
    """
    # Initialise packet content.
    first = None
    second = None
    payload = None
    timestamp = None

    # Handshake body length.
    handshake_length = 1536

    def __init__(self, **kwargs):
        timestamp = kwargs.get('timestamp', None)

        if timestamp is None:
            kwargs['timestamp'] = int(time.time())

        self.__dict__.update(kwargs)

    def encode(self, stream_buffer):
        """
        Encodes this packet to a stream.
        @param stream_buffer:
        """
        # Write the first and second into the stream.
        stream_buffer.write_ulong(self.first or 0)
        stream_buffer.write_ulong(self.second or 0)

        # Write the payload into the stream.
        stream_buffer.write(self.payload)

    def decode(self, stream_buffer):
        """Decodes this packet from a stream.

        """
        # Set up the first and second.
        self.first = stream_buffer.read_ulong()
        self.second = stream_buffer.read_ulong()

        # Set up the payload for the packet.
        self.payload = stream_buffer.read(self.handshake_length - 8)


class RTMPPacket(object):
    """ A class to abstract the RTMP packets (received) which consists of an RTMP header and an RTMP body. """

    # Set up a blank header.
    header = rtmp_protocol_header.Header(-1)
    # Set up a blank body.
    body = None

    def __init__(self, rtmp_header=None, rtmp_body=None):
        """
        Initialise the packet by providing the decoded header and the decoded body.
        NOTE: The packet can be initialised without providing a header or body, however in order to use this packet
              you must eventually place in the RTMP header and body. If you initialise without these two a default
              header with channel_id -1 will be used with no body, you MUST NOT use this for encoding/decoding to
              the RTMP stream.

        :param rtmp_header: L{Header} decoded header from the rtmp stream.
        :param rtmp_body: dict the body of the rtmp packet, with the contents stored in a dictionary.
        """
        if rtmp_header is not None:
            # Handle the packet header.
            self.header.format = rtmp_header.format
            self.header.channel_id = rtmp_header.channel_id

            self.header.timestamp = rtmp_header.timestamp
            self.header.body_size = rtmp_header.body_size
            self.header.data_type = rtmp_header.data_type
            self.header.stream_id = rtmp_header.stream_id
            self.header.extended_timestamp = rtmp_header.extended_timestamp

        if rtmp_body is not None:
            # Handle the packet body.
            self.body = rtmp_body

    def __repr__(self):
        """
        Return a printable representation of the contents of the header of the RTMPPacket.
        NOTE: We do not return a representation in the event that the packet was initialised plainly,
              with no RTMP header.

        :return: printable representation of header attributes.
        """
        if self.header.format is not -1:
            return '<RTMPPacket.header> format=%s channel_id=%s timestamp=%s body_size=%s ' \
                   'data_type=%s stream_id=%s extended_timestamp=%s' % \
                   (self.header.format, self.header.channel_id, self.header.timestamp, self.header.body_size,
                    self.header.data_type, self.header.stream_id, self.header.extended_timestamp)


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

    def next(self):
        """ Read one RTMP message from the stream and return it. """
        if self.stream.at_eof():
            raise StopIteration

        # Read the message into body_stream.
        # The message may span a number of chunks (each one with its own header).
        message_body = []
        msg_body_len = 0
        header = rtmp_protocol_header.header_decode(self.stream)
        log.debug('next() header %s' % header)

        if header.data_type == types.DT_NONE:
            header = self.previous_header
        self.previous_header = header

        while True:
            # Read the byte difference.
            read_bytes = min(header.body_size - msg_body_len, self.chunk_size)

            # Compare the message body length with the bytes read.
            message_body.append(self.stream.read(read_bytes))
            msg_body_len += read_bytes
            if msg_body_len >= header.body_size:
                break

            # Decode the next header in the stream.
            next_header = rtmp_protocol_header.header_decode(self.stream)

            # WORKAROUND: Even though the RTMP specification states that the extended timestamp
            #             field DOES NOT follow type 3 chunks, it seems that Flash player 10.1.85.3
            #             and Flash Media Server 3.0.2.217 send and expect this field here.
            if header.timestamp >= 0x00ffffff:
                self.stream.read_ulong()

            assert next_header.timestamp == -1, (header, next_header)
            assert next_header.body_size == -1, (header, next_header)
            assert next_header.data_type == -1, (header, next_header)
            assert next_header.stream_id == -1, (header, next_header)

        assert header.body_size == msg_body_len, (header, msg_body_len)
        body_stream = pyamf.util.BufferedByteStream(''.join(message_body))

        # TODO: Include in the ret, distinctly, the header and the body.
        # Decode the message based on the datatype present in the header.
        # ret = {'type': header.data_type}

        # Initialise an RTMP packet instance, to store the information we received, by providing the header.
        received_packet = RTMPPacket(header)

        # Given the header message type id (data_type), let us decode the message body appropriately.
        if received_packet.header.data_type == types.DT_NONE:
            log.warning('WARNING: Header with no data type received.')
            return self.next()

        elif received_packet.header.data_type == types.DT_SET_CHUNK_SIZE:

            # ret['chunk_size'] = body_stream.read_ulong()

            received_packet.body = {'chunk_size': body_stream.read_ulong()}

        elif header.data_type == types.DT_USER_CONTROL:

            # ret['stream_id'] = header.stream_id
            # ret['event_type'] = body_stream.read_ushort()
            # ret['event_data'] = body_stream.read()

            received_packet.body = {
                'event_type': body_stream.read_ushort(),
                'event_data': body_stream.read()
            }

        elif received_packet.header.data_type == types.DT_ABORT:

            received_packet.body = {'chunk_stream_id': body_stream.read_ulong()}

        elif received_packet.header.data_type == types.DT_ACKNOWLEDGEMENT:

            # TODO: Make sure we can parse this acknowledgment packet.
            #       The header has a format of 3 and typically it arrives on channel/chunk stream id 2.
            #       The body consists of a 'Sequence number' - 7+ (59 bytes) in length.

            received_packet.body = {'sequence_number': body_stream.read_ulong()}

        elif received_packet.header.data_type == types.DT_WINDOW_ACK_SIZE:

            # ret['window_ack_size'] = body_stream.read_ulong()

            received_packet.body = {'window_ack_size': body_stream.read_ulong()}

        elif received_packet.header.data_type == types.DT_SET_PEER_BANDWIDTH:

            # ret['window_ack_size'] = body_stream.read_ulong()
            # ret['limit_type'] = body_stream.read_uchar()

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

            # ret['obj_name'] = obj_name
            # ret['curr_version'] = curr_version
            # ret['flags'] = flags
            # ret['events'] = events

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

            # ret['obj_name'] = obj_name
            # ret['curr_version'] = curr_version
            # ret['flags'] = flags
            # ret['events'] = events

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

            # ret['command'] = commands

            received_packet.body = {'command': commands}

        elif received_packet.header.data_type == types.DT_AMF3_COMMAND:

            decoder = pyamf.amf3.Decoder(body_stream)
            commands = []

            while not body_stream.at_eof():
                commands.append(decoder.readElement())

            # ret['command'] = commands

            received_packet.body = {'command': commands}

        elif received_packet.header.data_type == types.DT_DATA_MESSAGE:

            # ret['stream_id'] = header.stream_id
            # ret['metadata'] = message_body

            received_packet.body = {'metadata': message_body}

        elif received_packet.header.data_type == types.DT_AUDIO_MESSAGE:

            # ret['stream_id'] = header.stream_id
            # ret['control'] = body_stream.read_uchar()
            # ret['data'] = body_stream.read()

            received_packet.body = {
                'control': body_stream.read_uchar(),
                'audio_data': body_stream.read()
            }

        elif received_packet.header.data_type == types.DT_VIDEO_MESSAGE:

            # ret['stream_id'] = header.stream_id
            # ret['control'] = body_stream.read_uchar()
            # ret['data'] = body_stream.read()

            received_packet.body = {
                'control:': body_stream.read_uchar(),
                'video_data': body_stream.read()
            }

        else:
            assert False, received_packet.header

        log.debug('Received RTMPPacket() %r', received_packet)
        print('Header received: %s' % repr(received_packet))
        return received_packet

    @staticmethod
    def read_shared_object_event(body_stream, decoder):
        """
        Helper method that reads one shared object event found inside a shared
        object RTMP message.
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


class RtmpWriter:
    """ This class writes RTMP messages into a stream. """

    # Default write chunk size.
    chunk_size = 128

    # NetStream specific variables.
    # chunk_channels = []
    # _audio_packet_count = 0
    # _video_packet_count = 0
    # _av_channel_id = None

    def __init__(self, stream):
        """
        Initialize the RTMP writer and set it to write into the specified stream.
        Set up a default RTMPPacket to use along with it's PyAMF Buffered Byte Stream body.
        :param stream:
        """
        self.stream = stream

        # TODO: Absolute timestamp and timestamp delta calculation.
        # self.timestamp = None
        # self.write_packet = RTMPPacket()
        # TODO: packet body (body_stream) as a class variable?
        # self.packet_body = pyamf.util.BufferedByteStream()

    def flush(self):
        """ Flush the underlying stream. """
        self.stream.flush()

    # def reset_packet(self):
    #     """ Resets the RTMPPacket to a new value. """
    #     self.write_packet = RTMPPacket()
    #     self.packet_body = pyamf.util.BufferedByteStream()

    # TODO: Allow us to create custom packets in here and then send it off via send_msg which
    #       handles the packet contents.
    # TODO: Convert to RTMPPacket.
    def write(self, message, preset_packet=None):
        """
        Encode and write the specified message into the stream.
        :param message:
        :param preset_packet:
        """
        log.debug('Send message: %r', message)
        # TODO: Allow RTMPPacket entry.
        # Set up a default RTMPPacket to use along with it's PyAMF Buffered Byte-stream body.
        # If a preset packet is already provided we can just process that without creating a new one;
        # the datatype must be specified in the packet header and the body SHOULD NOT contain any data already
        # (any data present will be overwritten by the initialisation of the PyAMF Buffered Bytestream.
        if preset_packet is None:
            write_packet = RTMPPacket()
            write_packet.header.data_type = message['type']  # datatype = message['msg']
        else:
            write_packet = preset_packet

        # Set up the encoder and body to encode and assign to the RTMPPacket.
        write_packet.body = pyamf.util.BufferedByteStream()
        encoder = pyamf.amf0.Encoder(write_packet.body)

        if write_packet.header.data_type == types.DT_SET_CHUNK_SIZE:
            # RtmpHeader.ChunkType.TYPE_1_RELATIVE_LARGE, ChunkStreamInfo.CONTROL_CHANNEL,
            # RtmpHeader.MessageType.SET_CHUNK_SIZE

            # Set up the basic header information.
            write_packet.header.channel_id = CONTROL_CHANNEL
            write_packet.header.stream_id = 0

            # Set up the body content.
            # self.body_stream.write_long(message['chunk_size'])
            write_packet.body.write_long(message['chunk_size'])
            # Assign the buffered bytestream body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        elif write_packet.header.data_type == types.DT_ACKNOWLEDGEMENT:
            # RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.CONTROL_CHANNEL,
            # RtmpHeader.MessageType.ACKNOWLEDGEMENT

            # Set up the basic header information.
            write_packet.header.channel_id = CONTROL_CHANNEL
            write_packet.header.stream_id = 0

            # Set up the body content.
            write_packet.body.write_ulong(message['sequence_number'])

            # Assign the buffered bytestream body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        elif write_packet.header.data_type == types.DT_ABORT:
            # RtmpHeader.ChunkType.TYPE_1_RELATIVE_LARGE, ChunkStreamInfo.CONTROL_CHANNEL,
            # RtmpHeader.MessageType.ABORT

            # Set up the basic header information.
            write_packet.header.channel_id = CONTROL_CHANNEL
            write_packet.header.stream_id = 0

            # Set up the body content.
            write_packet.body.write_ulong(message['chunk_stream_id'])

            # Assign the buffered bytestream body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        elif write_packet.header.data_type == types.DT_USER_CONTROL:
            # RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.CONTROL_CHANNEL,
            # RtmpHeader.MessageType.USER_CONTROL_MESSAGE

            # Set up the basic header information.
            write_packet.header.stream_id = CONTROL_CHANNEL
            write_packet.header.stream_id = 0

            # Set up the body content.
            write_packet.body.write_ushort(message['event_type'])
            write_packet.body.write(message['event_data'])

            # Assign the buffered bytestream body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        elif write_packet.header.data_type == types.DT_WINDOW_ACK_SIZE:
            # RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.CONTROL_CHANNEL,
            # RtmpHeader.MessageType.WINDOW_ACKNOWLEDGEMENT_SIZE

            # Set up the basic header information.
            write_packet.header.channel_id = CONTROL_CHANNEL
            write_packet.header.stream_id = 0

            # Set up the body content.
            write_packet.body.write_ulong(message['window_ack_size'])

            # Assign the body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        elif write_packet.header.data_type == types.DT_SET_PEER_BANDWIDTH:
            # RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.CONTROL_CHANNEL,
            # RtmpHeader.MessageType.WINDOW_ACKNOWLEDGEMENT_SIZE

            # Set up the basic header information.
            write_packet.header.channel_id = CONTROL_CHANNEL
            write_packet.header.stream_id = 0

            # Set up the body content.
            write_packet.body.write_ulong(message['window_ack_size'])
            write_packet.body.write_uchar(message['limit_type'])

            # Assign the body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        elif write_packet.header.data_type == types.DT_AUDIO_MESSAGE:

            # Set up the body content.
            write_packet.body.write_uchar(message['body']['control'])
            write_packet.body.write(message['body']['data'])

            # Assign the body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        elif write_packet.header.data_type == types.DT_VIDEO_MESSAGE:

            # Set up the body content.
            write_packet.body.write_uchar(message['body']['control'])
            write_packet.body.write(message['body']['data'])

            # Assign the buffered bytestream body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        elif write_packet.header.data_type == types.DT_AMF3_COMMAND:

            # Set up the body content.
            encoder = pyamf.amf3.Encoder(write_packet.body)
            for command in message['command']:
                encoder.writeElement(command)

            # Assign the buffered bytestream body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        elif write_packet.header.data_type == types.DT_DATA_MESSAGE:
            # RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.RTMP_COMMAND_CHANNEL,
            # RtmpHeader.MessageType.DATA_AMF0

            # Set up the basic header information.
            write_packet.header.channel_id = RTMP_COMMAND_CHANNEL

            # Set up the body content.
            write_packet.body.write(message['metadata'])

            # Assign the buffered bytestream body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        elif write_packet.header.data_type == types.DT_SHARED_OBJECT:

            # Set up the basic header information.
            write_packet.header.channel_id = CONTROL_CHANNEL

            # Set up the body content.
            encoder.serialiseString(message['obj_name'])
            write_packet.body.write_ulong(message['curr_version'])
            write_packet.body.write(message['flags'])

            for event in message['events']:
                self.write_shared_object_event(event, write_packet.body)

            # Assign the buffered bytestream body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        elif write_packet.header.data_type == types.DT_COMMAND:
            # RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.RTMP_COMMAND_CHANNEL,
            # RtmpHeader.MessageType.COMMAND_AMF0

            # Set up the basic header information.
            write_packet.header.channel_id = RTMP_COMMAND_CHANNEL

            # Set up the body content.
            for command in message['command']:
                encoder.writeElement(command)

            # Handle specific stream messages by providing the RTMPPacket object.
            write_packet = self.handle_stream(write_packet, message)

            # Assign the body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        else:
            assert False, message

        # Send the packet we have generated.
        self.send_rtmp_message(write_packet)

    @staticmethod
    def write_shared_object_event(event, body_stream):
        """

        :param event:
        :param body_stream:
        """
        inner_stream = pyamf.util.BufferedByteStream()
        encoder = pyamf.amf0.Encoder(inner_stream)

        event_type = event['type']
        if event_type == types.SO_USE:
            assert event['data'] == '', event['data']

        elif event_type == types.SO_CHANGE:
            for attrib_name in event['data']:
                attrib_value = event['data'][attrib_name]
                encoder.serialiseString(attrib_name)
                encoder.writeElement(attrib_value)

        elif event['type'] == types.SO_CLEAR:
            assert event['data'] == '', event['data']

        elif event['type'] == types.SO_USE_SUCCESS:
            assert event['data'] == '', event['data']

        else:
            assert False, event

        body_stream.write_uchar(event_type)
        body_stream.write_ulong(len(inner_stream))
        body_stream.write(inner_stream.getvalue())

    # TODO: Convert to RTMPPacket.
    @staticmethod
    def handle_stream(rtmp_packet, message):  # body
        """
        Handle the header attributes to set when sending streamId specific messages.
        :param rtmp_packet:
        :param message: dict the stream specific message to handle.
        """
        # :param body: PyAMF Value the body stream.

        log.info('Received %s to handle_stream.' % message)

        if rtmp_packet.header.stream_id is -1:
            if 'stream_id' in message:
                rtmp_packet.header.stream_id = message['stream_id']
            else:
                rtmp_packet.header.stream_id = 0

        if rtmp_packet.header.channel_id is -1:
            # if rtmp_packet.header.data_type == types.DT_SET_CHUNK_SIZE:
            #     rtmp_packet.header.channel_id = CONTROL_CHANNEL  # 0x02

            if ('play' in message) or ('publish' in message):
                rtmp_packet.header.channel_id = RTMP_STREAM_CHANNEL  # 0x08

            elif rtmp_packet.header.data_type == types.DT_AUDIO_MESSAGE:
                # if self._audio_packet_count is 0 and self._av_channel_id is None:
                #     self._av_channel_id = 6
                # channel_id = self._av_channel_id
                # self._audio_packet_count += 1

                rtmp_packet.header.channel_id = 0x04  # 4

            elif rtmp_packet.header.data_type == types.DT_VIDEO_MESSAGE:
                # if self._video_packet_count is 0 and self._av_channel_id is None:
                #     self._av_channel_id = 6
                # if self._audio_packet_count is 0:
                #     channel_id = self._av_channel_id
                # else:
                #     channel_id = self._av_channel_id + 1
                # self._video_packet_count += 1

                rtmp_packet.header.channel_id = 0x06  # 6

            elif 'closeStream' in message:
                rtmp_packet.header.channel_id = RTMP_STREAM_CHANNEL  # 0x08

                # stream_id = 0

            # elif 'deleteStream' in message:
            #     stream_id = 0

        log.info('handle_stream set %s values of channelId: %s streamId: %s' %
                 (message, rtmp_packet.header.channel_id, rtmp_packet.header.stream_id))

        return rtmp_packet

    # TODO: Handle packet header properties, e.g. the format and the channel/chunk stream id.
    # TODO: Allow creation of the RTMPPacket elsewhere and just provide the packet in to send appropriately.
    # data_type, body, channel_id=RTMP_COMMAND_CHANNEL, timestamp=0, stream_id=0
    def send_rtmp_message(self, send_packet):
        """
        Helper method that sends the specified message into the stream.
        Takes care to prepend the necessary headers and split the message into
        appropriately sized chunks.

        :param send_packet:
        """

        # :param channel_id:
        # :param timestamp:
        # :param body:
        # :param data_type:
        # :param stream_id:

        # TODO: Some rules when handling header properties:
        #       - Type 0 MUST BE used at the start of a new chunk stream (with a new chunk stream id).
        #       - If packet format is Type 0 it has: timestamp, message length, message type id, message stream id.
        #       - If packet format is Type 1 it has: timestamp delta, message length, message type id.
        #       - If packet format is Type 2 it has: timestamp delta.
        #       - If packet format is Type 3 it has: No header, takes header from preceding chunk.
        #       - If the timestamp delta between the first message and the second message is same as the timestamp
        #         of the first message, then a chunk of Type 3 could immediately follow the chunk of Type 0
        #         as there is no need for a chunk of Type 2 to register the delta. If a Type 3 chunk follows a
        #         Type 0 chunk, then the timestamp delta for this Type 3 chunk is the same as the timestamp
        #         of the Type 0 chunk.

        # TODO: This handles NetConnection protocol messages.
        # Values that just work. :-)
        # if 1 <= send_packet.header.data_type <= 7:
        #     send_packet.header.channel_id = CONTROL_CHANNEL
        #     send_packet.header.stream_id = 0

        # Sort out the timestamp/timestamp delta for the packet.
        # if send_packet.header.timestamp is -1:
        #     if self.timestamp is None:
        #         self.timestamp = 0
        #     else:
        #         self.timestamp = (int(time.time())/1000) - (int(time.time()/1000))
        #     Set the current timestamp as the timestamp in the header for the RTMPPacket.
        #     send_packet.header.timestamp = self.timestamp

        # Sort whether to use the stream id or not, we will only use it at the beginning of a new chunk stream.
        # if send_packet.header.channel_id not in self.chunk_channels:
        #     self.chunk_channels.append(send_packet.header.channel_id)
        # else:
        #     send_packet.header.stream_id = -1

        # Retrieve the packet body assigned to the RTMPPacket.
        packet_body = send_packet.body

        # TODO: How can we be selective in the type of header format we want to send? Shall we manually state this or
        #       should there be a new way of defining what type of header it is.
        # Initialise the RTMP message header to use to send the whole message body.
        header = rtmp_protocol_header.Header(
            channel_id=send_packet.header.channel_id,
            timestamp=send_packet.header.timestamp,
            body_size=len(packet_body),
            data_type=send_packet.header.data_type,
            stream_id=send_packet.header.stream_id)

        # TODO: KEY ISSUE - How can we make sure only the right fields are sent when encoding the header? Should we
        #                   be able to set the header chunk type/format manually?

        # Encode the RTMP message header.
        rtmp_protocol_header.header_encode(self.stream, header)

        # Write chunks into the stream (message body split up with the same header).
        for i in xrange(0, len(packet_body), self.chunk_size):
            chunk = packet_body[i:i + self.chunk_size]
            self.stream.write(chunk)
            if i + self.chunk_size < len(packet_body):
                rtmp_protocol_header.header_encode(self.stream, header, header)

        # TODO: Moved to now using the RTMPPacket body as the PyAMF buffered bytestream, do we need a separate
        #       variable for this, and if so, do we need to have a reset body function to reset the body?
        # Reset the body value.
        # self.reset_body()


class FlashSharedObject:
    """ This class represents a Flash Remote Shared Object. """

    def __init__(self, name):
        """
        Initialize a new Flash Remote SO with a given name and empty data.
        NOTE: The data regarding the shared object is located inside the self.data dictionary.
        """
        self.name = name
        self.data = {}
        self.use_success = False

    # TODO: Convert to RTMPPacket.
    def use(self, writer):
        """
        Initialize usage of the SO by contacting the Flash Media Server.
        Any remote changes to the SO should be now propagated to the client.
        :param writer:
        """
        self.use_success = False

        msg = {
            'type': types.DT_SHARED_OBJECT,
            'curr_version': 0,
            'flags': '\x00\x00\x00\x00\x00\x00\x00\x00',
            'events': [
                {
                    'data': '',
                    'type': types.SO_USE
                }
            ],
            'obj_name': self.name
        }
        writer.write(msg)
        writer.flush()

    def handle_message(self, message):
        """
        Handle an incoming RTMP message. Check if it is of any relevance for the
        specific SO and process it, otherwise ignore it.
        :param message:
        """
        if message['type'] == types.DT_SHARED_OBJECT and message['obj_name'] == self.name:
            events = message['events']

            if not self.use_success:
                assert events[0]['type'] == types.SO_USE_SUCCESS, events[0]
                assert events[1]['type'] == types.SO_CLEAR, events[1]
                events = events[2:]
                self.use_success = True

            self.handle_events(events)
            return True
        else:
            return False

    def handle_events(self, events):
        """
        Handle SO events that target the specific SO.
        :param events:
        """
        for event in events:
            event_type = event['type']
            if event_type == types.SO_CHANGE:
                for key in event['data']:
                    self.data[key] = event['data'][key]
                    self.on_change(key)

            elif event_type == types.SO_REMOVE:
                key = event['data']
                assert key in self.data, (key, self.data.keys())
                del self.data[key]
                self.on_delete(key)

            elif event_type == types.SO_SEND_MESSAGE:
                self.on_message(event['data'])
            else:
                assert False, event

    @staticmethod
    def on_change(key):
        """
        Handle change events for the specific shared object.
        :param key:
        """
        pass

    @staticmethod
    def on_delete(key):
        """
        Handle delete events for the specific shared object. "
        :param key:
        """
        pass

    @staticmethod
    def on_message(data):
        """
        Handle message events for the specific shared object.
        :param data:
        """
        pass


class RtmpClient:
    """ Represents an RTMP client. """

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

    def handshake(self):
        """ Perform the handshake sequence with the server. """
        self.stream.write_uchar(3)
        c1 = HandshakePacket()
        c1.first = 0
        c1.second = 0
        c1.payload = self.create_random_bytes(1528)
        c1.encode(self.stream)
        self.stream.flush()

        self.stream.read_uchar()
        s1 = HandshakePacket()
        s1.decode(self.stream)

        c2 = HandshakePacket()
        c2.first = s1.first
        c2.second = s1.second
        c2.payload = s1.payload
        c2.encode(self.stream)
        self.stream.flush()

        s2 = HandshakePacket()
        s2.decode(self.stream)

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
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.SOL_TCP)

        # Set socket options:
        #   - turn on TCP keep-alive (generally)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        # TODO: If we avoid using a file-object in the future, we can keep this in. However when using a file-object,
        #       non-blocking or timeout mode cannot be used since operations that cannot be completed immediately fail.
        #   - non-blocking socket
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
        self.reader = RtmpReader(self.stream)
        self.writer = RtmpWriter(self.stream)

        # Start an RTMP connection to the server.
        self.connect_rtmp(connect_params)

    # TODO: Convert to RTMPPacket.
    def connect_rtmp(self, connect_params):
        """
        Initiate an RTMP connection with the Flash Media Server (FMS) by sending an RTMP connection packet,
        with the appropriate header information.
        :param connect_params:
        """
        # Format: 0
        # Channel ID: 3
        # Timestamp: 1
        # Body size = variable
        # Type ID: 20
        # Stream ID: 0

        # Initialise an RTMPPacket for use.
        connection_packet = RTMPPacket()

        rtmp_connect_msg = {
            # 'type': types.DT_COMMAND,
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
        if type(connect_params) is dict:
            rtmp_connect_msg['command'].append(connect_params)
        else:
            rtmp_connect_msg['command'].extend(connect_params)

        # Set up the connection packet's header information.
        connection_packet.header.channel_id = RTMP_COMMAND_CHANNEL
        connection_packet.header.timestamp = 1
        connection_packet.header.data_type = types.DT_COMMAND
        connection_packet.header.stream_id = 0

        self.writer.write(rtmp_connect_msg, connection_packet)
        self.writer.flush()

    def handle_packet(self, packet):
        """
        Handle packets based on data type.
        :param packet: RTMPPacket object with both the header and body (AMF decoded data).
        """
        # if amf_data['msg'] == types.DT_USER_CONTROL and amf_data['event_type'] == types.UC_STREAM_BEGIN:
        if packet.header.data_type == types.DT_USER_CONTROL and packet.body['event_type'] == types.UC_STREAM_BEGIN:
            assert packet.body['event_type'] == types.UC_STREAM_BEGIN, packet.body
            assert packet.body['event_data'] == '\x00\x00\x00\x00', packet.body
            log.info('Handled STREAM_BEGIN packet: %s' % packet.body)
            return True

        elif packet.header.data_type == types.DT_WINDOW_ACK_SIZE:
            # The window acknowledgement may actually vary, rather than one asserted by us,
            # we do not actually handle this specifically (for now).
            assert packet.body['window_ack_size'] == 2500000, packet.body
            self.send_window_ack_size(packet.body)
            log.info('Handled WINDOW_ACK_SIZE packet with response to server.')
            return True

        elif packet.header.data_type == types.DT_SET_PEER_BANDWIDTH:
            assert packet.body['window_ack_size'] == 2500000, packet.body
            # TODO: Should we consider the other limit types: hard and soft (we can just assume dynamic)?
            assert packet.body['limit_type'] == 2, packet.body
            log.info('Handled SET_PEER_BANDWIDTH packet: %s' % packet.body)
            return True

        elif packet.header.data_type == types.DT_SET_CHUNK_SIZE:
            assert 0 < packet.body['chunk_size'] <= 65536, packet.body
            self.reader.chunk_size = packet.body['chunk_size']
            log.info('Handled SET_CHUNK_SIZE packet with new chunk size: %s' % self.reader.chunk_size)
            return True

        elif packet.header.data_type == types.DT_USER_CONTROL and packet.body['event_type'] == types.UC_PING_REQUEST:
            self.send_pong_reply(packet.body)
            log.info('Handled PING_REQUEST packet with response to server.')
            return True

        elif packet.header.data_type == types.DT_USER_CONTROL and packet.body['event_type'] == types.UC_PONG_REPLY:
            unpacked_tpl = struct.unpack('>I', packet.body['event_data'])
            unpacked_response = unpacked_tpl[0]
            log.debug('Server sent PONG_REPLY: %s' % unpacked_response)
            return True

        else:
            return False

    # TODO: Convert to RTMPPacket.
    def call(self, process_name, parameters=None, trans_id=0):
        """
        Runs remote procedure calls (RPC) at the receiving end.
        :param process_name:
        :param parameters:
        :param trans_id:
        """
        if parameters is None:
            parameters = {}

        msg = {
            'type': types.DT_COMMAND,
            'command': [process_name, trans_id, parameters]
        }

        self.writer.write(msg)
        self.writer.flush()

    def shared_object_use(self, so):
        """
        Use a shared object and add it to the managed list of shared objects (SOs).
        :param so:
        """
        if so in self._shared_objects:
            return
        so.use(self.reader, self.writer)
        self._shared_objects.append(so)

    # TODO: Convert to RTMPPacket.
    def send_window_ack_size(self, amf_data):
        """
        Send a WINDOW_ACK_SIZE message.
        :param amf_data: list the AMF data that was received from the server (including the window ack size).
        """
        ack_msg = {
            'type': types.DT_WINDOW_ACK_SIZE,
            'window_ack_size': amf_data['window_ack_size']
        }

        log.info('Sending WINDOW_ACK_SIZE to server: %s' % ack_msg)
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
            'type': types.DT_USER_CONTROL,
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
            'type': types.DT_USER_CONTROL,
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


__all__ = [
    'RTMPPacket',
    'RtmpReader',
    'RtmpWriter',
    'FlashSharedObject',
    'RtmpClient'
]
