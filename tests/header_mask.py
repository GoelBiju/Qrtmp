""" Testing how the header's mask or the chunk type should be decided depending on the previous header. """

import qrtmp.formats.rtmp_header as rtmp_header
import qrtmp.formats.rtmp_packet as rtmp_packet
import qrtmp.formats.types as types

# TODO: MAJOR ISSUE HERE - Implement rules and handle whether we use both the message and RtmpPacket.
# RULES: Some rules we must follow when handling header properties:
#       - Type 0 MUST BE used at the start of a new chunk stream (with a new chunk stream id).
#       - If packet format is Type 0 it has: timestamp, message length, message type id, message stream id.
#       - If packet format is Type 1 it has: timestamp delta, message length, message type id.
#       - If packet format is Type 2 it has: timestamp delta.
#       - If packet format is Type 3 it has: No header, takes header from preceding chunk.
#       - If the timestamp delta between the first message and the second message is same as the timestamp
#         of the first message, then a chunk of Type 3 could immediately follow the chunk of Type 0
#         as there is no need for a chunk of Type 2 to register the delta. If a Type 3 chunk follows a
#         Type 0 chunk, then the timestamp delta for this Type 3 chunk is the same as the timestamp
#         of the Type 0 chunk.

#      Chunk type            =            header mask
#  0 (0x00 - FULL)                         0x00 (0)
#  1 (0x01 - SAME STREAM)                  0x40 (64)
#  2 (0x02 - SAME LENGTH & SAME STREAM)    0x80 (128)
#  3 (0x03 - CONTINUATION)                 0xc0 (192)

# Info: In order for these to work, a situation where we have two different data types on the same chunk stream
#       can't happen, e.g. video and audio data on the same chunk stream, this is why they are sent on different
#       chunk streams.

# Info: The latest header must be merged with information from the latest header, where we don't have information,
#       if the header's are on the same stream, so we can decide what type of header to send next.

original_packet = rtmp_packet.RtmpPacket()
next_packet = rtmp_packet.RtmpPacket()


# Info: I think this can only work if the packets are sent on the same chunk stream.
def merge_headers(original_header, next_header):
    # Since the packets are on the same streams, we can copy over missing information.
    if original_header.chunk_stream_id == next_header.chunk_stream_id:
        print('On the same chunk stream.')

        if next_header.timestamp == -1:
            next_header.timestamp = original_header.timestamp
            print('assumed timestamp')

        if next_header.body_length == -1:
            next_header.body_length = original_header.body_length
            print('assumed body_length')

        if next_header.data_type == -1:
            next_header.data_type = original_header.data_type
            print('assumed data_type')

        if next_header.stream_id == -1:
            next_header.stream_id = original_header.stream_id
            print('assumed stream_id')

        return next_header

    else:
        return None


# TODO: Testing a type 1 header mask.
def test_type_1():
    # Set up some initial information about the packet.
    original_packet.set_chunk_stream_id(2)

    original_packet.set_timestamp(16373702)
    original_packet.header.body_length = 4
    original_packet.set_type(types.DT_WINDOW_ACKNOWLEDGEMENT_SIZE)
    original_packet.set_stream_id(0)

    # Set up some initial information about the next packet.
    next_packet.set_chunk_stream_id(2)

    next_packet.header.body_length = 10
    next_packet.set_type(types.DT_USER_CONTROL)

    print('Before merge:')
    print(repr(original_packet))
    print(repr(next_packet))

    merged_header = merge_headers(original_packet.header, next_packet.header)
    next_packet.header = merged_header

    print('After merge:')
    print(repr(next_packet))

    print('Chunk type/mask:', rtmp_header.get_size_mask(original_packet.header, next_packet.header))


def test_type_2():
    # If we had a stream of RTMP audio messages we needed to send, the first header can help indicate if the next
    # header in the next packet needs to be sent as a type 2 or something else.
    original_packet.set_chunk_stream_id(4)

    original_packet.set_timestamp(143364)
    original_packet.header.body_length = 129
    original_packet.set_type(types.DT_AUDIO_MESSAGE)
    original_packet.set_stream_id(1)

    # The next packet's data is the same as the first except for the timestamp, so we can have a type 2 header.
    next_packet.set_chunk_stream_id(4)

    next_packet.set_timestamp(48)  # this timestamp is the delta, the time between the original packet and this one.

    print('Before merge:')
    print(repr(original_packet))
    print(repr(next_packet))

    merged_header = merge_headers(original_packet.header, next_packet.header)
    next_packet.header = merged_header

    print('After merge:')
    print(repr(next_packet))

    print('Chunk type/mask:', rtmp_header.get_size_mask(original_packet.header, next_packet.header))


def test_type_3():
    # If we had a large AMF Command RTMP message we needed to send, we can use the same header to send the remaining
    # pieces of the RTMP body if the chunk size is too small. If size is smaller than 504 then we can split the body
    # into chunks into the size of the chunk size and send it. Here we send the all messages after the first as
    # a type 3 header - continuation.
    original_packet.set_chunk_stream_id(3)

    original_packet.set_timestamp(143364)
    original_packet.header.body_length = 504
    original_packet.set_type(types.DT_COMMAND)
    original_packet.set_stream_id(0)

    # The next packet will have all the same details as the original packet, but we do not need to write all the same
    # data into the stream, instead the a type 3 header will indicate to the server that the rest of the chunks are
    # from the same body and that the message was split up into smaller pieces.
    next_packet.set_chunk_stream_id(3)

    print('Before merge:')
    print(repr(original_packet))
    print(repr(next_packet))

    merged_header = merge_headers(original_packet.header, next_packet.header)
    next_packet.header = merged_header

    print('After merge:')
    print(repr(next_packet))

    print('Chunk type/mask:', rtmp_header.get_size_mask(original_packet.header, next_packet.header))

