"""
Represents an enumeration of the different RTMP message types such as
data types, shared object event types and user control types (including details of types of data sent/received).

As well as this, it stores the various types of RTMP headers and chunk streams.

DT: RTMP Packet - data-type - standard types of packets.
UC: RTMP Packet - data-type - user control message type.
SO: RTMP Packet - data-type - shared object message type.
"""

DT_SET_CHUNK_SIZE = 1

DT_ABORT = 2

DT_ACKNOWLEDGE_BYTES = 3

DT_USER_CONTROL = 4

DT_WINDOW_ACKNOWLEDGEMENT_SIZE = 5

DT_SET_PEER_BANDWIDTH = 6

DT_EDGE_ORIGIN = 7

DT_AUDIO_MESSAGE = 8

DT_VIDEO_MESSAGE = 9

DT_AMF3_DATA_MESSAGE = 15

DT_AMF3_SHARED_OBJECT = 16

DT_AMF3_COMMAND = 17

DT_METADATA_MESSAGE = 18

DT_SHARED_OBJECT = 19

DT_COMMAND = 20

DT_AGGREGATE_MESSAGE = 22

UC_STREAM_BEGIN = 0

UC_STREAM_EOF = 1

UC_STREAM_DRY = 2

UC_SET_BUFFER_LENGTH = 3

UC_STREAM_IS_RECORDED = 4

UC_PING_REQUEST = 6

UC_PING_RESPONSE = 7

UC_BUFFER_EMPTY = 31

UC_BUFFER_READY = 32

HARD = 0

SOFT = 1

DYNAMIC = 2

SO_USE = 1

SO_RELEASE = 2

SO_REQUEST_CHANGE = 3

SO_CHANGE = 4

SO_SUCCESS = 5

SO_SEND_MESSAGE = 6

SO_STATUS = 7

SO_CLEAR = 8

SO_REMOVE = 9

SO_REQUEST_MOVE = 10

SO_USE_SUCCESS = 11
