""" Defines the handshake object for use in an RTMP Handshake before the connection. """

import time


class HandshakeChunk(object):
    """ Handshake object representing a chunk.
    
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
    _handshake_length = 1536

    first = None
    second = None
    payload = None
    timestamp = None

    def __init__(self, **kwargs):
        """
        Initialise the handshake chunk object.
        
        :param kwargs:
        """
        timestamp = kwargs.get('timestamp', None)

        if timestamp is None:
            kwargs['timestamp'] = int(time.time())

        self.__dict__.update(kwargs)

    def encode(self, rtmp_stream):
        """
        Encodes packet to the RTMP stream.
        
        :param rtmp_stream:
        :type rtmp_stream:
        """
        rtmp_stream.write_ulong(self.first or 0)
        rtmp_stream.write_ulong(self.second or 0)
        rtmp_stream.write(self.payload)

    def decode(self, rtmp_stream):
        """
        Decodes packet from the RTMP stream.
        
        :param rtmp_stream:
        :type rtmp_stream:
        """
        self.first = rtmp_stream.read_ulong()
        self.second = rtmp_stream.read_ulong()
        self.payload = rtmp_stream.read(self._handshake_length - 8)
