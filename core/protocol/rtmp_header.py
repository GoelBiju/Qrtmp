"""
Initial source code taken from rtmpy project (http://rtmpy.org/)

It seems as the above url is broken, so provided below are the the links to the rtmpy project on GitHub
(https://github.com/hydralabs/rtmpy):

handshake.py - https://github.com/hydralabs/rtmpy/blob/master/rtmpy/protocol/handshake.py
rtmp_header.py - https://github.com/hydralabs/rtmpy/blob/master/rtmpy/protocol/rtmp/rtmp_header.py
"""

import logging

from core.protocol.types import enum_rtmp_header

log = logging.getLogger(__name__)


class HeaderError(Exception):
    """ Raised if a header related operation failed. """
    pass


class RtmpHeader(object):
    """
    An RTMP Header which holds contextual information regarding an RTMP Channel,
    along with the information regarding the payload it will be carrying.
    """
    __slots__ = ['chunk_type', 'chunk_stream_id', 'data_type', 'body_length', 'stream_id',
                 'absolute_timestamp', 'timestamp_delta', 'extended_timestamp']

    def __init__(self, chunk_stream_id, absolute_timestamp=-1, body_length=-1, data_type=-1, stream_id=-1):
        """
        
        :param chunk_stream_id:
        :param absolute_timestamp:
        :param body_length:
        :param data_type:
        :param stream_id:
        """
        self.chunk_type = -1
        self.chunk_stream_id = int(chunk_stream_id)
        self.data_type = int(data_type)
        self.body_length = int(body_length)
        self.stream_id = int(stream_id)

        # TODO: Replace one common timestamp attribute with two attributes:
        #       absolute timestamp and a timestamp delta.
        # self.timestamp = int(timestamp)
        self.absolute_timestamp = int(absolute_timestamp)
        self.timestamp_delta = -1

        # TODO: Is this applicable and does this relate to the absolute timestamp
        #       or the timestamp delta?
        self.extended_timestamp = -1

        # TODO: State if the header's timestamp includes an absolute timestamp or
        #       a timestamp delta.
        # self.has_absolute_timestamp = False
        # self.has_timestamp_delta = False

    def __repr__(self):
        """
        Return a string representation of the attributes of the header.
        
        :return str: printable representation of the header's attributes.
        """
        attributes = []

        for k in self.__slots__:
            v = getattr(self, k, None)
            if v is -1:
                v = None
            attributes.append('%s=%r' % (k, v))

        return '<%s.%s %s at 0x%x>' % (
         self.__class__.__module__,
         self.__class__.__name__,
         ' '.join(attributes),
         id(self))


# TODO: Implement chunk stream channels for the correct header to be read.
class RtmpHeaderHandler:

    def __init__(self, rtmp_stream):
        """

        :param rtmp_stream:
        @type rtmp_stream: L{pyamf.util.BufferedByteStream}.
        """
        self._rtmp_stream = rtmp_stream

        # A dictionary with each key being a present chunk-stream id
        # to keep data relevant on each header that is received.
        self._prev_received_headers = {}

        # TODO: Implement previously sent headers to help with choosing
        #       what chunk type to send the next header with.
        # self._prev_sent_headers = {}

    def encode_into_stream(self, encode_header, previous=None):
        """
        Encodes an RTMP header to C{stream}.
        
        NOTE: We expect the stream to already be in network endian mode.
              The chunk stream id can be encoded in up to 3 bytes.
              The first byte is special as it contains the size of the rest of the header as described in
               L{get_chunk_type}.
        
        0 >= chunk_stream_id > 64: chunk_stream_id
        64 >= chunk_stream_id > 320: 0 chunk_stream_id - 64
        320 >= chunk_stream_id > 0xffff + 64: 1, chunk_stream_id - 64 (written as 2 byte int)
        
        Chunk stream type: | Mask type:
        ------------------   ----------
               0           =    0x00 (0)
               1           =    0x40 (64)
               2           =    0x80 (128)
               3           =    0xc0 (192)
        
        NOTE: We keep on altering the value of the header's format until we recognise
              which header format it truly is.
        
        NOTE: When we use the previous header from the previous parameter, this is only to be used to
              to compare messages in which it's body has been split into chunks.
        
        :param encode_header: The header to encode into the RTMP stream.
        @type encode_header: L{RtmpHeader}
        :param previous:
        @type previous:
        """
        chunk_stream_id = encode_header.chunk_stream_id

        if previous is None:
            mask = 0
        else:
            mask = self._get_header_mask(encode_header, previous)
        print('Encoding mask:', mask)

        if chunk_stream_id < 64:
            self._rtmp_stream.write_uchar(mask | chunk_stream_id)
        else:
            if chunk_stream_id < 320:
                self._rtmp_stream.write_uchar(mask)
                self._rtmp_stream.write_uchar(chunk_stream_id - 64)
            else:
                chunk_stream_id -= 64
                self._rtmp_stream.write_uchar(mask + 1)
                self._rtmp_stream.write_uchar(chunk_stream_id & 255)
                self._rtmp_stream.write_uchar(chunk_stream_id >> 8)

        if mask == 192:
            print('Encoded continuation header: ', encode_header)
            return

        if mask == 128:
            if encode_header.absolute_timestamp >= 16777215:
                self._rtmp_stream.write_24bit_uint(16777215)
            else:
                self._rtmp_stream.write_24bit_uint(encode_header.timestamp)

            encode_header.timestamp_delta = True

        elif mask == 64:
            if encode_header.absolute_timestamp >= 16777215:
                self._rtmp_stream.write_24bit_uint(16777215)
            else:
                self._rtmp_stream.write_24bit_uint(encode_header.absolute_timestamp)

            self._rtmp_stream.write_24bit_uint(encode_header.body_length)

            self._rtmp_stream.write_uchar(encode_header.data_type)

            # encode_header.timestamp_delta = True

        elif mask == 0:
            if encode_header.absolute_timestamp >= 16777215:
                self._rtmp_stream.write_24bit_uint(16777215)
            else:
                self._rtmp_stream.write_24bit_uint(encode_header.absolute_timestamp)

            self._rtmp_stream.write_24bit_uint(encode_header.body_length)
            self._rtmp_stream.write_uchar(encode_header.data_type)
            self._rtmp_stream.endian = '<'
            self._rtmp_stream.write_ulong(encode_header.stream_id)
            self._rtmp_stream.endian = '!'
            # encode_header.timestamp_absolute = True

        if encode_header.absolute_timestamp >= 16777215:
            self._rtmp_stream.write_ulong(encode_header.absolute_timestamp)

            encode_header.extended_timestamp = encode_header.absolute_timestamp
        else:
            encode_header.extended_timestamp = None

        print('Header encoded:', repr(encode_header))

    def decode_from_stream(self):
        """
        Reads a header from the incoming stream.
        
        NOTE: A header can be of varying lengths and the properties that
              gets updated depend on its length.
        
        :return decoded_header: The read header from the RTMP stream.
        @rtype: L{RtmpHeader}
        """
        header_size = self._rtmp_stream.read_uchar()
        # Ord returns the unicode code point of the 1 length string we give it to read.
        # header_size = ord(self._rtmp_stream._read(1))
        # TODO: Use for window acknowledgement total bytes read.
        # print('Header size: ', header_size)

        chunk_type = header_size >> 6
        # chunk_type = header_size & 192  # or header size & 0xC0 (192)
        # chunk_stream_id &= 63
        chunk_stream_id = header_size & 63  # (0x3F)

        if chunk_stream_id == 0:
            chunk_stream_id = self._rtmp_stream.read_uchar() + 64
        if chunk_stream_id == 1:
            chunk_stream_id = self._rtmp_stream.read_uchar() + 64 + (self._rtmp_stream.read_uchar() << 8)

        # Create the header to decode fully using the chunk stream id we have decoded.
        decoded_header = RtmpHeader(chunk_stream_id)
        decoded_header.chunk_type = chunk_type

        # TODO: Fix audio/video and aggregate packets by adding the timestamp delta from a chunk-type of 1, 2
        #       to the absolute timestamp received from a chunk-type of 0.
        if chunk_type == enum_rtmp_header.HR_TYPE_3_CONTINUATION:
            # print('Decoded header:', repr(decoded_header))

            # Handle red5 server ping request which has defines no data-type and
            # is sent as a continuation header.
            # if chunk_stream_id == enum_rtmp_header.CS_CONTROL:
            #     decoded_header.data_type = 4
            #     decoded_header.body_length = 6

            # TODO: According to rtmp2flv, contrary to the RTMP specification, the extended timestamp may also
            # be present in an continuation header.
            # if decoded_header.timestamp == 16777215:
            #     decoded_header.extended_timestamp = self._rtmp_stream.read_ulong()
            # else:
            #     decoded_header.extended_timestamp = None

            if chunk_stream_id in self._prev_received_headers:
                previous_header = self._prev_received_headers[chunk_stream_id]

                decoded_header.timestamp_delta = previous_header.timestamp_delta
                decoded_header.absolute_timestamp = previous_header.absolute_timestamp + decoded_header.timestamp_delta
                decoded_header.body_length = previous_header.body_length
                decoded_header.data_type = previous_header.data_type
                decoded_header.stream_id = previous_header.stream_id

            return decoded_header

        if chunk_type == enum_rtmp_header.HR_TYPE_2_SAME_LENGTH_AND_STREAM:
            # TODO: Timestamp delta only.
            # decoded_header.timestamp = self._rtmp_stream.read_24bit_uint()
            decoded_header.timestamp_delta = self._rtmp_stream.read_24bit_uint()

            if chunk_stream_id in self._prev_received_headers:
                previous_header = self._prev_received_headers[chunk_stream_id]

                decoded_header.body_length = previous_header.body_length
                decoded_header.stream_id = previous_header.stream_id
                decoded_header.absolute_timestamp = previous_header.absolute_timestamp + decoded_header.timestamp_delta

            # decoded_header.timestamp_delta = True

        elif chunk_type == enum_rtmp_header.HR_TYPE_1_SAME_STREAM:
            # TODO: Timestamp delta only.
            # decoded_header.timestamp = self._rtmp_stream.read_24bit_uint()
            decoded_header.timestamp_delta = self._rtmp_stream.read_24bit_uint()

            # Body length.
            decoded_header.body_length = self._rtmp_stream.read_24bit_uint()

            # Message type.
            decoded_header.data_type = self._rtmp_stream.read_uchar()

            # Use the previous header from the chunk stream to create
            # the missing header information.
            if chunk_stream_id in self._prev_received_headers:
                previous_header = self._prev_received_headers[chunk_stream_id]

                decoded_header.stream_id = previous_header.stream_id
                decoded_header.absolute_timestamp = previous_header.absolute_timestamp + decoded_header.timestamp_delta
            else:
                decoded_header.stream_id = 0
                decoded_header.absolute_timestamp = decoded_header.timestamp_delta

            # decoded_header.timestamp_delta = True

        elif chunk_type == enum_rtmp_header.HR_TYPE_0_FULL:
            # TODO: Absolute timestamp received. No timestamp delta.
            # decoded_header.timestamp = self._rtmp_stream.read_24bit_uint()
            decoded_header.absolute_timestamp = self._rtmp_stream.read_24bit_uint()
            decoded_header.timestamp_delta = 0

            # Length of message.
            decoded_header.body_length = self._rtmp_stream.read_24bit_uint()

            # Message type.
            decoded_header.data_type = self._rtmp_stream.read_uchar()

            # Message stream id in little-endian order.
            # TODO: Find out what is little-endian/endian order.
            self._rtmp_stream.endian = '<'
            decoded_header.stream_id = self._rtmp_stream.read_ulong()
            self._rtmp_stream.endian = '!'

            # State we have received an absolute timestamp.
            # decoded_header.timestamp_absolute = True

        if decoded_header.absolute_timestamp == 16777215 or decoded_header.timestamp_delta == 16777215:
            decoded_header.extended_timestamp = self._rtmp_stream.read_ulong()
        else:
            decoded_header.extended_timestamp = None

        # Before we return the decoded header, store it in the correct chunk stream's previous headers.
        self._prev_received_headers[chunk_stream_id] = decoded_header

        # print('Decoded header:', repr(decoded_header))
        return decoded_header

    @staticmethod
    def _get_header_mask(latest_full_header, header_to_encode):
        """
        Returns the number of bytes needed to encode the header based on the differences between the two.

        NOTE: Both headers must be from the same chunk stream in order for this to work.
              By comparing the size of the header we need to encode into the stream, we can reduce overhead in formats
              by only writing the necessary parts of the header.

        :param latest_full_header: the last full header that we received in this chunk stream.
        @type latest_full_header: L{RtmpHeader}
        :param header_to_encode: the header we need to encode into the RTMP stream.
        @type header_to_encode: L{RtmpHeader}
        """
        if latest_full_header.chunk_stream_id == header_to_encode.chunk_stream_id:

            if latest_full_header is header_to_encode:
                return 192

            if latest_full_header.stream_id != header_to_encode.stream_id:
                return 0

            if latest_full_header.data_type == header_to_encode.data_type and \
                    latest_full_header.body_length == header_to_encode.body_length:

                if latest_full_header.absolute_timestamp == header_to_encode.absolute_timestamp:
                    return 192
                return 128
            return 64
