""" Classes relevant to the basic RTMP packet structure; the packet header and body. """

import time

from rtmp.core import rtmp_header
# from rtmp.util import types

# The handshake length.
HANDSHAKE_LENGTH = 1536


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

    def __init__(self, **kwargs):
        timestamp = kwargs.get('timestamp', None)

        if timestamp is None:
            kwargs['timestamp'] = int(time.time())

        self.__dict__.update(kwargs)

    def encode(self, stream_buffer):
        """ Encodes this packet to a stream. """
        # Write the first and second data into the stream.
        stream_buffer.write_ulong(self.first or 0)
        stream_buffer.write_ulong(self.second or 0)

        # Write the payload into the stream.
        stream_buffer.write(self.payload)

    def decode(self, stream_buffer):
        """ Decodes this packet from a stream. """
        # Read the first and second data from the stream buffer.
        self.first = stream_buffer.read_ulong()
        self.second = stream_buffer.read_ulong()

        # Read the message payload from the stream buffer.
        self.payload = stream_buffer.read(HANDSHAKE_LENGTH - 8)


# TODO: Any other essential packet methods?
class RtmpPacket(object):
    """ A class to abstract the RTMP packets (received) which consists of an RTMP header and an RTMP body. """

    # Set up a packet blank header.
    header = rtmp_header.Header(-1)
    # Set up a packet blank body.
    body = None

    # Set up body descriptors.
    body_is_amf = None
    body_is_so = None

    def __init__(self, header=None, body=None):
        """
        Initialise the packet by providing the header information and body data.
        NOTE: The packet can be initialised without providing a header or a body, however, in order to use this packet,
              you must eventually assign the correct RTMP header and body.

              If you initialise the packet without these two, a default header with a chunk_stream_id value of -1
              will be used to encode/decode (with no packet body).

              In this case, you MUST NOT use the packet for encoding/decoding to/from the RTMP stream.

        :param header: L{Header} header with the appropriate values.
        :param body: dict the body of the rtmp packet, with each key being a section of the RTMP packet.
        """
        # Handle the packet header.
        if header is not None:
            # self.header.format = header.format
            self.header.chunk_type = header.chunk_type  # _chunk_type?
            self.header.chunk_stream_id = header.chunk_stream_id

            self.header.timestamp = header.timestamp
            self.header.body_length = header.body_length
            self.header.data_type = header.data_type
            self.header.stream_id = header.stream_id
            self.header.extended_timestamp = header.extended_timestamp  # _extended_timestamp?

            self.timestamp_absolute = header.timestamp_absolute  # _timestamp_absolute?
            self.timestamp_delta = header.timestamp_delta  # _timestamp_delta?

        # Handle the packet body.
        if body is not None:
            self.body = body

        # TODO: Add convenience methods to get the fixed parts of the AMF body (only applicable to command messages
        #       for now).
        # TODO: Possibly have an AMF body format attributes (.body_amf/.is_amf?)
        #       if the message received was a command (RPC).
        # Allow the recognition as whether the encoded/decoded was/is AMF (plainly or from a Shared Object).
        # This can only be used once the packet has been initialised.
        self.body_is_amf = False
        self.body_is_so = False

    # TODO: A 'get_type' method should also be added.
    # TODO: Abstract all the essential header variables that we can set e.g. data (message) type, body.
    def set_type(self, data_type):
        """
        A convenience method to allow the message data type to be set without having to
        point to the RtmpPacket header initially.
        :param data_type:
        """
        self.header.data_type = data_type

    def set_stream_id(self, stream_id):
        """
        A convenience method to allow the message stream id to be set without having to
        point to the RtmpPacket header initially.
        :param stream_id:
        """
        self.header.stream_id = stream_id

    # TODO: Is the order of branches in this method correct?
    def finalise(self):
        """
        Allows the packet to be finalised once all the necessary information is present.
        NOTE: This is only to be called once the packet's header is ready to be encoded and
              written onto the stream. We will need the chunk_stream_id, data_type, body.
        """
        # If the timestamp has still not been established by this point, we set it to zero.
        if self.header.timestamp is -1:
            self.header.timestamp = 0

        # If the stream id has still not been established by this point, we will set it to be sent
        # on the RTMP connection channel.
        # if self.header.stream_id is -1:
        #     self.header.stream_id = types.RTMP_CONNECTION_CHANNEL

        if self.body is not None:
            self.header.body_length = len(self.body)

    def free_body(self):
        """ 'Free' (clear) the body content of the packet. """
        self.body = None

    def reset_packet(self):
        """ Resets the packet's contents to the original form with an invalid header and body. """
        self.header = rtmp_header.Header(-1)
        self.body = None

    def __repr__(self):
        """
        Return a printable representation of the contents of the header of the RTMPPacket.
        NOTE: We do not return a representation in the event that the packet was initialised plainly,
              with no RTMP header.

        :return: printable representation of header attributes.
        """
        # if self.header.format is not -1:
        if self.header.chunk_type is not -1:
            return '<RtmpPacket.header> chunk_type=%s chunk_stream_id=%s timestamp=%s body_length=%s ' \
                   'data_type=%s stream_id=%s extended_timestamp=%s (timestamp_absolute=%s timestamp_delta=%s)' % \
                   (self.header.chunk_type, self.header.chunk_stream_id, self.header.timestamp,
                    self.header.body_length, self.header.data_type, self.header.stream_id,
                    self.header.extended_timestamp, self.timestamp_absolute, self.timestamp_delta)
