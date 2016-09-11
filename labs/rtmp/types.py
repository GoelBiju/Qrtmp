"""
Represents an enumeration of the different RTMP message types such as
data types, shared object event types and user control types.

The notes in this file originally came from the SimpleRtmp project (https://github.com/faucamp/SimpleRtmp),
by faucamp, based in the Java programming language. It has only been slightly altered/reworded.
"""

# TODO: The file name has been altered to types.py and variables names have been modified.
# TODO: The shared object event types and user control types have been placed in here along with AMF3 types.


# === data types ===

# This is used in the case that the data type we receive could not be recognised.
DT_NONE = -0x1  # -1

# Protocol control message 1
# Set Chunk Size, is used to notify the peer a new maximum chunk size to use.

DT_SET_CHUNK_SIZE = 0x1  # 1

# Protocol control message 2
# Abort Message, is used to notify the peer if it is waiting for chunks
# to complete a message, then to discard the partially received message
# over a chunk stream and abort processing of that message.

DT_ABORT = 0x2  # 2

# Protocol control message 3
# The client or the server sends the acknowledgment to the peer after
# receiving bytes equal to the window size. The window size is the
# maximum number of bytes that the sender sends without receiving
# acknowledgment from the receiver.

DT_ACKNOWLEDGEMENT = 0x3  # 3

# Protocol control message 4
# The client or the server sends this message to notify the peer about
# the user control events. This message carries Event type and Event data.
# NOTE: Also known as a PING message in some RTMP implementations.

DT_USER_CONTROL = 0x4  # 4

# Protocol control message 5
# The client or the server sends this message to inform the peer which
# window size to use when sending acknowledgment.
# Also known as ServerBW ("server bandwidth") in some RTMP implementations.

DT_WINDOW_ACK_SIZE = 0x5  # 5

# Protocol control message 6
# The client or the server sends this message to update the output
# bandwidth of the peer. The output bandwidth value is the same as the
# window size for the peer.
# Also known as ClientBW ("client bandwidth") in some RTMP implementations.

DT_SET_PEER_BANDWIDTH = 0x6  # 6

# Protocol control message 7
# This is an Edge/Origin message, as stated in the Red5-server constants file.
# See here: https://github.com/Red5/red5-server-common/blob/master/src/main/java/org/red5/server/
#           net/rtmp/message/Constants.java#L74

DT_EDGE_ORIGIN = 0x7  # 7

# RTMP audio packet 8
# The client or the server sends this message to send audio data to the peer.

DT_AUDIO_MESSAGE = 0x8  # 8

# RTMP video packet 9
# The client or the server sends this message to send video data to the peer.

DT_VIDEO_MESSAGE = 0x9  # 9

# RTMP message type 15
# The client or the server sends this message to send Metadata or any
# user data to the peer. Metadata includes details about the data (audio, video etc.)
# like creation time, duration, theme and so on.
# This is the AMF3-encoded version.

DT_AMF3_DATA_MESSAGE = 0x0F  # 15

# RTMP message type 16
# A shared object is a Flash object (a collection of name value pairs)
# that are in synchronization across multiple clients, instances, and so on.
# This is the AMF3 version: kMsgContainerEx=16 for AMF3.

DT_AMF3_SHARED_OBJECT = 0x10  # 16

# RTMP message type 17
# Command messages carry the AMF-encoded commands between the client and the server.
# A command message consists of command name, transaction ID, and command object that
# contains related parameters.
# This is the AMF3-encoded version.

DT_AMF3_COMMAND = 0x11  # 17

# RTMP message type 18
# The client or the server sends this message to send Metadata or any
# user data to the peer. Metadata includes details about the data (audio, video etc.)
# like creation time, duration, theme and so on.
# This is the AMF0-encoded version.
# This can also act as a NOTIFY message, in some RTMP implementations, which does not expect a response.

DT_DATA_MESSAGE = 0x12  # 18

# RTMP message type 19
# A shared object is a Flash object (a collection of name value pairs)
# that are in synchronization across multiple clients, instances, and so on.
# This is the AMF0 version: kMsgContainer=19 for AMF0.

DT_SHARED_OBJECT = 0x13  # 19

# RTMP message type 20
# Command messages (invoke operation via RPC/also used in streaming) carry the AMF-encoded commands between the client
# and the server.
# A command message consists of command name, transaction ID, and command object that
# contains related parameters.
# This is the common AMF0 version, also known as INVOKE in some RTMP implementations.

DT_COMMAND = 0x14  # 20

# RTMP message type 22
# An aggregate message is a single message that contains a list of sub-messages.

DT_AGGREGATE_MESSAGE = 0x16  # 22


# === user control types ===

# This is used in the case that the data type we receive could not be recognised.
UC_NONE = -0x1  # -1

# Type: 0
# The server sends this event to notify the client that a stream has become
# functional and can be used for communication. By default, this event
# is sent on ID 0 after the application connect command is successfully
# received from the client.

# Event Data:
# eventData[0] (int) the stream ID of the stream that became functional

UC_STREAM_BEGIN = 0x00  # 0

# Type: 1
# The server sends this event to notify the client that the playback of
# data is over as requested on this stream. No more data is sent without
# issuing additional commands. The client discards the messages received
# for the stream.

# Event Data:
# eventData[0]: the ID of the stream on which playback has ended.

UC_STREAM_EOF = 0x1  # 1

# Type: 2
# The server sends this event to notify the client that there is no
# more data on the stream. If the server does not detect any message for
# a time period, it can notify the subscribed clients that the stream is
# dry.

# Event Data:
# eventData[0]: the stream ID of the dry stream.

UC_STREAM_DRY = 0x02  # 2

# Type: 3
# The client sends this event to inform the server of the buffer size
# (in milliseconds) that is used to buffer any data coming over a stream.
# This event is sent before the server starts  processing the stream.

# Event Data:
# eventData[0]: the stream ID and
# eventData[1]: the buffer length, in milliseconds.

UC_SET_BUFFER_LENGTH = 0x03  # 3

# Type: 4
# The server sends this event to notify the client that the stream is a
# recorded stream.

# Event Data:
# eventData[0]: the stream ID of the recorded stream.

UC_STREAM_IS_RECORDED = 0x04  # 4

# Type: 6
# The server sends this event to test whether the client is reachable.

# Event Data:
# eventData[0]: a timestamp representing the local server time when the server dispatched the command.
#
# The client responds with PING_RESPONSE on receiving PING_REQUEST.

UC_PING_REQUEST = 0x06  # 6

# Type: 7
# The client sends this event to the server in response to the ping request.

# Event Data:
# eventData[0]: the 4-byte timestamp which was received with the PING_REQUEST.

UC_PONG_REPLY = 0x07  # 7

# Type: 31 (0x1F)

# This user control type is not specified in any official documentation, but
# is sent by Flash Media Server 3.5. Thanks to the rtmpdump devs for their explanation.

# Buffer Empty (unofficial name): After the server has sent a complete buffer, and
# sends this Buffer Empty message, it will wait until the play
# duration of that buffer has passed before sending a new buffer.
# The Buffer Ready message will be sent when the new buffer starts.

# (see also: http://repo.or.cz/w/rtmpdump.git/blob/8880d1456b282ee79979adbe7b6a6eb8ad371081:/librtmp/rtmp.c#l2787)

UC_BUFFER_EMPTY = 0x1F  # 31

# Type: 32 (0x20)

# This user control type is not specified in any official documentation, but
# is sent by Flash Media Server 3.5. Thanks to the rtmpdump devs for their explanation.

# Buffer Ready (unofficial name): After the server has sent a complete buffer, and
# sends a Buffer Empty message, it will wait until the play
# duration of that buffer has passed before sending a new buffer.
# The Buffer Ready message will be sent when the new buffer starts.
# (There is no BufferReady message for the very first buffer;
# presumably the Stream Begin message is sufficient for that purpose.)

# (see also: http://repo.or.cz/w/rtmpdump.git/blob/8880d1456b282ee79979adbe7b6a6eb8ad371081:/librtmp/rtmp.c#l2787)

UC_BUFFER_READY = 0x20  # 32

# === shared object types ===

# Shared Object connection
SO_USE = 0x1  # 1

# Shared Object disconnection
SO_RELEASE = 0x2  # 2

# Set Shared Object attribute flag
SO_REQUEST_CHANGE = 3

# Client Shared Object data update
SO_CHANGE = 0x4  # 4

# Client Shared Object attribute update
SO_SUCCESS = 0x5  # 5

# Send message flag
SO_SEND_MESSAGE = 0x6  # 6

# Shared Object status marker
SO_STATUS = 0x7  # 7

# Clear event for Shared Object
SO_CLEAR = 0x8  # 8

# Delete data for Shared Object
SO_REMOVE = 0x9  # 9

# Shared Object attribute deletion flag
SO_REQUEST_MOVE = 0x0A  # 10

# Initial SO data flag
SO_USE_SUCCESS = 0x0B  # 11



