import time


class HandshakeChunk(object):
    """
    An RTMP handshake chunk.

    @ivar first: The first 4 bytes of the packet, represented as an unsigned long.
    @type first: 32bit unsigned int.
    @ivar second: The second 4 bytes of the packet, represented as an unsigned long.
    @type second: 32bit unsigned int.
    @ivar payload: A blob of data which makes up the rest of the packet.
                   This must be C{handshake_length} - 8 bytes in length.
    @type payload: C{str}
    @ivar timestamp: Timestamp that this packet was created (in milliseconds).
    @type timestamp: C{int}
    """
    # The handshake length.
    handshake_length = 1536

    # Initialise packet content.
    first = None
    second = None
    payload = None
    timestamp = None

    def __init__(self, **kwargs):
        """

        :param kwargs:
        """
        timestamp = kwargs.get('timestamp', None)

        if timestamp is None:
            kwargs['timestamp'] = int(time.time())

        self.__dict__.update(kwargs)

    def encode(self, rtmp_stream):
        """
        Encodes this packet to the RTMP stream.

        :param rtmp_stream:
        """
        # Write the first and second data into the stream.
        rtmp_stream.write_ulong(self.first or 0)
        rtmp_stream.write_ulong(self.second or 0)

        # Write the payload into the stream.
        rtmp_stream.write(self.payload)

    def decode(self, rtmp_stream):
        """
        Decodes this packet from the RTMP stream.

        :param rtmp_stream:
        """
        # Read the first and second data from the stream buffer.
        self.first = rtmp_stream.read_ulong()
        self.second = rtmp_stream.read_ulong()

        # Read the message payload from the stream buffer given the handshake length.
        self.payload = rtmp_stream.read(self.handshake_length - 8)
