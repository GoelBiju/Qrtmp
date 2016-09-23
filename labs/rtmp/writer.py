"""

"""

import logging

import pyamf
import pyamf.amf0
import pyamf.amf3
import types
import packet

import rtmp_protocol_header

log = logging.getLogger(__name__)


class RtmpWriter:
    """ This class writes RTMP messages into a stream. """

    # Default write chunk size.
    chunk_size = 128

    # NetStream specific variables.
    chunk_channels = []

    # _audio_packet_count = 0
    # _video_packet_count = 0
    # _av_chunk_stream_id = None

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
            write_packet = packet.RtmpPacket()
            write_packet.header.data_type = message['data_type']  # datatype = message['msg']
        else:
            write_packet = preset_packet

        # Set up the encoder and body to encode and assign to the RTMPPacket.
        write_packet.body = pyamf.util.BufferedByteStream()
        encoder = pyamf.amf0.Encoder(write_packet.body)

        if write_packet.header.data_type == types.DT_SET_CHUNK_SIZE:
            # RtmpHeader.ChunkType.TYPE_1_RELATIVE_LARGE, ChunkStreamInfo.CONTROL_CHANNEL,
            # RtmpHeader.MessageType.SET_CHUNK_SIZE

            # Set up the basic header information.
            write_packet.header.chunk_stream_id = types.CONTROL_CHANNEL
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
            write_packet.header.chunk_stream_id = types.CONTROL_CHANNEL
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
            write_packet.header.chunk_stream_id = types.CONTROL_CHANNEL
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
            write_packet.header.stream_id = types.CONTROL_CHANNEL
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
            write_packet.header.chunk_stream_id = types.CONTROL_CHANNEL
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
            write_packet.header.chunk_stream_id = types.CONTROL_CHANNEL
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
            write_packet.header.chunk_stream_id = types.RTMP_COMMAND_CHANNEL

            # Set up the body content.
            write_packet.body.write(message['metadata'])

            # Assign the buffered bytestream body value into the RTMPPacket.
            write_packet.body = write_packet.body.getvalue()

            # self.send_rtmp_message(datatype, self.body_stream.getvalue())

        elif write_packet.header.data_type == types.DT_SHARED_OBJECT:

            # Set up the basic header information.
            write_packet.header.chunk_stream_id = types.CONTROL_CHANNEL

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
            write_packet.header.chunk_stream_id = types.RTMP_COMMAND_CHANNEL

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
        self.send_rtmp_packet(write_packet)

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

        # if rtmp_packet.header.chunk_stream_id is -1:
            # if rtmp_packet.header.data_type == types.DT_SET_CHUNK_SIZE:
            #     rtmp_packet.header.chunk_stream_id = CONTROL_CHANNEL  # 0x02

        if ('play' in message['command']) or ('publish' in message['command']):
            rtmp_packet.header.chunk_stream_id = types.RTMP_STREAM_CHANNEL  # 0x08

        elif rtmp_packet.header.data_type == types.DT_AUDIO_MESSAGE:
            # if self._audio_packet_count is 0 and self._av_chunk_stream_id is None:
            #     self._av_chunk_stream_id = 6
            # chunk_stream_id = self._av_chunk_stream_id
            # self._audio_packet_count += 1

            rtmp_packet.header.chunk_stream_id = 0x04  # 4

        elif rtmp_packet.header.data_type == types.DT_VIDEO_MESSAGE:
            # if self._video_packet_count is 0 and self._av_chunk_stream_id is None:
            #     self._av_chunk_stream_id = 6
            # if self._audio_packet_count is 0:
            #     chunk_stream_id = self._av_chunk_stream_id
            # else:
            #     chunk_stream_id = self._av_chunk_stream_id + 1
            # self._video_packet_count += 1

            rtmp_packet.header.chunk_stream_id = 0x06  # 6

        elif 'closeStream' in message['command']:
            rtmp_packet.header.chunk_stream_id = types.RTMP_STREAM_CHANNEL  # 0x08

            # stream_id = 0

        # elif 'deleteStream' in message:
        #     stream_id = 0

        log.info('handle_stream set %s values of channelId: %s streamId: %s' %
                 (message, rtmp_packet.header.chunk_stream_id, rtmp_packet.header.stream_id))

        return rtmp_packet

    # TODO: Handle packet header properties, e.g. the format and the channel/chunk stream id.
    # TODO: Allow creation of the RTMPPacket elsewhere and just provide the packet in to send appropriately.
    # data_type, body, chunk_stream_id=RTMP_COMMAND_CHANNEL, timestamp=0, stream_id=0

    def send_rtmp_packet(self, send_packet):
        """
        Helper method that sends the specified message into the stream.
        Takes care to prepend the necessary headers and split the message into
        appropriately sized chunks.

        :param send_packet: RtmpPacket object
        """
        # :param chunk_stream_id:
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
        #     send_packet.header.chunk_stream_id = CONTROL_CHANNEL
        #     send_packet.header.stream_id = 0

        # TODO: How can we be selective in the type of header format we want to send? Shall we manually state this or
        #       should there be a new way of defining what type of header it is.

        # TODO: The header should be from the rtmp packet.
        # Initialise the RTMP message header to use to send the whole message body.
        packet_header = rtmp_protocol_header.Header(
            chunk_stream_id=send_packet.header.chunk_stream_id,
            timestamp=send_packet.header.timestamp,
            body_length=len(send_packet.body),  # packet_body
            data_type=send_packet.header.data_type,
            stream_id=send_packet.header.stream_id)

        # Sort whether to use the stream id or not, we will only use it at the beginning of a new chunk stream.
        # if send_packet.header.chunk_stream_id not in self.chunk_channels:
        #     self.chunk_channels.append(send_packet.header.chunk_stream_id)
        # else:
        #     send_packet.header.format = 1
        #     send_packet.header.stream_id = -1

        # header = send_packet.header
        # header.body_length = len(send_packet.body)

        # Sort out the timestamp/timestamp delta for the packet.
        # if send_packet.header.timestamp is -1:
        #     if self.timestamp is None:
        #         self.timestamp = 0
        #     else:
        #         self.timestamp = (int(time.time())/1000) - (int(time.time()/1000))
        #     Set the current timestamp as the timestamp in the header for the RTMPPacket.
        #     send_packet.header.timestamp = self.timestamp

        # TODO: KEY ISSUE - How can we make sure only the right fields are sent when encoding the header? Should we
        #                   be able to set the header chunk type/format manually?

        # Encode the initial header before the main RTMP message.
        rtmp_protocol_header.encode(self.stream, packet_header)

        # TODO: We need to chunk all packets message bodies, however we need to put into perspective
        #       whether message that are to be sent are related to one another and what format it needs to be.
        # Write chunks into the stream (message body split up with the same header).
        # c = 0
        for i in xrange(0, len(send_packet.body), self.chunk_size):
            # c += 1
            # print('Writing chunk #' + str(c + 1))
            write_size = i + self.chunk_size
            chunk = send_packet.body[i:write_size]
            self.stream.write(chunk)

            # We keep on encoding a header for each part of the packet body we send, until it is equal to
            # or exceeds the length of the packet body.
            if write_size < len(send_packet.body):
                # We provide the previous packet we encoded to provide context into what we are sending.
                rtmp_protocol_header.encode(self.stream, packet_header, packet_header)

        # TODO: Moved to now using the RtmpPacket body as the PyAMF buffered bytestream, do we need a separate
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
            'data_type': types.DT_SHARED_OBJECT,
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
        if message['data_type'] == types.DT_SHARED_OBJECT and message['obj_name'] == self.name:
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


__all__ = [
    'RtmpWriter',
    'FlashSharedObject'
]