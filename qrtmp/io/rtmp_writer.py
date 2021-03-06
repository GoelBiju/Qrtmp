""" RTMP Writer """

import pyamf
import pyamf.amf0
import pyamf.amf3

from qrtmp.formats import rtmp_packet
from qrtmp.formats import types


class RtmpWriter:
    """ This class writes RTMP messages into a stream. """

    def __init__(self, rtmp_stream, rtmp_header_handler):
        """
        Initialize the RTMP writer and set it to write into the specified stream.
        Set up a default RtmpPacket to use along with it's PyAMF Buffered Byte Stream body.

        :param rtmp_stream:
        :param rtmp_header_handler:
        """
        # Initialise the RTMP stream.
        self._rtmp_stream = rtmp_stream

        # Default write chunk size at the beginning of the RTMP stream.
        self.chunk_size = 128

        self.transaction_id = 0

        # Set up the RTMP header handler.
        self._rtmp_header_handler = rtmp_header_handler

        self._write_packet = None
        self._send_packet = None

        # TODO: Absolute timestamp and timestamp delta calculation.
        # TODO: Make use of the chunk streams we are using to put RTMP rules into effect.
        #       I.e. At start of chunk stream we send a full header chunk type.

    def stream_flush(self):
        """ Flush the underlying stream. """
        self._rtmp_stream.flush()

    @staticmethod
    def new_packet():
        """
        A connective method to return an invalid and empty RtmpPacket.

        :return rtmp_packet.RtmpPacket: object
        """
        return rtmp_packet.RtmpPacket()

    def reset_working_packets(self):
        """ Resets the write and send packets. """
        self._write_packet = None
        self._send_packet = None

    # DONE?: Allow us to create custom formats in here and then send it off via send_msg which
    #       handles the packet contents.
    # DONE: Allowed RtmpPacket entry.

    # TODO: Moved to RtmpPacket, as a function.

    # TODO: We need move the encoding and writing to body aspect to another function.
    # def setup_packet(self, write_packet):
    #     """
    #     Setup an RtmpPacket with specified parameters to encode/write into the RTMP stream.
    #
    #     INFO: Sets up a default RtmpPacket to use along with it's PyAMF Buffered Byte-stream body.
    #           If a preset packet is already provided we can just process that without creating a new one;
    #           the data-type must be specified in the packet header and the body SHOULD NOT contain any data already
    #           (any data present will be overwritten by the initialisation of the PyAMF Buffered Bytestream.
    #
    #     :param write_packet: RtmpPacket object to setup and prepare for sending.
    #     """
    #     # Set up the encoder and body buffer which is to be assigned to
    #     # the RtmpPacket once data has been written into it.
    #     packet_body_buffer = pyamf.util.BufferedByteStream()
    #
    #     if write_packet.header.data_type == types.DT_SET_CHUNK_SIZE:
    #         # NOTE: RtmpHeader.ChunkType.TYPE_1_RELATIVE_LARGE, ChunkStreamInfo.CONTROL_CHANNEL,
    #         #       RtmpHeader.MessageType.SET_CHUNK_SIZE
    #
    #         # Set up the basic header information.
    #         write_packet.header.chunk_stream_id = types.RTMP_CONTROL_CHUNK_STREAM
    #         write_packet.header.stream_id = 0
    #
    #         # Set up the body content.
    #         packet_body_buffer.write_long(write_packet.body['chunk_size'])
    #
    #         # Assign the buffered bytestream body value into the RtmpPacket; freeing the body before-hand.
    #         write_packet.free_body()
    #         write_packet.body = packet_body_buffer.getvalue()
    #
    #     elif write_packet.header.data_type == types.DT_ACKNOWLEDGEMENT:
    #         # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.CONTROL_CHANNEL,
    #         #       RtmpHeader.MessageType.ACKNOWLEDGEMENT
    #
    #         # Set up the basic header information.
    #         write_packet.header.chunk_stream_id = types.RTMP_CONTROL_CHUNK_STREAM
    #         write_packet.header.stream_id = 0
    #
    #         # Set up the body content.
    #         packet_body_buffer.write_ulong(write_packet.body['sequence_number'])
    #
    #         # Assign the buffered bytestream body value into the RtmpPacket; freeing the body before-hand.
    #         write_packet.free_body()
    #         write_packet.body = packet_body_buffer.getvalue()
    #
    #     elif write_packet.header.data_type == types.DT_ABORT:
    #         # NOTE: RtmpHeader.ChunkType.TYPE_1_RELATIVE_LARGE, ChunkStreamInfo.CONTROL_CHANNEL,
    #         #       RtmpHeader.MessageType.ABORT
    #
    #         # Set up the basic header information.
    #         write_packet.header.chunk_stream_id = types.RTMP_CONTROL_CHUNK_STREAM
    #         write_packet.header.stream_id = 0
    #
    #         # Set up the body content.
    #         packet_body_buffer.write_ulong(write_packet.body['chunk_stream_id'])
    #
    #         # Assign the buffered bytestream body value into the RtmpPacket; freeing the body before-hand.
    #         write_packet.free_body()
    #         write_packet.body = packet_body_buffer.getvalue()
    #
    #     elif write_packet.header.data_type == types.DT_USER_CONTROL:
    #         # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.RTMP_CONTROL_CHANNEL,
    #         #       RtmpHeader.MessageType.USER_CONTROL_MESSAGE
    #
    #         # Set up the basic header information.
    #         write_packet.header.stream_id = types.RTMP_CONTROL_CHUNK_STREAM
    #         write_packet.header.stream_id = 0
    #
    #         # Set up the body content.
    #         # TODO: Event data itself may not be stated in pcap files, however it proceeds after the event type.
    #         # if 'event_type' in write_packet.body:
    #         packet_body_buffer.write_ushort(write_packet.body['event_type'])
    #         # if 'event_data' in write_packet.body:
    #         packet_body_buffer.write(write_packet.body['event_data'])
    #
    #         # Assign the buffered bytestream body value into the RtmpPacket; freeing the body before-hand.
    #         write_packet.free_body()
    #         write_packet.body = packet_body_buffer.getvalue()
    #
    #     elif write_packet.header.data_type == types.DT_WINDOW_ACKNOWLEDGEMENT_SIZE:
    #         # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.CONTROL_CHANNEL,
    #         #       RtmpHeader.MessageType.WINDOW_ACKNOWLEDGEMENT_SIZE
    #
    #         # Set up the basic header information.
    #         write_packet.header.chunk_stream_id = types.RTMP_CONTROL_CHUNK_STREAM
    #         write_packet.header.stream_id = 0
    #
    #         # Set up the body content.
    #         packet_body_buffer.write_ulong(write_packet.body['window_acknowledgement_size'])
    #
    #         # Assign the buffered bytestream body value into the RtmpPacket; freeing the body before-hand.
    #         write_packet.free_body()
    #         write_packet.body = packet_body_buffer.getvalue()
    #
    #     elif write_packet.header.data_type == types.DT_SET_PEER_BANDWIDTH:
    #         # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.CONTROL_CHANNEL,
    #         #       RtmpHeader.MessageType.WINDOW_ACKNOWLEDGEMENT_SIZE
    #
    #         # Set up the basic header information.
    #         write_packet.header.chunk_stream_id = types.RTMP_CONTROL_CHUNK_STREAM
    #         write_packet.header.stream_id = 0
    #
    #         # Set up the body content.
    #         packet_body_buffer.write_ulong(write_packet.body['window_acknowledgement_size'])
    #         packet_body_buffer.write_uchar(write_packet.body['limit_type'])
    #
    #         # Assign the buffered bytestream body value into the RtmpPacket; freeing the body before-hand.
    #         write_packet.free_body()
    #         write_packet.body = packet_body_buffer.getvalue()
    #
    #     elif write_packet.header.data_type == types.DT_AUDIO_MESSAGE:
    #
    #         # TODO: Testing header information for now.
    #         # Set up the basic header information.
    #         # TODO: Connect to NetStream chunk stream id attribute?
    #         write_packet.header.chunk_stream_id = types.RTMP_CUSTOM_AUDIO_CHUNK_STREAM
    #
    #         # TODO: Connect to NetStream stream id attribute?
    #         write_packet.header.stream_id = 1
    #
    #         # Set up the body content.
    #         packet_body_buffer.write_uchar(write_packet.body['control'])
    #         packet_body_buffer.write(write_packet.body['audio_data'])
    #
    #         # Assign the buffered bytestream body value into the RtmpPacket; freeing the body before-hand.
    #         write_packet.free_body()
    #         write_packet.body = packet_body_buffer.getvalue()
    #
    #     elif write_packet.header.data_type == types.DT_VIDEO_MESSAGE:
    #
    #         # TODO: Testing header information for now.
    #         # Set up the basic header information.
    #         # TODO: Connect to NetStream chunk stream id attribute?
    #         write_packet.header.chunk_stream_id = types.RTMP_CUSTOM_VIDEO_CHUNK_STREAM
    #
    #         # TODO: Connect to NetStream stream id attribute?
    #         write_packet.header.stream_id = 1
    #
    #         # Set up the body content.
    #         packet_body_buffer.write_uchar(write_packet.body['control'])
    #         packet_body_buffer.write(write_packet.body['video_data'])
    #
    #         # Assign the buffered bytestream body value into the RtmpPacket; freeing the body before-hand.
    #         write_packet.free_body()
    #         write_packet.body = packet_body_buffer.getvalue()
    #
    #     elif write_packet.header.data_type == types.DT_AMF3_COMMAND:
    #         # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.RTMP_COMMAND_CHANNEL,
    #         #       RtmpHeader.MessageType.COMMAND_AMF0
    #
    #         # Set up the basic header information.
    #         write_packet.header.chunk_stream_id = types.RTMP_CONNECTION_CHUNK_STREAM
    #
    #         # Set up the body content.
    #         encoder = pyamf.amf3.Encoder(packet_body_buffer)
    #         # for command in write_packet.body['command']:
    #         #     encoder.writeElement(command)
    #
    #         # Write the command name and transaction id, followed by an iteration over the
    #         # command object to write the AMF elements.
    #         encoder.writeElement(write_packet.body['command_name'])
    #         encoder.writeElement(write_packet.body['transaction_id'])
    #         encoder.writeElement(write_packet.body['command_object'])
    #         for parameter in write_packet.body['options']:
    #             encoder.writeElement(parameter)
    #
    #         # Assign the buffered bytestream body value into the RtmpPacket; freeing the body before-hand.
    #         write_packet.free_body()
    #         write_packet.body = packet_body_buffer.getvalue()
    #
    #         # The body we encoded was AMF formatted.
    #         write_packet.body_is_amf = True
    #
    #     elif write_packet.header.data_type == types.DT_DATA_MESSAGE:
    #         # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.RTMP_COMMAND_CHANNEL,
    #         #       RtmpHeader.MessageType.DATA_AMF0
    #
    #         # Set up the basic header information.
    #         write_packet.header.chunk_stream_id = types.RTMP_CONNECTION_CHUNK_STREAM
    #
    #         encoder = pyamf.amf0.Encoder(packet_body_buffer)
    #         # Set up the body content.
    #         encoder.writeElement(write_packet.body['onMetaData'])
    #         """
    #         ('Packet:', {'data_content': [
    #             {'videoframerate': 24, 'moovposition': 8671904, 'avclevel': 30, 'avcprofile': 66,
    #              'audiosamplerate': 12000, 'audiocodecid': u'mp4a', 'framerate': 24, 'height': 160, 'width': 240,
    #              'displayWidth': 240, 'audiochannels': 2, 'frameHeight': 160, 'frameWidth': 240, 'duration': 596.48,
    #              'displayHeight': 160, 'aacaot': 2, 'videocodecid': u'avc1', 'trackinfo': [
    #                 {'length': 14315, 'language': u'eng', 'timescale': 24,
    #                  'sampledescription': [{'sampletype': u'avc1'}]},
    #                 {'length': 7157760, 'language': u'eng', 'timescale': 12000,
    #                  'sampledescription': [{'sampletype': u'mp4a'}]}]}], 'data_name': u'onMetaData'})
    #         """
    #         encoder.writeMixedArray(write_packet.body['metadata'])
    #
    #         # Assign the buffered bytestream body value into the RtmpPacket; freeing the body before-hand.
    #         write_packet.free_body()
    #         write_packet.body = packet_body_buffer.getvalue()
    #
    #     elif write_packet.header.data_type == types.DT_SHARED_OBJECT:
    #
    #         # Set up the basic header information.
    #         write_packet.header.chunk_stream_id = types.RTMP_CONNECTION_CHUNK_STREAM
    #
    #         # Set up the body content.
    #         encoder = pyamf.amf0.Encoder(packet_body_buffer)
    #         encoder.serialiseString(write_packet.body['obj_name'])
    #         packet_body_buffer.write_ulong(write_packet.body['curr_version'])
    #         packet_body_buffer.write(write_packet.body['flags'])
    #
    #         for event in write_packet.body['events']:
    #             self.write_shared_object_event(event, packet_body_buffer)
    #
    #         # Assign the buffered bytestream body value into the RtmpPacket; freeing the body before-hand.
    #         write_packet.free_body()
    #         write_packet.body = packet_body_buffer.getvalue()
    #
    #         # The body we encoded was a Shared Object.
    #         write_packet.body_is_so = True
    #
    #     # TODO: Is it possible to remove the list, so we can freely add various data structures to the command_object
    #     #       or options fields without having to place it inside a list all the time
    #     #       (or would it remove it's iterable feature)?
    #     elif write_packet.header.data_type == types.DT_COMMAND:
    #         # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.RTMP_COMMAND_CHANNEL,
    #         #       RtmpHeader.MessageType.COMMAND_AMF0
    #
    #         # Set up the basic header information.
    #         write_packet.header.chunk_stream_id = types.RTMP_CONNECTION_CHUNK_STREAM
    #
    #         # Set up the body content.
    #         encoder = pyamf.amf0.Encoder(packet_body_buffer)
    #         # for command in write_packet.body['command']:
    #         #     encoder.writeElement(command)
    #
    #         # Write the command name and transaction id, followed by an iteration over the
    #         # command object to write the AMF elements.
    #         encoder.writeElement(write_packet.body['command_name'])
    #         encoder.writeElement(write_packet.body['transaction_id'])
    #         # TODO: Iteration over the command object would be an issue here (in the event of the connection packet,
    #         #       maybe we should handle all formats and assume the command object is going to be used anyhow).
    #         command_object = write_packet.body['command_object']
    #         if type(command_object) is list:
    #             for command_info in command_object:
    #                 encoder.writeElement(command_info)
    #         else:
    #             # TODO: Allow types which are not iterable to be written on it's own into the stream.
    #             encoder.writeElement(command_object)
    #
    #         options = write_packet.body['options']
    #         if type(options) is list:
    #             for parameter in options:
    #                 encoder.writeElement(parameter)
    #
    #         # TODO: Converted stream information handling into types and to RtmpPacket.
    #
    #         # Assign the buffered bytestream body value into the RtmpPacket; freeing the body before-hand.
    #         write_packet.free_body()
    #         write_packet.body = packet_body_buffer.getvalue()
    #
    #         # The body we encoded was AMF formatted.
    #         write_packet.body_is_amf = True
    #
    #     else:
    #         assert False, write_packet

    @staticmethod
    def write_shared_object_event(event, body_stream):
        """

        :param event: dict
        :param body_stream: PyAMF BufferedByteStream object
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

    # DONE: Allow creation of the RtmpPacket elsewhere and just provide the packet in to send appropriately.

    # TODO: KEY ISSUE - How can we make sure only the right fields are sent when encoding the header? Should we
    #                   be able to set the header chunk type/format manually?
    # TODO: How can we be selective in the type of header format we want to send? Shall we manually state this or
    #       should there be a new way of defining what type of header it is.
    def send_packet(self, packet):
        """
        Helper method that sends the specified message into the stream.
        Takes care to prepend the necessary headers and split the message into
        appropriately sized chunks.

        :param packet: RtmpPacket object
        """
        # print('sending packet')

        # If the packet was not set up, then make sure we have the body buffer ready to write.
        if packet.body_buffer is None:
            # print('body buffer was none')
            packet.setup()

            # print('we set up the packet')

            # DONE: stream.flush() is called automatically after the packet has been sent.
            # Flush file-object.
            self.stream_flush()

            # print('flushed stream')

        # TODO: Sort whether to use the stream id or not, we will only use it at the beginning of a new chunk stream.
        # if send_packet.header.chunk_stream_id not in self.chunk_channels:
        #     self.chunk_channels.append(send_packet.header.chunk_stream_id)
        # else:
        #     send_packet.header.chunk_type = 1
        #     send_packet.header.stream_id = -1

        # TODO: Sort out the timestamp/timestamp delta for the packet.
        # if send_packet.header.timestamp is -1:
        #     if self.timestamp is None:
        #         self.timestamp = 0
        #     else:
        #         self.timestamp = (int(time.time())/1000) - (int(time.time()/1000))
        #     Set the current timestamp as the timestamp in the header for the RtmpPacket.
        #     send_packet.header.timestamp = self.timestamp

        # Encode the initial header before the main RTMP message.
        # rtmp_header.encode(self._rtmp_stream, packet.header)
        self._rtmp_header_handler.encode_into_stream(packet.header)

        # print('encoded first header into stream')

        # TODO: We need to chunk all formats message bodies, however we need to put into perspective
        #       whether message that are to be sent are related to one another and what format it needs to be.

        # Write chunks into the stream.
        for i in xrange(0, packet.header.body_length, self.chunk_size):
            write_size = i + self.chunk_size
            chunk = packet.body_buffer[i:write_size]
            self._rtmp_stream.write(chunk)
            # print('writing chunk')

            # TODO: Why is the previous in the header encode always 0?
            # We keep on encoding a header for each part of the packet body we send, until it is equal to
            # or exceeds the length of the packet body.
            if write_size < packet.header.body_length:
                # print('continuing chunks')
                # We provide the previous packet we encoded to provide context into what we are sending.
                # TODO: The rtmp_stream is None when entering here.
                # rtmp_header.encode(self._rtmp_stream, packet.header, packet.header)
                self._rtmp_header_handler.encode_into_stream(packet.header)

        # print('all chunks written')

        # TODO: Moved to now using the RtmpPacket body as the PyAMF buffered bytestream, do we need a separate
        #       variable for this, and if so, do we need to have a reset body function to reset the body?

        # print('[Written] %s' % repr(send_packet.header))

        # TODO: If we do not flush the stream after sending one packet, we might not get the reply after a while.
        self.stream_flush()


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

    # TODO: Convert to RtmpPacket.
    def use(self, writer):
        """
        Initialize usage of the SO by contacting the Flash Media Server.
        Any remote changes to the SO should be now propagated to the client.

        :param writer:
        """
        self.use_success = False

        # msg = {
        #     'data_type': types.DT_SHARED_OBJECT,
        #     'curr_version': 0,
        #     'flags': '\x00\x00\x00\x00\x00\x00\x00\x00',
        #     'events': [
        #         {
        #             'data': '',
        #             'type': types.SO_USE
        #         }
        #     ],
        #     'obj_name': self.name
        # }

        so_use = writer.new_packet()
        so_use.header.data_type = types.DT_SHARED_OBJECT

        so_use.body = {
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

        # writer.write(msg)
        # writer.flush()

        writer.setup_packet(so_use)

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
        Handle delete events for the specific shared object.

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
