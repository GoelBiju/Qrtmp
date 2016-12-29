# -*- coding: utf-8 -*-

"""
Initial source code taken from rtmpy project (http://rtmpy.org/)

It seems as the above url is broken, so provided below are the the links to the rtmpy project on GitHub
(https://github.com/hydralabs/rtmpy):

handshake.py - https://github.com/hydralabs/rtmpy/blob/master/rtmpy/protocol/handshake.py
rtmp_header.py - https://github.com/hydralabs/rtmpy/blob/master/rtmpy/protocol/rtmp/rtmp_header.py

This is an edited version of the old library developed by prekageo (rtmp-python -
https://github.com/prekageo/rtmp-python/) and mixed with edits by nortxort (pinylib -
https://github.com/nortxort/pinylib/). Along with the fixes required to form RTMP headers correctly.

GoelBiju (https://github.com/GoelBiju/)

"""

# import logging

from qrtmp.formats import types

# TODO: RECORD HEADER:
#       Possibly remove use of dictionary and since this will increase memory size, since we only
#       need the previous header, just store that separately.

# TODO: Video data has type/format 1 after initial frame with streamId on format 0.
#       Audio data, if same length then uses type 2, if the length changes then it can use type 3.
#       The chunk stream id for both video and audio data IS NOT the same - default video (6), audio (7).
#       The stream id on the first packet for both video and audio data should be the same, we can do not have to
#       send the stream_id afterwards.

# log = logging.getLogger(__name__)


# TODO: Make it more simpler to log and debug rtmp headers.


class HeaderError(Exception):
    """ Raised if a header related operation failed. """


# TODO: Handle packet header properties, e.g. the chunk_type and chunk stream id.
class RtmpHeader(object):
    """
    An RTMP Header which holds contextual information regarding an RTMP Channel,
    along with the information regarding the payload it will be carrying.
    """
    # DONE: Solved __slots__ read-only issue - moved structure of classes.
    # Initialise the only attributes we want the object to store.
    __slots__ = ('chunk_type', 'chunk_stream_id', 'timestamp',
                 'body_length', 'data_type', 'stream_id', 'extended_timestamp',
                 'timestamp_delta', 'timestamp_absolute')

    # TODO: Formatting of names: _chunk_type, _extended_timestamp, _timestamp_absolute or _timestamp_delta?
    def __init__(self, chunk_stream_id, timestamp=-1, body_length=-1, data_type=-1, stream_id=-1):
        """

        :param chunk_stream_id:
        :param timestamp:
        :param body_length:
        :param data_type:
        :param stream_id:
        """
        # TODO: Explicitly state the type of variable the header's attributes require when setting it,
        #       this will prevent any other type of variable being initialised instead of what we need.
        # NOTE: The header format (format) and the extended timestamp (extended_timestamp) ARE NOT to
        #       be set manually or at your own accord.

        # Header content:
        self.chunk_type = -1  # Non-manual - calculated.

        # DONE: Renamed channel_id to chunk_stream_id.
        self.chunk_stream_id = int(chunk_stream_id)  # Manual entry.

        self.timestamp = int(timestamp)  # Manual entry.

        self.body_length = int(body_length)  # Manual entry.

        self.data_type = int(data_type)  # Manual entry.

        self.stream_id = int(stream_id)  # Manual entry.

        # This is only used if the timestamp is too large to fit in the original.
        self.extended_timestamp = -1  # Non-manual - calculated.

        # TODO: Should we have a descriptor for the type of timestamp e.g. absolute or delta?
        # TODO: Added notice attribute to show if the timestamp received is an absolute.
        self.timestamp_absolute = False  # Non-manual - monitored.

        # TODO: Added notice attribute to show if the timestamp received is a delta.
        self.timestamp_delta = False  # Non-manual - monitored.

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


# TODO: This should be based on each header we decode. We need to create encoding rules as well.
# TODO: This does not function to it's full - it just keep on returning 0xc0 due to the same header being re-used.
# TODO: We need to make this work on a packet basis as well.
def get_size_mask(old_header, new_header):
    """
    Returns the number of bytes needed to encode the header based on the differences between the two.
    NOTE: Both headers must be from the same chunk stream in order for this to work.

    NOTE: By comparing the size we need to encode the header, we can reduce overhead in formats by only
          the necessary parts of the packet.

    @type old_header: L{Header}
    @type new_header: L{Header}
    """
    # If the header is not on the same chunk stream then we cannot get a mask.
    if old_header.chunk_stream_id != new_header.chunk_stream_id:
        raise HeaderError('chunk_stream_id mismatch on diff old=%r, new=%r' % (old_header, new_header))

    # If the header we just received and the header previous to it is identical,
    # then it is an RTMP message in chunks.
    # Return that size corresponds to a type 3 header.
    if old_header is new_header:
        return 0xc0  # 192
    else:
        # If the stream id are not the same, then this indicates the use of a Type 0 message. A message stream is
        # being used on the RTMP stream.
        if old_header.stream_id != new_header.stream_id:
            # Return that size corresponds to a type 0 header.
            return 0x00

        # If the previous header and the new headers message type id match and they have the same body size,
        # then send the chunk as Type 2, this saves space on the stream.
        # header.body_size, header.timestamp
        if old_header.data_type == new_header.data_type and old_header.body_length == new_header.body_length:
            # If the old header's timestamp and the new_header's timestamp match then send via Type 3,
            # we do not need to send a type 2 since the timestamp delta is the same.
            if old_header.timestamp == new_header.timestamp:
                # Return that size corresponds to a type 3 header.
                return 0xc0  # 192

            # If the body size is the same we can send via Type 2.
            # Return that size corresponds to a type 2 header.
            return 0x80  # 128

        # Return that size corresponds to a type 1 header.
        return 0x40  # 64


# TODO: The rtmp_stream object is not provided into this properly, so it becomes a NoneType.
# TODO: Can we not connect this up to the Header class?
def encode(rtmp_stream, header, previous=None):
    """
    Encodes an RTMP header to C{stream}.

    NOTE: We expect the stream to already be in network endian mode.
    The chunk stream id can be encoded in up to 3 bytes. The first byte is special as
    it contains the size of the rest of the header as described in L{getHeaderSize}.

    0 >= chunk_stream_id > 64: chunk_stream_id
    64 >= chunk_stream_id > 320: 0 chunk_stream_id - 64
    320 >= chunk_stream_id > 0xffff + 64: 1, chunk_stream_id - 64 (written as 2 byte int)

    Chunk Stream type: | Mask type:
    ------------------   ----------
           0           =    0x00
           1           =    0x40
           2           =    0x80
           3           =    0xc0

    NOTE: We keep on altering the value of the header's format until we recognise
          which header format it truly is.

    NOTE: When we use the previous header from the previous parameter, this is only to be used to
          to compare messages in which it's body has been split into chunks.

    @param rtmp_stream: The stream to write the encoded header.
    @type rtmp_stream: L{util.BufferedByteStream}.
    @param header: The L{Header} to encode.
    @param previous: The previous header (if any).
    """
    # TODO: Implement the use of previous headers here.
    if previous is None:
        mask = 0
    else:
        # TODO: Get mask procedure name.
        # TODO: We could use a continuation field here.
        # TODO: 'read_format' to 'mask' or 'header_mask'.
        mask = get_size_mask(previous, header)

    # Retrieve the channel id from the header's chunk_stream_id attribute.
    chunk_stream_id = header.chunk_stream_id

    # print('Previous header: %r HEADER TYPE: %s CHANNEL ID: %s' % (previous, mask, chunk_stream_id))

    if chunk_stream_id < 64:  # <= 63
        rtmp_stream.write_uchar(mask | chunk_stream_id)
    elif chunk_stream_id < 320:  # <=319
        rtmp_stream.write_uchar(mask)
        rtmp_stream.write_uchar(chunk_stream_id - 64)
    else:
        chunk_stream_id -= 64

        rtmp_stream.write_uchar(mask + 1)
        rtmp_stream.write_uchar(chunk_stream_id & 0xff)
        rtmp_stream.write_uchar(chunk_stream_id >> 0x08)

    # TODO: We should not be encoding depending on sections, we need to decode based on format - branching.
    # This is a Type 3 (0xC0) header, we do not need to write the stream id, message size or
    # timestamp delta since they are not present in this type of message.
    if mask == 0xc0:
        # TODO: Added format information in rtmp_header.encode.
        # Set header format to Type 3
        header.chunk_type = types.HEADER_TYPE_3_CONTINUATION
    else:
        # This applies to all header which is Type 2 (0x80) or smaller.
        # Write the timestamp, if it fits, elsewhere state we need an extended timestamp and write it later.
        # if mask <= 0x80:

        if mask == 0x80:
            # We only need to write the timestamp delta for this type of header.

            # Write the timestamp delta.
            # NOTE: If the timestamp delta is greater than or equal to the value 16777215,
            #       then we need to extend the timestamp with another field at the end of the header.
            if header.timestamp >= 0xffffff:
                rtmp_stream.write_24bit_uint(0xffffff)
            else:
                # Otherwise write the timestamp delta.
                rtmp_stream.write_24bit_uint(header.timestamp)

            # Set to state that we sent a timestamp delta,
            header.timestamp_delta = True

            # TODO: Added format information in rtmp_header.encode.
            # Set header format to Type 2.
            header.chunk_type = types.HEADER_TYPE_2_SAME_LENGTH_AND_STREAM

        # This applies to headers which are Type 1 (0x40) or smaller.
        # Write message length, followed by the message type id.
        # if mask <= 0x40:

        elif mask == 0x40:
            # We will need to write the timestamp delta, body length and data type
            # for this type of header.

            # Write the timestamp delta.
            # NOTE: See above branch for mask type 0x80.
            if header.timestamp >= 0xffffff:
                rtmp_stream.write_24bit_uint(0xffffff)
            else:
                # Otherwise write the timestamp delta.
                rtmp_stream.write_24bit_uint(header.timestamp)

            # Write the body length.
            rtmp_stream.write_24bit_uint(header.body_length)  # message length

            # Write the data type.
            rtmp_stream.write_uchar(header.data_type)  # message type id

            # Set to state that we are sending a timestamp delta.
            header.timestamp_delta = True

            # TODO: Added format information in rtmp_header.encode.
            # Set header format to Type 1.
            header.chunk_type = types.HEADER_TYPE_1_SAME_STREAM

        # This applies if the format is Type 0 (0x00).
        # Write the stream id.
        # if mask is 0x00:

        elif mask == 0x00:
            # We will need to write an absolute timestamp, body length, data type
            # and stream id for this type of packet.

            # Write the absolute timestamp.
            # NOTE: See above branch for mask type 0x80.
            if header.timestamp >= 0xffffff:
                rtmp_stream.write_24bit_uint(0xffffff)
            else:
                # Otherwise write the timestamp delta.
                rtmp_stream.write_24bit_uint(header.timestamp)

            # Write the body length.
            rtmp_stream.write_24bit_uint(header.body_length)  # message length

            # Write the data type.
            rtmp_stream.write_uchar(header.data_type)  # message type id

            # Write the stream id.
            rtmp_stream.endian = '<'
            rtmp_stream.write_ulong(header.stream_id)
            rtmp_stream.endian = '!'

            # Set to state that we are sending an absolute timestamp.
            header.timestamp_absolute = True

            # TODO: Added format information in rtmp_header.encode.
            # Set header format to Type 0.
            header.chunk_type = types.HEADER_TYPE_0_FULL

        # If the timestamp (absolute or delta) we wrote was greater than or equal to the value 16777215,
        # then we need to write it's true value in this extended timestamp field.
        # This is only applicable to types 0, 1 or 2 (not 3 as it does not feature a timestamp).
        # if mask <= 0x80:

        if header.timestamp >= 0xffffff:
            # Write the extended timestamp.
            rtmp_stream.write_ulong(header.timestamp)

            # TODO: Should the extended timestamp be a boolean value?
            header.extended_timestamp = header.timestamp
        else:
            header.extended_timestamp = None

    # log.info('Header encoded: %s' % header)
    # TODO: Verify at encode_header end-point that a True was returned from encoding the header.
    # print('Header encoded: %s' % repr(header))


# TODO: Read issue where some formats are missing - this maybe due to a format of 3 (type 3) header arrival.
# TODO: Can we not connect this up to the Header class?
def decode(rtmp_stream):
    """
    Reads a header from the incoming stream.

    NOTE: A header can be of varying lengths and the properties that
          gets updated depend on its length.
    @param rtmp_stream: The byte stream to read the header from.
    @type rtmp_stream: C{pyamf.util.BufferedByteStream}
    @return: The read header from the stream.
    @rtype: L{Header}
    """
    # Read header type and chunk stream Id.
    chunk_stream_id = rtmp_stream.read_uchar()
    # header_format = chunk_stream_id >> 6
    header_type = chunk_stream_id >> 6
    # Set the channel mask.
    chunk_stream_id &= 0x3f

    # log.debug('Header type (format): %s Read chunk_stream_id: %s' % (header_type, chunk_stream_id))

    # We need one more byte.
    if chunk_stream_id is 0:
        chunk_stream_id = rtmp_stream.read_uchar() + 64

    # We need two more bytes.
    if chunk_stream_id is 1:
        chunk_stream_id = rtmp_stream.read_uchar() + 64 + (rtmp_stream.read_uchar() << 8)

    # Initialise a header object and set it up with the channelId.
    decoded_header = RtmpHeader(chunk_stream_id)
    # Apply the decoded header format type to the header object.
    decoded_header.chunk_type = header_type

    # TODO: We should not be decoding depending on sections, we need to decode based on format - branching.
    # if header_format is types.TYPE_3_CONTINUATION:

    # TODO: RECORD HEADER - since this header is in chunks, we can re-use this same header
    #       if it occurs again on the same channel id.
    # Make sure we check the channel is in the recorded_headers dictionary and the correct attributes are present.
    # if str(chunk_stream_id) in recorded_headers:
    #     # Instate a parent header, which we can easily refer back to.
    #     parent_header = recorded_headers[str(chunk_stream_id)]

    #     # Assign the stream ID, body length, data type and timestamp to the new header.
    #     if hasattr(parent_header, 'stream_id'):
    #         header.stream_id = parent_header.stream_id
    #     if hasattr(parent_header, 'data_type'):
    #         header.data_type = parent_header.data_type
    #     if hasattr(parent_header, 'timestamp'):
    #         header.timestamp = parent_header.timestamp
    #     if hasattr(parent_header, 'body_length'):
    #         header.body_length = parent_header.body_length

    # Set header format to Type 3.
    # header.format = types.TYPE_3_CONTINUATION

    # return header

    # TODO: If the bits is 3 then we will have to use chunks, as a result we will need to re-use headers.
    # TODO: Will the format jump into this branch first before going into anything else?
    # if header_format < types.TYPE_3_CONTINUATION:

    # if str(chunk_stream_id) in recorded_headers:
    #     # Instate a parent header, which we can easily refer back to.
    #     previous_header = recorded_headers[str(chunk_stream_id)]
    #
    #     # Assign the stream ID and body size to the new header.
    #     if hasattr(previous_header, 'stream_id'):
    #         header.stream_id = previous_header.stream_id
    #     if hasattr(previous_header, 'body_length'):
    #         header.body_length = previous_header.body_length

    # Read the timestamp [delta] if it has changed.
    # header.timestamp = stream.read_24bit_uint()

    # Set header format to Type 2.
    # header.format = types.TYPE_2_SAME_LENGTH_AND_STREAM

    # if header_format < types.TYPE_2_SAME_LENGTH_AND_STREAM:
    #     # Read the message body size and the message type id.
    #     header.body_length = stream.read_24bit_uint()
    #     header.data_type = stream.read_uchar()

    # TODO: RECORD HEADER - set stream id before we parse it.
    #  if recorded_headers['previous'] is not None:
    #     if hasattr(recorded_headers['previous'], 'stream_id'):
    #         header.stream_id = recorded_headers['previous'].stream_id

    # Set header format to Type 1.
    # header.format = types.TYPE_1_SAME_STREAM

    # if header_format < types.TYPE_1_SAME_STREAM:
    #     # Read the stream id, this is little endian.
    #     stream.endian = '<'
    #     header.stream_id = stream.read_ulong()
    #     stream.endian = '!'
    #
    #     # Set header format to Type 0.
    #     # header.format = types.TYPE_0_FULL

    if decoded_header.chunk_type == types.HEADER_TYPE_3_CONTINUATION:
        # No header data present, it is a continuation of the same data from the preceding chunks.
        # TODO: Return the previously recorded headers, otherwise the read loop in RtmpReader will continue looping as
        #       we do not know the message body size to expect.
        return decoded_header

    else:

        if decoded_header.chunk_type == types.HEADER_TYPE_2_SAME_LENGTH_AND_STREAM:
            # Only the timestamp delta is present in this.
            decoded_header.timestamp = rtmp_stream.read_24bit_uint()

            # Set to state that the timestamp received was a delta.
            decoded_header.timestamp_delta = True

            # TODO: Make sure we get the previous headers body length.

            # TODO: Make sure we get the previous headers stream id.

        elif decoded_header.chunk_type == types.HEADER_TYPE_1_SAME_STREAM:
            # Has all the fields except for the stream Id, which remains the same,
            # when the first type 0 header was sent.

            # Read the timestamp delta.
            decoded_header.timestamp = rtmp_stream.read_24bit_uint()

            # Read the body length.
            decoded_header.body_length = rtmp_stream.read_24bit_uint()

            # Read the data type (message types).
            decoded_header.data_type = rtmp_stream.read_uchar()

            # TODO: Make sure we get the previous headers stream id.

            # Set to state that the timestamp received was a delta.
            decoded_header.timestamp_delta = True

        elif decoded_header.chunk_type == types.HEADER_TYPE_0_FULL:
            # This has all the fields present in its header.

            # Read the absolute timestamp.
            decoded_header.timestamp = rtmp_stream.read_24bit_uint()

            # Read the body length.
            decoded_header.body_length = rtmp_stream.read_24bit_uint()

            # Read the data type (message types).
            decoded_header.data_type = rtmp_stream.read_uchar()

            # Read the little endian stream id.
            rtmp_stream.endian = '<'
            decoded_header.stream_id = rtmp_stream.read_ulong()
            rtmp_stream.endian = '!'

            # Set to state that the timestamp received was an absolute.
            decoded_header.timestamp_absolute = True

        # If the timestamp (absolute or delta) we read was greater than or equal to
        # the value 16777215, we can read the extended timestamp field to get the full timestamp.
        if decoded_header.timestamp == 0xffffff:
            # TODO: Should the extended timestamp be a boolean value?
            decoded_header.extended_timestamp = rtmp_stream.read_ulong()
        else:
            decoded_header.extended_timestamp = None

    # TODO: RECORD HEADER.
    # Record the headers we decoded and store them into the recorded_headers dictionary.
    # Type 1 and 2.
    # recorded_headers['previous'] = header
    # Type 3.
    # recorded_headers[str(chunk_stream_id)] = header

    # log.info('Header decoded: %s' % header)
    # print('Header decoded: %s' % repr(header))
    return decoded_header


class RtmpHeaderHandler:

    def __init__(self):
        """"""
