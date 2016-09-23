""" Classes relevant to the basic packet structure, including packet header's and body. """

import time
import rtmp_protocol_header

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


class RtmpPacket(object):
    """ A class to abstract the RTMP packets (received) which consists of an RTMP header and an RTMP body. """

    # Set up a packet blank header.
    header = rtmp_protocol_header.Header(-1)
    # Set up a packet blank body.
    body = None

    def __init__(self, header=None, body=None):
        """
        Initialise the packet by providing the decoded header and the decoded body.
        NOTE: The packet can be initialised without providing a header or body, however, in order to use this packet
              you must eventually assign the RTMP header and body.

              If you initialise without these two a default header with a chunk_stream_id of -1 will be used with
              no packet body. In this case, you MUST NOT use the packet for encoding/decoding to/from the RTMP stream.

        :param header: L{Header} decoded header from the rtmp stream.
        :param body: dict the body of the rtmp packet, with the contents stored in a dictionary.
        """
        # Handle the packet header.
        if header is not None:
            self.header.format = header.format
            self.header.chunk_stream_id = header.chunk_stream_id

            self.header.timestamp = header.timestamp
            self.header.body_length = header.body_length
            self.header.data_type = header.data_type
            self.header.stream_id = header.stream_id
            self.header.extended_timestamp = header.extended_timestamp

        # Handle the packet body.
        if body is not None:
            self.body = body

    def __repr__(self):
        """
        Return a printable representation of the contents of the header of the RTMPPacket.
        NOTE: We do not return a representation in the event that the packet was initialised plainly,
              with no RTMP header.

        :return: printable representation of header attributes.
        """
        if self.header.format is not -1:
            return '<RTMPPacket.header> format=%s chunk_stream_id=%s timestamp=%s body_length=%s ' \
                   'data_type=%s stream_id=%s extended_timestamp=%s' % \
                   (self.header.format, self.header.chunk_stream_id, self.header.timestamp, self.header.body_length,
                    self.header.data_type, self.header.stream_id, self.header.extended_timestamp)

