""" Represents an enumeration of the RTMP message datatypes. """

# TODO: Make sure the variables name are restored back to their originals.

NONE = -1

# TODO: Added.
UNKNOWN = 0

SET_CHUNK_SIZE = 1

ABORT = 2

# TODO: Altered.
ACKNOWLEDGEMENT = 3

# TODO: Altered.
USER_CONTROL = 4

WINDOW_ACK_SIZE = 5

SET_PEER_BANDWIDTH = 6

# TODO: Altered most.
AUDIO_MESSAGE = 8

VIDEO_MESSAGE = 9

DATA_MESSAGE = 18

SHARED_OBJECT = 19

COMMAND = 20

# TODO: Altered.
AGGREGATE_MESSAGE = 22

# AMF3_DATA_MESSAGE = 15

AMF3_SHARED_OBJECT = 16

AMF3_COMMAND = 17
