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


NOTE: The notes below are taken from the rtmplite project and have been slightly modified -
     (https://github.com/theintencity/rtmplite/)

How the header format works:
----------------------------

NOTE: Here is a part of the documentation to understand how the Chunks' headers work.
      To have a complete documentation, YOU HAVE TO READ RTMP Specification V1.0 (rtmp_specification_1.0.pdf) -
      http://wwwimages.adobe.com/content/dam/Adobe/en/devnet/rtmp/pdf/rtmp_specification_1.0.pdf (page 13 onwards).

This is the format of a chunk. Here, we store all except the chunk data:
------------------------------------------------------------------------
+-------------+----------------+-------------------+--------------+
| Basic header|Chunk Msg Header|Extended Time Stamp|   Chunk Data |
+-------------+----------------+-------------------+--------------+

This are the formats of the basic header:
-----------------------------------------
 0 1 2 3 4 5 6 7      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3
+-+-+-+-+-+-+-+-+    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|fmt|   cs id   |    |fmt|     0     |   cs id - 64  |    |fmt|     1     |        cs id - 64             |
+-+-+-+-+-+-+-+-+    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
  (cs id < 64)            (64 <= cs id < 320)                           (320 <= cs id)

'fmt' stores the format of the chunk message header. There are four different formats.


Type 0 (fmt=00):
----------------
fmt = 00 (binary) / fmt = 0 (decimal)

This type MUST be used at the start of a chunk stream, and whenever the stream timestamp goes backward (e.g., because
of a backwards seek).


 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      timestamp                |                message length                 |message type id|                message stream id              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


Type 1 (fmt=01):
----------------
fmt = 01 (binary) / fmt = 1 (decimal)

Streams with variable-sized messages (for example, many video formats) SHOULD use this format for the first chunk
of each new message after the first.

 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                timestamp delta                |                message length                 |message type id|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


Type 2 (fmt=10):
----------------
fmt = 10 (binary) / fmt = 2 (decimal)

Streams with constant-sized messages (for example, some audio and data formats) SHOULD use this format for the first
chunk of each message after the first.

 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                timestamp delta                |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


Type 3 (fmt=11):
----------------
fmt=11 (binary)/ fmt=3 (decimal)


Chunks of Type 3 have no header. Stream ID, message length and timestamp delta are not present; chunks of this type take
values from the preceding chunk. When a single message is split into chunks, all chunks of a message except the first
one, SHOULD use this type.


Extended Timestamp:
-------------------
NOTE: Type 3 chunks MUST NOT have this field.
      This field MUST NOT be present if the timestamp field is not present.
      If normal timestamp is set to any value less than 0x00ffffff, this field MUST NOT be present.

This field is transmitted only when the normal time stamp in the chunk message header is set to 0x00ffffff.
This field, if transmitted, is located immediately after the chunk message header and before the chunk data.

Standard Chunk Stream ID Assignments:
-------------------------------------
/**
 * the chunk stream id used for some under-layer message,
 * for example, the PC(protocol control) message.
 */
RTMP_CID_ProtocolControl                0x02

/**
 * the AMF0/AMF3 command message, invoke method and return the result, over NetConnection.
 * generally use 0x03.
 */
RTMP_CID_OverConnection                 0x03

/**
 * the AMF0/AMF3 command message, invoke method and return the result, over NetConnection,
 * the midst state(we guess).
 * rarely used, e.g. onStatus(NetStream.Play.Reset).
 */
RTMP_CID_OverConnection2                0x04

/**
 * the stream message(amf0/amf3), over NetStream.
 * generally use 0x05.
 */
RTMP_CID_OverStream                     0x05

/**
 * the stream message(amf0/amf3), over NetStream, the midst state(we guess).
 * rarely used, e.g. play("mp4:mystream.f4v")
 */
RTMP_CID_OverStream2                    0x08

/**
 * the stream message(video), over NetStream
 * generally use 0x06.
 */
RTMP_CID_Video                          0x06

/**
 * the stream message(audio), over NetStream.
 * generally use 0x07.
 */
RTMP_CID_Audio                          0x07


Sending Audio/Video Data (message type 8/9):
------------------------------------

NOTE: When using the channel, it is equal to the format + whatever chunk stream ID the RTMP messages are to be sent on.

When we send the video data we initially send a packet in which:

Initial packet:
    • header:
        - format WILL BE 0
        - a chunk stream id

        - timestamp (absolute)
        - message (body) size
        - message type id
        - message stream id

    • body:
        - Control type (sometimes keyframe e.g. 0x12 - keyframes may have times at which they are sent e.g. every 50
                        packets of video data sent we send a keyframe)
        - Audio/Video data (sometimes FLV data e.g. Sorenson H263/MP3)

Remaining packets:
    • header:
        - format SHOULD BE 3 (if it is audio we are sending and the body size is the same, we can send on format 2)
        - same chunk stream id

        - timestamp (delta)
        - message (body) size
        - message type id

    • body:
        - Control type (sometimes inter-frames/disposable frames e.g. 0x22/0x32 / 0x22 (MP3 control type))
        - Video data (sometimes FLV data e.g Sorenson H263/ MP3)


Calculating timestamp delta:
--------------------------

Roughly get the time the previous packet was sent at (in seconds) to 3 decimal places.
Get the time at which the new packet has been completely assembled and ready to send with a similar accuracy.
Take away the latest from the earlier and times the answer by 1000 to return our timestamp delta roughly.
"""

import logging

from rtmp.util import types

# TODO: RECORD HEADER:
#       Possibly remove use of dictionary and since this will increase memory size, since we only
#       need the previous header, just store that separately.

# TODO: Video data has type/format 1 after initial frame with streamId on format 0.
#       Audio data, if same length then uses type 2, if the length changes then it can use type 3.
#       The chunk stream id for both video and audio data IS NOT the same - default video (6), audio (7).
#       The stream id on the first packet for both video and audio data should be the same, we can do not have to
#       send the stream_id afterwards.

log = logging.getLogger(__name__)


# TODO: Make it more simpler to log and debug rtmp headers.


class HeaderError(Exception):
    """ Raised if a header related operation failed. """


class RtmpHeader(object):
    """
    The main class to handle RTMP header related events.
    This will hold and be able to encode/decode the contextual information regarding a RTMP chunk stream, along
    with the data's payload.
    """

    __slots__ = ('chunk_type', 'chunk_stream_id', 'timestamp',
                 'body_length', 'data_type', 'stream_id', 'extended_timestamp',
                 'timestamp_absolute', 'timestamp_delta')

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
        # self.format = -1  # Non-manual - calculated.
        self.chunk_type = -1  # Non-manual - calculated.

        # TODO: Should we rename to chunk_stream_id or keep it as channel_id?
        #       Might be worth renaming according to the specification.
        # self.channel_id = int(channel_id)  # Manual entry.
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

    # TODO: Make the code to represent the object more clear and concise.
    def __repr__(self):
        """
        Return a string representation of the attributes of the header.
        :return: str header attribute presentation.
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


class Header(object):
    """
    An RTMP Header which holds contextual information regarding an RTMP Channel,
    along with the information regarding the payload it will be carrying.
    """
    # TODO: Solved __slots__ read-only issue - moved structure of classes.
    # Initialise the only attributes we want the object to store.
    # 'format', 'channel_id'
    __slots__ = ('chunk_type', 'chunk_stream_id', 'timestamp',
                 'body_length', 'data_type', 'stream_id', 'extended_timestamp',
                 'timestamp_absolute', 'timestamp_delta')

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
        # self.format = -1  # Non-manual - calculated.
        self.chunk_type = -1  # Non-manual - calculated.

        # TODO: Should we rename to chunk_stream_id or keep it as channel_id?
        #       Might be worth renaming according to the specification.
        # self.channel_id = int(channel_id)  # Manual entry.
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
        :return: str header attribute presentation.
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


class HeaderHandler:
    """ A class to handle header related events. """

    def __init__(self, rtmp_stream):
        """
        Initialise the handler once with the working RTMP stream.

        :param rtmp_stream: L{pyamf.util.BufferedByteStream} the stream to write the encoded header.
        """
        # @param header: The L{Header} to encode.
        # @param previous: The previous header (if any).

        # Initialise the stream in which we will be receiving headers.
        self.working_stream = rtmp_stream

        # Set up a previous packet to merge data from in the event of header
        # attributes we do not have.
        self.previous_header = RtmpHeader(-1)

    # Header help methods:
    # TODO: We can use this to get the rest of the values for a continuation header type.
    # TODO: Is it possible to utilise this function to handle chunk_types?
    @staticmethod
    def get_merged(original, to_merge):
        """
        Merge the values of C{original} and C{to_merge}, returning the resulting header.

        NOTE: Mainly for decoding.

        This method is especially useful in the event we receive headers which are missing data that
        is crucial to decode the header e.g. header type 3 where nothing is sent, we can return
        the complete header by merging the values of the previous header and this new one.

        NOTE: We cannot start to merge headers from different chunk streams.

        :param original: L{Header}
        :param to_merge: L{Header}
        :return: L{Header}
        """
        if to_merge.chunk_stream_id != original.chunk_stream_id:
            raise HeaderError('chunk_stream_id mismatch on the header to merge (merging=%r, merging with=%r)' %
                              (to_merge.chunk_stream_id, original.chunk_stream_id))

        merged_header = to_merge

        # TODO: Should we limit this function from only being able to work when we have a complete original header?

        # TODO: No need to create a new header object when we can just utilise the object we were given.
        if merged_header.stream_id != -1:
            merged_header.stream_id = original.stream_id

        # else:
        #     merged_header.stream_id = old.stream_id

        if merged_header.data_type != -1:
            merged_header.data_type = original.data_type

        # else:
        #     merged.data_type = old.data_type

        if merged_header.timestamp != -1:
            merged_header.timestamp = original.timestamp

        # else:
        #     merged.timestamp = old.timestamp

        if merged_header.body_length != -1:
            merged_header.body_length = merged_header.body_length

        # else:
        #     merged.body_length = old.body_length

        return merged_header

    @staticmethod
    def get_size_mask(old_header, new_header):
        """
        Returns the number of bytes needed to encode the header based on the differences between the two.
        NOTE: Both headers must be from the same chunk stream in order for this to work.

        NOTE: Mainly for encoding.

        NOTE: By comparing the size we need to encode the header, we can reduce overhead in packets by only
              the necessary parts of the packet.

        @type old_header: L{Header}
        @type new_header: L{Header}
        """
        # TODO: Re-organise the logic of the branching in this function.

        if old_header.chunk_stream_id != new_header.chunk_stream_id:
            raise HeaderError('chunk_stream_id mismatch on size mask old_header=%r, new=%r' % (old_header, new_header))

        if old_header is new_header:
            return 0xc0  # type 3 encode - send continuation
        else:
            if old_header.stream_id != new_header.stream_id:
                return 0  # type 0 encode - send full header
            else:
                if old_header.data_type == new_header.data_type and old_header.body_length == new_header.body_length:
                    if old_header.timestamp == new_header.timestamp:
                        return 0xc0  # type 3 encode
                    else:
                        return 0x80  # type 2 encode
                else:
                    return 0x40  # type 1 encode

    def encode(self, header):
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

        @param stream: The stream to write the encoded header.
        @type stream: L{util.BufferedByteStream}.
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
            stream.write_uchar(mask | chunk_stream_id)
        elif chunk_stream_id < 320:  # <=319
            stream.write_uchar(mask)
            stream.write_uchar(chunk_stream_id - 64)
        else:
            chunk_stream_id -= 64

            stream.write_uchar(mask + 1)
            stream.write_uchar(chunk_stream_id & 0xff)
            stream.write_uchar(chunk_stream_id >> 0x08)

        # TODO: We should not be encoding depending on sections, we need to decode based on format - branching.
        # This is a Type 3 (0xC0) header, we do not need to write the stream id, message size or
        # timestamp delta since they are not present in this type of message.
        if mask == 0xc0:
            # TODO: Added format information in rtmp_header.encode.
            # Set header format to Type 3
            header.chunk_type = types.TYPE_3_CONTINUATION
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
                    stream.write_24bit_uint(0xffffff)
                else:
                    # Otherwise write the timestamp delta.
                    stream.write_24bit_uint(header.timestamp)

                # Set to state that we sent a timestamp delta,
                header.timestamp_delta = True

                # TODO: Added format information in rtmp_header.encode.
                # Set header format to Type 2.
                header.chunk_type = types.TYPE_2_SAME_LENGTH_AND_STREAM

            # This applies to headers which are Type 1 (0x40) or smaller.
            # Write message length, followed by the message type id.
            # if mask <= 0x40:

            elif mask == 0x40:
                # We will need to write the timestamp delta, body length and data type
                # for this type of header.

                # Write the timestamp delta.
                # NOTE: See above branch for mask type 0x80.
                if header.timestamp >= 0xffffff:
                    stream.write_24bit_uint(0xffffff)
                else:
                    # Otherwise write the timestamp delta.
                    stream.write_24bit_uint(header.timestamp)

                # Write the body length.
                stream.write_24bit_uint(header.body_length)  # message length

                # Write the data type.
                stream.write_uchar(header.data_type)  # message type id

                # Set to state that we are sending a timestamp delta.
                header.timestamp_delta = True

                # TODO: Added format information in rtmp_header.encode.
                # Set header format to Type 1.
                header.chunk_type = types.TYPE_1_SAME_STREAM

            # This applies if the format is Type 0 (0x00).
            # Write the stream id.
            # if mask is 0x00:

            elif mask == 0x00:
                # We will need to write an absolute timestamp, body length, data type
                # and stream id for this type of packet.

                # Write the absolute timestamp.
                # NOTE: See above branch for mask type 0x80.
                if header.timestamp >= 0xffffff:
                    stream.write_24bit_uint(0xffffff)
                else:
                    # Otherwise write the timestamp delta.
                    stream.write_24bit_uint(header.timestamp)

                # Write the body length.
                stream.write_24bit_uint(header.body_length)  # message length

                # Write the data type.
                stream.write_uchar(header.data_type)  # message type id

                # Write the stream id.
                stream.endian = '<'
                stream.write_ulong(header.stream_id)
                stream.endian = '!'

                # Set to state that we are sending an absolute timestamp.
                header.timestamp_absolute = True

                # TODO: Added format information in rtmp_header.encode.
                # Set header format to Type 0.
                header.chunk_type = types.TYPE_0_FULL

            # If the timestamp (absolute or delta) we wrote was greater than or equal to the value 16777215,
            # then we need to write it's true value in this extended timestamp field.
            # This is only applicable to types 0, 1 or 2 (not 3 as it does not feature a timestamp).
            # if mask <= 0x80:

            if header.timestamp >= 0xffffff:
                # Write the extended timestamp.
                stream.write_ulong(header.timestamp)

                # TODO: Should the extended timestamp be a boolean value?
                header.extended_timestamp = header.timestamp
            else:
                header.extended_timestamp = None

                # log.info('Header encoded: %s' % header)
                # TODO: Verify at encode_header end-point that a True was returned from encoding the header.
                # print('Header encoded: %s' % repr(header))


# TODO: This should be based on each header we decode. We need to create encoding rules as well.
# TODO: This does not function to it's full - it just keep on returning 0xc0 due to the same header being re-used.
# TODO: We need to make this work on a packet basis as well.
def get_size_mask(old_header, new_header):
    """
    Returns the number of bytes needed to encode the header based on the differences between the two.
    NOTE: Both headers must be from the same chunk stream in order for this to work.

    NOTE: By comparing the size we need to encode the header, we can reduce overhead in packets by only
          the necessary parts of the packet.

    @type old_header: L{Header}
    @type new_header: L{Header}
    """
    # TODO: Re-organise the logic of the branching in this function.
    # If the header we just received and the header previous to it is identical,
    # then it is an RTMP message in chunks.
    # Return that size corresponds to a type 3 header.
    if old_header is new_header:
        return 0xc0  # 192

    # If the header is not on the same channel then we cannot compare it.
    if old_header.chunk_stream_id != new_header.chunk_stream_id:
        raise HeaderError('chunk_stream_id mismatch on diff old=%r, new=%r' % (old_header, new_header))

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


# TODO: Can we not connect this up to the Header class?
def encode(stream, header, previous=None):
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

    @param stream: The stream to write the encoded header.
    @type stream: L{util.BufferedByteStream}.
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
        stream.write_uchar(mask | chunk_stream_id)
    elif chunk_stream_id < 320:  # <=319
        stream.write_uchar(mask)
        stream.write_uchar(chunk_stream_id - 64)
    else:
        chunk_stream_id -= 64

        stream.write_uchar(mask + 1)
        stream.write_uchar(chunk_stream_id & 0xff)
        stream.write_uchar(chunk_stream_id >> 0x08)

    # TODO: We should not be encoding depending on sections, we need to decode based on format - branching.
    # This is a Type 3 (0xC0) header, we do not need to write the stream id, message size or
    # timestamp delta since they are not present in this type of message.
    if mask == 0xc0:
        # TODO: Added format information in rtmp_header.encode.
        # Set header format to Type 3
        header.chunk_type = types.TYPE_3_CONTINUATION
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
                stream.write_24bit_uint(0xffffff)
            else:
                # Otherwise write the timestamp delta.
                stream.write_24bit_uint(header.timestamp)

            # Set to state that we sent a timestamp delta,
            header.timestamp_delta = True

            # TODO: Added format information in rtmp_header.encode.
            # Set header format to Type 2.
            header.chunk_type = types.TYPE_2_SAME_LENGTH_AND_STREAM

        # This applies to headers which are Type 1 (0x40) or smaller.
        # Write message length, followed by the message type id.
        # if mask <= 0x40:

        elif mask == 0x40:
            # We will need to write the timestamp delta, body length and data type
            # for this type of header.

            # Write the timestamp delta.
            # NOTE: See above branch for mask type 0x80.
            if header.timestamp >= 0xffffff:
                stream.write_24bit_uint(0xffffff)
            else:
                # Otherwise write the timestamp delta.
                stream.write_24bit_uint(header.timestamp)

            # Write the body length.
            stream.write_24bit_uint(header.body_length)  # message length

            # Write the data type.
            stream.write_uchar(header.data_type)  # message type id

            # Set to state that we are sending a timestamp delta.
            header.timestamp_delta = True

            # TODO: Added format information in rtmp_header.encode.
            # Set header format to Type 1.
            header.chunk_type = types.TYPE_1_SAME_STREAM

        # This applies if the format is Type 0 (0x00).
        # Write the stream id.
        # if mask is 0x00:

        elif mask == 0x00:
            # We will need to write an absolute timestamp, body length, data type
            # and stream id for this type of packet.

            # Write the absolute timestamp.
            # NOTE: See above branch for mask type 0x80.
            if header.timestamp >= 0xffffff:
                stream.write_24bit_uint(0xffffff)
            else:
                # Otherwise write the timestamp delta.
                stream.write_24bit_uint(header.timestamp)

            # Write the body length.
            stream.write_24bit_uint(header.body_length)  # message length

            # Write the data type.
            stream.write_uchar(header.data_type)  # message type id

            # Write the stream id.
            stream.endian = '<'
            stream.write_ulong(header.stream_id)
            stream.endian = '!'

            # Set to state that we are sending an absolute timestamp.
            header.timestamp_absolute = True

            # TODO: Added format information in rtmp_header.encode.
            # Set header format to Type 0.
            header.chunk_type = types.TYPE_0_FULL

        # If the timestamp (absolute or delta) we wrote was greater than or equal to the value 16777215,
        # then we need to write it's true value in this extended timestamp field.
        # This is only applicable to types 0, 1 or 2 (not 3 as it does not feature a timestamp).
        # if mask <= 0x80:

        if header.timestamp >= 0xffffff:
            # Write the extended timestamp.
            stream.write_ulong(header.timestamp)

            # TODO: Should the extended timestamp be a boolean value?
            header.extended_timestamp = header.timestamp
        else:
            header.extended_timestamp = None

    # log.info('Header encoded: %s' % header)
    # TODO: Verify at encode_header end-point that a True was returned from encoding the header.
    # print('Header encoded: %s' % repr(header))


# TODO: Read issue where some packets are missing - this maybe due to a format of 3 (type 3) header arrival.
# TODO: Can we not connect this up to the Header class?
def decode(stream):
    """
    Reads a header from the incoming stream.

    NOTE: A header can be of varying lengths and the properties that
          gets updated depend on its length.
    @param stream: The byte stream to read the header from.
    @type stream: C{pyamf.util.BufferedByteStream}
    @return: The read header from the stream.
    @rtype: L{Header}
    """
    # Read header type and chunk stream Id.
    chunk_stream_id = stream.read_uchar()
    # header_format = chunk_stream_id >> 6
    header_type = chunk_stream_id >> 6
    # Set the channel mask.
    chunk_stream_id &= 0x3f

    # log.debug('Header type (format): %s Read chunk_stream_id: %s' % (header_type, chunk_stream_id))

    # We need one more byte.
    if chunk_stream_id is 0:
        chunk_stream_id = stream.read_uchar() + 64

    # We need two more bytes.
    if chunk_stream_id is 1:
        chunk_stream_id = stream.read_uchar() + 64 + (stream.read_uchar() << 8)

    # Initialise a header object and set it up with the channelId.
    header = Header(chunk_stream_id)
    # Apply the decoded header format type to the header object.
    header.chunk_type = header_type

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

    if header.chunk_type == types.TYPE_3_CONTINUATION:
        # No header data present, it is a continuation of the same data from the preceding chunks.
        # TODO: Return the previously recorded headers, otherwise the read loop in RtmpReader will continue looping as
        #       we do not know the message body size to expect.
        return header

    else:

        if header.chunk_type == types.TYPE_2_SAME_LENGTH_AND_STREAM:
            # Only the timestamp delta is present in this.
            header.timestamp = stream.read_24bit_uint()

            # Set to state that the timestamp received was a delta.
            header.timestamp_delta = True

            # TODO: Make sure we get the previous headers body length.

            # TODO: Make sure we get the previous headers stream id.

        elif header.chunk_type == types.TYPE_1_SAME_STREAM:
            # Has all the fields except for the stream Id, which remains the same,
            # when the first type 0 header was sent.

            # Read the timestamp delta.
            header.timestamp = stream.read_24bit_uint()

            # Read the body length.
            header.body_length = stream.read_24bit_uint()

            # Read the data type (message types).
            header.data_type = stream.read_uchar()

            # TODO: Make sure we get the previous headers stream id.

            # Set to state that the timestamp received was a delta.
            header.timestamp_delta = True

        elif header.chunk_type == types.TYPE_0_FULL:
            # This has all the fields present in its header.

            # Read the absolute timestamp.
            header.timestamp = stream.read_24bit_uint()

            # Read the body length.
            header.body_length = stream.read_24bit_uint()

            # Read the data type (message types).
            header.data_type = stream.read_uchar()

            # Read the little endian stream id.
            stream.endian = '<'
            header.stream_id = stream.read_ulong()
            stream.endian = '!'

            # Set to state that the timestamp received was an absolute.
            header.timestamp_absolute = True

        # If the timestamp (absolute or delta) we read was greater than or equal to
        # the value 16777215, we can read the extended timestamp field to get the full timestamp.
        if header.timestamp == 0xffffff:
            # TODO: Should the extended timestamp be a boolean value?
            header.extended_timestamp = stream.read_ulong()
        else:
            header.extended_timestamp = None

    # TODO: RECORD HEADER.
    # Record the headers we decoded and store them into the recorded_headers dictionary.
    # Type 1 and 2.
    # recorded_headers['previous'] = header
    # Type 3.
    # recorded_headers[str(chunk_stream_id)] = header

    # log.info('Header decoded: %s' % header)
    # print('Header decoded: %s' % repr(header))
    return header


__all__ = [
    'Header',
    'get_size_mask',
    'header_encode',
    'header_decode'
]
