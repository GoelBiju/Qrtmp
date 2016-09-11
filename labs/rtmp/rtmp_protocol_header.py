# -*- coding: utf-8 -*-

"""
Original source code taken from rtmpy project (http://rtmpy.org/)

It seems as the above url is broken, so provided below are the the links to the rtmpy project on GitHub
(https://github.com/hydralabs/rtmpy):

handshake.py - https://github.com/hydralabs/rtmpy/blob/master/rtmpy/protocol/handshake.py
header.py - https://github.com/hydralabs/rtmpy/blob/master/rtmpy/protocol/rtmp/header.py

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
This type MUST be used at the start of a chunk stream, and whenever the stream timestamp goes backward (e.g., because
of a backwards seek).


 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      timestamp                |                message length                 |message type id|                message stream id              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


Type 1 (fmt=01):
----------------
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


Type 3:
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
 * rarely used, e.g. play("mp4:mystram.f4v")
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

NOTE: When using the channel it is equal to the format + whatever chunk stream ID the RTMP messages are to be sent on.

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

# TODO: RECORD HEADER
#       Possibly remove use of dictionary and since this will increase memory size, since we only
#       need the previous header, just store that separately.

# TODO: Video data has type/format 1 after initial frame with streamId on format 0.
#       Audio data, if same length then uses type 2, if the length changes then it can use type 3.
#       The chunk stream id for both video and audio data IS NOT the same - default video (6), audio (7).
#       The stream id on the first packet for both video and audio data should be the same, we can do not have to
#       send the stream_id afterwards.

log = logging.getLogger(__name__)


# Record previous headers, for re-use when decoding packets, initialise the previous header.
recorded_headers = {'previous': None}

# Header types.
TYPE_0_FULL = 0x00
TYPE_1_RELATIVE_LARGE = 0x01
TYPE_2_RELATIVE_TIMESTAMP_ONLY = 0x02
TYPE_3_RELATIVE_SINGLE_BYTE = 0x03


class Header(object):
    """ An RTMP Header which holds contextual information regarding an RTMP Channel. """
    # TODO: Solve __slots__ read-only issue.
    # Initialise the only attributes we want the object to store.
    __slots__ = ('format', 'channel_id', 'timestamp', 'body_size',
                 'data_type', 'stream_id', 'extended_timestamp')

    def __init__(self, channel_id, timestamp=-1, body_size=-1, data_type=-1, stream_id=-1):
        """

        @param channel_id:
        @param timestamp:
        @param timestamp:
        @param body_size:
        @param data_type:
        @param stream_id:
        """
        # body_length=-1, full=False, variable=False, constant=False, continuation=False
        # TODO: Explicitly state the type of variable the header's attributes require when setting it,
        #       this will prevent any other type of variable being initialised instead of what we need.
        # NOTE: The header format (format) and the extended timestamp (extended_timestamp) ARE NOT to
        #       be set manually or at your own accord.

        # Header content:
        self.format = -1  # Non-manual - calculated.
        # TODO: Should we rename to chunk_stream_id or keep it as channel_id?
        self.channel_id = int(channel_id)  # Manual entry.

        self.timestamp = int(timestamp)  # Manual entry.
        self.body_size = int(body_size)  # Manual entry.
        # self.body_length = int(body_length)
        self.data_type = int(data_type)  # Manual entry.
        self.stream_id = int(stream_id)  # Manual entry.
        # This is only used if the timestamp is too large to fit in the original.
        self.extended_timestamp = -1  # Non-manual - calculated.

        # TODO: Should we have a descriptor for the type of timestamp e.g. absolute or delta.
        # self.timestamp_type = None  'absolute'/'delta'
        # self.absolute_timestamp = int(absolute_timestamp)
        # self.timestamp_delta = int(timestamp_delta)

        # Header Chunk Type descriptors:
        # self.header_full = bool(full)  # Header type (format) 0.
        # self.header_variable = bool(variable)  # Header type (format) 1.
        # self.header_constant = bool(constant)  # Header type (format) 2.
        # self.header_continuation = bool(continuation)  # Header type (format) 3.

    def __repr__(self):
        """

        @return:
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


def min_bytes_required(old_header, new_header):
    """
    Returns the number of bytes needed to de/encode the header based on the
    differences between the two.
    NOTE: Both headers must be from the same channel.

    @type old_header: L{Header}
    @type new_header: L{Header}
    """
    # If the header we just received and the header previous to it is identical,
    # then it is a chunked RTMP message and a continuation.
    if old_header is new_header:
        return 0xc0

    if old_header.channel_id != new_header.channel_id:
        raise Exception('HeaderError: channel_id mismatch on diff old=%r, new=%r' % (old_header, new_header))

    # If the stream id are not the same, then this indicates the use of a Type 0 message. A new chunk stream has
    # begun on the RTMP stream.
    if old_header.stream_id != new_header.stream_id:
        # This denotes a type 0 (full) header.
        return 0

    # If the previous header and the new headers message type id match and they have the same body size,
    # then send the chunk as Type 2, this saves space on the stream.
    # header.body_size, header.timestamp
    if old_header.data_type == new_header.data_type and old_header.body_size == new_header.body_size:
        # If the old header's timestamp and the new_header's timestamp match then send via Type 3,
        # we do not need to send a type 2 since the timestamp delta is the same.
        if old_header.timestamp == new_header.timestamp:
            # Return that the Type is 3.
            return 0xc0
        else:
            # If the body size is the same we can send via Type 2.
            # Return that the Type is 2.
            return 0x80

    # Return that the format is Type 1.
    return 0x40


def header_encode(stream, header, previous=None):
    """
    Encodes a RTMP header to C{stream}.

    NOTE: We expect the stream to already be in network endian mode.
    The channel id can be encoded in up to 3 bytes. The first byte is special as
    it contains the size of the rest of the header as described in L{getHeaderSize}.

    0 >= channel_id > 64: channel_id
    64 >= channel_id > 320: 0 channel_id - 64
    320 >= channel_id > 0xffff + 64: 1, channel_id - 64 (written as 2 byte int)

    Chunk Stream (type) 0 = 0x00
    Chunk Stream (type) 1 = 0x40
    Chunk Stream (type) 2 = 0x80
    Chunk Stream (type) 3 = 0xc0

    NOTE: We keep on altering the value of the header's format until we recognise
          which header format it truly is.

    @param stream: The stream to write the encoded header.
    @type stream: L{util.BufferedByteStream}.
    @param header: The L{Header} to encode.
    @param previous: The previous header (if any).
    """
    # TODO: Implement the use of previous headers here.
    if previous is None:
        read_format = 0
    else:
        read_format = min_bytes_required(header, previous)

    # Retrieve the channel id from the header's 'channel_id' attribute.
    channel_id = header.channel_id

    if channel_id < 64:
        stream.write_uchar(read_format | channel_id)
    elif channel_id < 320:
        stream.write_uchar(read_format)
        stream.write_uchar(channel_id - 64)
    else:
        channel_id -= 64

        stream.write_uchar(read_format + 1)
        stream.write_uchar(channel_id & 0xff)
        stream.write_uchar(channel_id >> 0x08)

    # This is a Type 3 (0xC0) header, we do not need to write the stream id, message size or
    # timestamp delta since they are not present in this type of message.
    if read_format is 0xc0:
        # Set header format to Type 3
        header.format = TYPE_3_RELATIVE_SINGLE_BYTE
        return

    # This applies to all header which is Type 2 (0x80) or smaller.
    # Write the timestamp, if it fits, elsewhere state we need an extended timestamp and write it later.
    if read_format <= 0x80:
        # If the value exceeds what we expect from a normal timestamp, state we need to extend the timestamp.
        if header.timestamp >= 0xffffff:
            stream.write_24bit_uint(0xffffff)
        else:
            # Otherwise write the timestamp delta.
            stream.write_24bit_uint(header.timestamp)

        # Set header format to Type 2.
        header.format = TYPE_2_RELATIVE_TIMESTAMP_ONLY

    # This applies to headers which are Type 1 (0x40) or smaller.
    # Write message length, followed by the message type id.
    if read_format <= 0x40:
        stream.write_24bit_uint(header.body_size)  # message length
        stream.write_uchar(header.data_type)  # message type id

        # Set header format to Type 1.
        header.format = TYPE_1_RELATIVE_LARGE

    # This applies if the format is Type 0 (0).
    # Write the stream id.
    if read_format is 0:
        stream.endian = '<'
        stream.write_ulong(header.stream_id)
        stream.endian = '!'

        # Set header format to Type 0.
        header.format = TYPE_0_FULL

    # If the timestamp present is too large to fit in, write an extended timestamp.
    # This is only applicable to types 0, 1 or 2 (not 3 as it does not feature a timestamp).
    if read_format <= 0x80:
        if header.timestamp >= 0xffffff:
            stream.write_ulong(header.timestamp)
            header.extended_timestamp = header.timestamp

    log.info('Header sent: %s' % header)
    print('Header sent: ', header)
    # TODO: Verify at encode_header end-point that a True was returned from encoding the header.
    return True


def header_decode(stream):
    """
    Reads a header from the incoming stream.

    NOTE: A header can be of varying lengths and the properties that get updated
    depend on its length.
    @param stream: The byte stream to read the header from.
    @type stream: C{pyamf.util.BufferedByteStream}
    @return: The read header from the stream.
    @rtype: L{Header}
    """
    # Read the size and 'channel_id'.
    channel_id = stream.read_uchar()
    read_format = channel_id >> 6
    # Set the channel mask.
    channel_id &= 0x3f

    log.debug('Read Format: %s Read channel_id (Chunk Stream Id): %s' % (read_format, channel_id))

    # We need one more byte.
    if channel_id is 0:
        channel_id = stream.read_uchar() + 64

    # We need two more bytes.
    if channel_id is 1:
        channel_id = stream.read_uchar() + 64 + (stream.read_uchar() << 8)

    # Initialise a header object and set it up with the channelId.
    header = Header(channel_id)

    if read_format is 3:
        # Set header format to Type 3.
        header.format = 3

        # TODO: RECORD HEADER - since this header is chunked, we can re-use this same header if it occurs again
        #       on the same channel id.
        # Make sure we check the channel is in the recorded_headers dictionary and the correct attributes are present.
        # if str(channel_id) in recorded_headers:
        #     # Instate a parent header, which we can easily refer back to.
        #     parent_header = recorded_headers[str(channel_id)]

        #     # Assign the stream ID, body length, data type and timestamp to the new header.
        #     if hasattr(parent_header, 'stream_id'):
        #         header.stream_id = parent_header.stream_id
        #     if hasattr(parent_header, 'data_type'):
        #         header.data_type = parent_header.data_type
        #     if hasattr(parent_header, 'timestamp'):
        #         header.timestamp = parent_header.timestamp
        #     if hasattr(parent_header, 'body_size'):
        #         header.body_size = parent_header.body_size

        return header

    # TODO: If the bits is 3 then we will have to use chunking, as a result we will need to re-use headers.
    # TODO: Will the format jump into this branch first before going into anything else?
    if read_format < 3:
        # if str(channel_id) in recorded_headers:
        #     # Instate a parent header, which we can easily refer back to.
        #     previous_header = recorded_headers[str(channel_id)]
        #
        #     # Assign the stream ID and body size to the new header.
        #     if hasattr(previous_header, 'stream_id'):
        #         header.stream_id = previous_header.stream_id
        #     if hasattr(previous_header, 'body_size'):
        #         header.body_size = previous_header.body_size

        # Read the timestamp [delta] if it has changed.
        header.timestamp = stream.read_24bit_uint()

        # Set header format to Type 2.
        header.format = 2

    if read_format < 2:
        # Read the message body size and the message type id.
        header.body_size = stream.read_24bit_uint()
        header.data_type = stream.read_uchar()

        # TODO: RECORD HEADER - set stream id before we parse it.
        # if recorded_headers['previous'] is not None:
        #     if hasattr(recorded_headers['previous'], 'stream_id'):
        #         header.stream_id = recorded_headers['previous'].stream_id

        # Set header format to Type 1.
        header.format = 1

    if read_format < 1:
        # Read the stream id, this is little endian.
        stream.endian = '<'
        header.stream_id = stream.read_ulong()
        stream.endian = '!'

        # Set header format to Type 0.
        header.format = 0

    # Locate the extended timestamp if it is present in types 0,1 or 2.
    if header.timestamp == 0xffffff:
        header.extended_timestamp = stream.read_ulong()

    # TODO: RECORD HEADER.
    # Record the headers we decoded and store them into the recorded_headers dictionary.
    # Type 1 and 2.
    # recorded_headers['previous'] = header
    # Type 3.
    # recorded_headers[str(channel_id)] = header

    log.info('Header received: %s' % header)
    return header


__all__ = [
    'HandshakePacket',
    'Header',
    'min_bytes_required',
    'header_encode',
    'header_decode'
]
