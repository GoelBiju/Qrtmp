""" Classes relevant to the basic RTMP packet structure; the packet header and body. """

import pyamf
import pyamf.amf0
import pyamf.amf3

# from qrtmp.formats import rtmp_header
# from qrtmp.formats import types

import qrtmp.formats.rtmp_header as rtmp_header
import qrtmp.formats.types as types


# TODO: Any other essential packet methods?
class RtmpPacket(object):
    """ A class to abstract the RTMP formats (received) which consists of an RTMP header and an RTMP body. """

    # TODO: Possible smallest header function to make it small as possible if we give it the previous the full header
    #       at the start of the chunk stream and it decides what to copy over to make it small as possible.
    #       Or maybe give it the previous packet and current channels/streams being used.
    # TODO: Formatting of names: _chunk_type, _extended_timestamp, _timestamp_absolute or _timestamp_delta?
    # TODO: Raise error message in the event that an invalid header and body is trying to be sent, this should prevent
    #       the message from going into the stream and crashing it.
    def __init__(self, set_header=None, set_body=None):
        """
        Initialise the packet by providing the header information and body data.

        NOTE:   The packet can be initialised without providing a header or a body, however,
                in order to use this packet, you must eventually assign the correct RTMP header and body.

                If you initialise the packet without these two, a default header with a chunk_stream_id value of -1
                will be used to encode/decode (with no packet body).

                In this case, you MUST NOT use the packet for encoding/decoding to/from the RTMP stream.

        :param set_header: L{Header} header with the appropriate values.
        :param set_body: dict the body of the rtmp packet, with each key being a section of the RTMP packet.
        """
        # Make sure all the header and body contents are cleared before initialising.
        # if self.header is not None or self.body is not None or self.body_buffer is not None:
        #     self.reset()

        # Set up a blank header, body and body_buffer.
        self.header = rtmp_header.RtmpHeader(-1)
        self.body_buffer = None
        self.body = None

        # Handle the packet header.
        if set_header is not None:
            self.header.chunk_type = set_header.chunk_type
            self.header.chunk_stream_id = set_header.chunk_stream_id

            self.header.timestamp = set_header.timestamp
            self.header.body_length = set_header.body_length
            self.header.data_type = set_header.data_type
            self.header.stream_id = set_header.stream_id
            self.header.extended_timestamp = set_header.extended_timestamp

            self.timestamp_absolute = set_header.timestamp_absolute
            self.timestamp_delta = set_header.timestamp_delta

        # Handle the packet body.
        if set_body is not None:
            self.body = set_body

        # TODO: Add convenience methods to get the fixed parts of the AMF body
        #       (only applicable to command messages for now). What did I mean by this?
        # DONE: AMF body format attributes (.body_if_amf) if the message received was a command (RPC).
        # Allow the recognition as whether the encoded/decoded was/is AMF (plainly or from a Shared Object).
        # This can only be used once the packet has been initialised.
        self.body_is_amf = False
        # self.body_is_so = False

        # Incoming/outgoing packet descriptor to see if the packet came in from the server or if it is one we are
        # sending. This should be labelled by RtmpReader or the RtmpWriter before/after reading or writing.
        self.incoming = False
        self.outgoing = False

        # Handled descriptor to see if the packet was handled by default (otherwise it was not).
        self.handled = False

    # DONE: A 'get_type' method should also be added.
    # DONE: Abstract all the essential header variables that we can set e.g. data (message) type, body, timestamp.
    # Packet attribute convenience methods:
    def get_chunk_stream_id(self):
        """
        A convenience method to allow the message chunk stream id to be retrieved without having to
        point to the RtmpHeader directly.

        :return header.chunk_stream_id:
        """
        return self.header.chunk_stream_id

    def get_timestamp(self):
        """
        A convenience method to allow the message timestamp to be retrieved without having to
        point to the RtmpHeader directly.

        :return header.timestamp:
        """
        return self.header.timestamp

    def get_body_length(self):
        """
        A convenience method to allow the message body length from the body buffer without having to
        point to the packet directly.

        :return len(body_buffer):
        """
        return len(self.body_buffer)

    def get_type(self):
        """
        A convenience method to allow the message data-type to be retrieved without having to
        point to the RtmpHeader directly.

        :return header.data_type:
        """
        return self.header.data_type

    def get_stream_id(self):
        """
        A convenience method to allow the message stream id to be retrieved without having to
        point to the RtmpHeader directly.

        :return header.stream_id:
        """
        return self.header.stream_id

    def set_chunk_stream_id(self, new_chunk_stream_id):
        """
        A convenience method to allow the message chunk stream id to be set without having to
        point to the RtmpHeader initially.

        :param new_chunk_stream_id:
        """
        self.header.chunk_stream_id = new_chunk_stream_id

    # DONE: Should we have a convenience method for setting the timestamp; we handle
    #       the timestamp delta and an absolute timestamp in this case by treating them as the same,
    #       they can be interpreted as an absolute timestamp or delta when writing into the stream with the
    #       chunk type/mask.
    def set_timestamp(self, new_timestamp):
        """
        A convenience method ot allow the message timestamp to be set without having to
        point to the RtmpPacket header initially.

        :param new_timestamp:
        """
        self.header.timestamp = new_timestamp

    def set_type(self, new_data_type):
        """
        A convenience method to allow the message data type to be set without having to
        point to the RtmpPacket header initially.

        :param new_data_type:
        """
        self.header.data_type = new_data_type

    def set_stream_id(self, new_stream_id):
        """
        A convenience method to allow the message stream id to be set without having to
        point to the RtmpPacket header initially.

        :param new_stream_id:
        """
        self.header.stream_id = new_stream_id

    # AMF-specific convenience methods:
    def get_command_name(self):
        """
        Returns the command name received from the server if the message was a COMMAND
        data-type and the body was AMF formatted.

        :return body['command_name']: str the command name from the COMMAND response or None if it's not present.
        """
        if self.body_is_amf and 'command_name' in self.body:
            return self.body['command_name']
        else:
            return None

    def get_transaction_id(self):
        """
        Returns the transaction id received from the server if the message was a COMMAND
        data-type and the body was AMF formatted.

        :return body['transaction_id']: int the transaction id of the message or None if it's not present.
        """
        if self.body_is_amf and 'transaction_id' in self.body:
            return int(self.body['transaction_id'])
        else:
            return None

    def get_command_object(self):
        """
        Returns the command object received from the server if the message was a COMMAND
        data-type and the body was AMF formatted.

        :return body['command_object']: list the command object retrieved from the message or None if it's not present.
        """
        if self.body_is_amf and 'command_object' in self.body:
            return self.body['command_object']
        else:
            return None

    def get_response(self):
        """
        Returns the response received from the server if the message was a COMMAND data-type
        and the body was AMF formatted.

        :return body['response']: list the response parsed from the AMF-encoded message or None if it's not present.
        """
        if self.body_is_amf and 'response' in self.body:
            return self.body['response']
        else:
            return None

    # DONE: Make a raw body contents function to get all the body content in a list. Like previously to use iparam.
    def get_body(self):
        """
        Returns a list of how the RTMP packet's body would be without sorting it.

        :return rtmp_body: list the RTMP packet's body.
        """
        if self.body_is_amf and self.header.data_type == types.DT_COMMAND:
            # TODO: Should we iterate over the command_object?
            # Generate a list of the command name, transaction id and the command object.
            rtmp_body = list((
                self.body['command_name'],
                self.body['transaction_id'],
                self.body['command_object'],
            ))

            # Iterate all the contents of the response as it would appear in the packet.
            if 'response' in self.body:
                for data in range(len(self.body['response'])):
                    rtmp_body.append(self.body['response'][data])

            return rtmp_body
        else:
            return self.body

    # Handler convenience methods.
    def free_body(self):
        """ 'Free' (clear) the body content of the packet. """
        self.body = None

    # DONE: 'setup_packet' -> '.setup()' which will give the packet ready to be sent but also allow the user
    #       to view the packet which has been set up.
    # def setup_packet(self, write_packet):
    def setup(self):
        """
        Setup an RtmpPacket with specified parameters to encode/write into the RTMP stream.

        INFO: Sets up a default RtmpPacket to use along with it's PyAMF Buffered Byte-stream body.
              If a preset packet is already provided we can just process that without creating a new one;
              the data-type must be specified in the packet header and the body SHOULD NOT contain any data already
              (any data present will be overwritten by the initialisation of the PyAMF Buffered Bytestream.
        """
        # Set up the encoder and body buffer which is to be assigned to the RtmpPacket once
        # data has been written into it.
        temp_buffer = pyamf.util.BufferedByteStream()

        if self.header.data_type == types.DT_SET_CHUNK_SIZE:
            # NOTE: RtmpHeader.ChunkType.TYPE_1_RELATIVE_LARGE, ChunkStreamInfo.CONTROL_CHANNEL,
            #       RtmpHeader.MessageType.SET_CHUNK_SIZE

            # Set up the basic header information.
            self.header.chunk_stream_id = types.RTMP_CONTROL_CHUNK_STREAM
            self.header.stream_id = 0

            # Set up the body content.
            temp_buffer.write_long(self.body['chunk_size'])

        elif self.header.data_type == types.DT_ACKNOWLEDGEMENT:
            # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.CONTROL_CHANNEL,
            #       RtmpHeader.MessageType.ACKNOWLEDGEMENT

            # Set up the basic header information.
            self.header.chunk_stream_id = types.RTMP_CONTROL_CHUNK_STREAM
            self.header.stream_id = 0

            # Set up the body content.
            temp_buffer.write_ulong(self.body['sequence_number'])

        elif self.header.data_type == types.DT_ABORT:
            # NOTE: RtmpHeader.ChunkType.TYPE_1_RELATIVE_LARGE, ChunkStreamInfo.CONTROL_CHANNEL,
            #       RtmpHeader.MessageType.ABORT

            # Set up the basic header information.
            self.header.chunk_stream_id = types.RTMP_CONTROL_CHUNK_STREAM
            self.header.stream_id = 0

            # Set up the body content.
            temp_buffer.write_ulong(self.body['chunk_stream_id'])

        elif self.header.data_type == types.DT_USER_CONTROL:
            # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.RTMP_CONTROL_CHANNEL,
            #       RtmpHeader.MessageType.USER_CONTROL_MESSAGE

            # Set up the basic header information.
            self.header.chunk_stream_id = types.RTMP_CONTROL_CHUNK_STREAM
            self.header.stream_id = 0

            # Set up the body content.
            # DONE: Event data itself may not be stated in pcap files, however it is after the event type.
            #       Make sure we have the event type or event data to send.
            if 'event_type' in self.body:
                temp_buffer.write_ushort(self.body['event_type'])
            if 'event_data' in self.body:
                temp_buffer.write(self.body['event_data'])

        elif self.header.data_type == types.DT_WINDOW_ACKNOWLEDGEMENT_SIZE:
            # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.CONTROL_CHANNEL,
            #       RtmpHeader.MessageType.WINDOW_ACKNOWLEDGEMENT_SIZE

            # Set up the basic header information.
            self.header.chunk_stream_id = types.RTMP_CONTROL_CHUNK_STREAM
            self.header.stream_id = 0

            # Set up the body content.
            temp_buffer.write_ulong(self.body['window_acknowledgement_size'])

        elif self.header.data_type == types.DT_SET_PEER_BANDWIDTH:
            # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.CONTROL_CHANNEL,
            #       RtmpHeader.MessageType.WINDOW_ACKNOWLEDGEMENT_SIZE

            # Set up the basic header information.
            self.header.chunk_stream_id = types.RTMP_CONTROL_CHUNK_STREAM
            self.header.stream_id = 0

            # Set up the body content.
            temp_buffer.write_ulong(self.body['window_acknowledgement_size'])
            temp_buffer.write_uchar(self.body['limit_type'])

        elif self.header.data_type == types.DT_AUDIO_MESSAGE:

            # TODO: These two attributes should be decided by the NetStream class.
            # Set up the basic header information.
            # TODO: Connect to NetStream chunk stream id attribute?
            self.header.chunk_stream_id = types.RTMP_CUSTOM_AUDIO_CHUNK_STREAM

            # TODO: Connect to NetStream stream id attribute?
            self.header.stream_id = 1

            # Set up the body buffer content.
            temp_buffer.write_uchar(self.body['control'])
            temp_buffer.write(self.body['audio_data'])

        elif self.header.data_type == types.DT_VIDEO_MESSAGE:

            # TODO: These two attributes should be decided by the NetStream class.
            # Set up the basic header information.
            # TODO: Connect to NetStream chunk stream id attribute?
            self.header.chunk_stream_id = types.RTMP_CUSTOM_VIDEO_CHUNK_STREAM

            # TODO: Connect to NetStream stream id attribute?
            self.header.stream_id = 1

            # Set up the body buffer content.
            temp_buffer.write_uchar(self.body['control'])
            temp_buffer.write(self.body['video_data'])

        elif self.header.data_type == types.DT_AMF3_COMMAND:
            # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.RTMP_COMMAND_CHANNEL,
            #       RtmpHeader.MessageType.COMMAND_AMF0

            # Set up the basic header information.
            self.header.chunk_stream_id = types.RTMP_CONNECTION_CHUNK_STREAM

            # Set up the body content.
            encoder = pyamf.amf3.Encoder(temp_buffer)
            # for command in write_packet.body['command']:
            #     encoder.writeElement(command)

            # Write the command name and transaction id, followed by an iteration over the
            # command object to write the AMF elements.
            encoder.writeElement(self.body['command_name'])
            encoder.writeElement(self.body['transaction_id'])
            encoder.writeElement(self.body['command_object'])
            for parameter in self.body['options']:
                encoder.writeElement(parameter)

            # The body we encoded was AMF formatted.
            self.body_is_amf = True

        # TODO: Work out how all this data should be iterated and written into the buffer.
        # elif self.header.data_type == types.DT_DATA_MESSAGE:
        #     # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.RTMP_COMMAND_CHANNEL,
        #     #       RtmpHeader.MessageType.DATA_AMF0
        #
        #     # Set up the basic header information.
        #     self.header.chunk_stream_id = types.RTMP_CONNECTION_CHUNK_STREAM
        #
        #     encoder = pyamf.amf0.Encoder(temp_buffer)
        #     # Set up the body content.
        #     encoder.writeElement(self.body['onMetaData'])
        #     """
        #     ('Packet:', {'data_content': [
        #         {'videoframerate': 24, 'moovposition': 8671904, 'avclevel': 30, 'avcprofile': 66,
        #          'audiosamplerate': 12000, 'audiocodecid': u'mp4a', 'framerate': 24, 'height': 160, 'width': 240,
        #          'displayWidth': 240, 'audiochannels': 2, 'frameHeight': 160, 'frameWidth': 240, 'duration': 596.48,
        #          'displayHeight': 160, 'aacaot': 2, 'videocodecid': u'avc1', 'trackinfo': [
        #             {'length': 14315, 'language': u'eng', 'timescale': 24,
        #              'sampledescription': [{'sampletype': u'avc1'}]},
        #             {'length': 7157760, 'language': u'eng', 'timescale': 12000,
        #              'sampledescription': [{'sampletype': u'mp4a'}]}]}], 'data_name': u'onMetaData'})
        #     """
        #     encoder.writeMixedArray(self.body['metadata'])

        # TODO: How do we include shared objects?
        # elif write_packet.header.data_type == types.DT_SHARED_OBJECT:
        #
        #     # Set up the basic header information.
        #     self.header.chunk_stream_id = types.RTMP_CONNECTION_CHUNK_STREAM
        #
        #     # Set up the body content.
        #     encoder = pyamf.amf0.Encoder(temp_buffer)
        #     encoder.serialiseString(self.body['obj_name'])
        #     temp_buffer.write_ulong(self.body['curr_version'])
        #     temp_buffer.write(self.body['flags'])
        #
        #     for event in self.body['events']:
        #         self.write_shared_object_event(event, temp_buffer)
        #
        #     # The body we encoded was a Shared Object.
        #     self.body_is_so = True

        # TODO: Is it possible to remove the list, so we can freely add various data structures to the command_object
        #       or options fields without having to place it inside a list all the time
        #       (or would it remove it's iterable feature)?
        elif self.header.data_type == types.DT_COMMAND:
            # NOTE: RtmpHeader.ChunkType.TYPE_0_FULL, ChunkStreamInfo.RTMP_COMMAND_CHANNEL,
            #       RtmpHeader.MessageType.COMMAND_AMF0

            # Set up the basic header information.
            self.header.chunk_stream_id = types.RTMP_CONNECTION_CHUNK_STREAM

            # Set up the body content.
            encoder = pyamf.amf0.Encoder(temp_buffer)
            # for command in write_packet.body['command']:
            #     encoder.writeElement(command)

            # Write the command name and transaction id, followed by an iteration over the
            # command object to write the AMF elements.
            encoder.writeElement(self.body['command_name'])
            encoder.writeElement(self.body['transaction_id'])
            # TODO: Iteration over the command object would be an issue here (in the event of the connection packet,
            #       maybe we should handle all formats and assume the command object is going to be used anyhow).
            command_object = self.body['command_object']
            if type(command_object) is list:
                for command_info in command_object:
                    encoder.writeElement(command_info)
            else:
                # TODO: Allow types which are not iterable to be written on it's own into the stream.
                encoder.writeElement(command_object)

            options = self.body['options']
            if type(options) is list:
                for parameter in options:
                    encoder.writeElement(parameter)

            # DONE: Converted stream information handling into types and to RtmpPacket.

            # The body we encoded was AMF formatted.
            self.body_is_amf = True

        else:
            return None

        # If the timestamp has still not been established by this point,
        # we set it to default (zero).
        if self.header.timestamp is -1:
            self.header.timestamp = 0

        # Assign the buffered bytestream body value into the RtmpPacket.
        self.body_buffer = temp_buffer.getvalue()

        # If the body buffer was made then we can get the length of it.
        if self.body_buffer is not None:
            self.header.body_length = len(self.body_buffer)

    # DONE: 'reset_packet' -> '.reset()'.
    # def reset_packet(self):
    def reset(self):
        """ Resets the packet's contents to the original form with an invalid header and body. """
        self.header = rtmp_header.RtmpHeader(-1)
        self.body = None
        self.body_buffer = None

    # DONE: If we print() or log() with string formatting we are unable to use '__repr__'.
    # TODO: Make it clear if the packet was incoming or outgoing?
    def __repr__(self):
        """
        Return a printable representation of the contents of the header of the RtmpPacket.

        :return repr: str printable representation of the header's attributes.
        """
        return '<RtmpPacket.header> chunk_type=%s chunk_stream_id=%s timestamp=%s body_length=%s ' \
               'data_type=%s stream_id=%s extended_timestamp=%s (timestamp_delta=%s, timestamp_absolute=%s) ' \
               '<handled:%s>' % \
               (self.header.chunk_type, self.header.chunk_stream_id, self.header.timestamp,
                self.header.body_length, self.header.data_type, self.header.stream_id,
                self.header.extended_timestamp, self.header.timestamp_delta, self.header.timestamp_absolute,
                self.handled)
