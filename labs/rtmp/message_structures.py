""" Retains all the various RTMP message structures which can be used in general (providing parameters are given). """

# Developed by GoelBiju (https://github.com/GoelBiju/)


def send_command(data_type, command):
    """
    Construct a remote procedure call (RPC) message provided the command and the parameters are given.
    :param data_type: int the RTMP data type.
    :param command: list with the RPC command name and  all the parameters to pass on in the message.
    """
    message = {
        'msg': data_type,
        'command': command
    }
    return message


def create_stream(data_type, transaction_id):
    """
    Construct a 'createStream' message to issue a new stream on which data can travel through.
    :param data_type: int the RTMP data type.
    :param transaction_id: int the transactionId in which the message will be sent on.
    """
    message = {
        'msg': data_type,
        'command': [u'createStream', transaction_id, None]
    }
    return message


def publish(data_type, stream_id, publishing_name, publishing_type):
    """
    Construct a 'publish' message to send publish information to start a broadcast.
    :param data_type: int the RTMP data type.
    :param stream_id: int the stream which the message will be sent on (received from createStream).
    :param publishing_name: str the name of the stream to publish on the server.
    :param publishing_type: str the type of publishing method i.e. 'live', 'record' or 'append'.
    """
    message = {
        'msg': data_type,
        'stream_id': stream_id,
        'command': [u'publish', 0, None, u'' + str(publishing_name), u'' + publishing_type]
    }
    return message


def set_chunk_size(data_type, stream_id, new_size):
    """
    Construct a 'SET_CHUNK_SIZE' message to adjust the chunk size at which the RTMP library works with.

    NOTE: All sizes set after 16777215 are equivalent.
    :param data_type: int the RTMP data type.
    :param stream_id: int the stream which the message will be sent on.
    :param new_size: int the new size of future message chunks from the client (1 <= size <= 2147483647).
    """
    message = {
        'msg': data_type,
        'stream_id': stream_id,
        'chunk_size': new_size
    }
    return message


def play(data_type, stream_id, name, start=-2, duration=-1, reset=False):
    """
    Construct a 'play' message to start receive audio/video data from publishers on the server.
    :param data_type: int the RTMP data type.
    :param stream_id: int the stream which the message will be sent on.
    :param name: str the name of the stream that is published/recorded on the server.
    :param start: N/A.
    :param duration: N/A.
    :param reset: N/A.
    """
    # TODO: Add start, duration, reset(?) Will it work with 'play'?
    message = {
        'msg': data_type,
        'stream_id': stream_id,
        'command': [u'play', 0, None, u'' + str(name)]
    }
    return message


def audio(data_type, stream_id, data, control, timestamp):
    """
    Construct an audio message to send audio data to the server.
    :param data_type: int the RTMP data type.
    :param stream_id: int the stream which the message will be sent on (same as the publish StreamID).
    :param data: bytes the raw audio data.
    :param control: bytes in hex the control type to send the data as.
    :param timestamp: int the timestamp of the packet.
    """
    message = {
        'msg': data_type,
        'stream_id': stream_id,
        'timestamp': timestamp,
        'body': {'control': control, 'data': data}
    }
    return message


def video(data_type, stream_id, data, control, timestamp):
    """
    Construct a video message to send video data to the server.
    :param data_type: int the RTMP data type.
    :param stream_id: int the stream which the message will be sent on (same as the publish StreamID).
    :param data: bytes the raw video data.
    :param control: bytes in hex the control type to send the data as.
    :param timestamp: int the timestamp of the packet.
    """
    message = {
        'msg': data_type,
        'stream_id': stream_id,
        'timestamp': timestamp,
        'body': {'control': control, 'data': data}
    }
    return message


def close_stream(data_type, stream_id):
    """
    Construct a 'closeStream' message to close an open stream between the client and server, by the server.
    :param data_type: int the RTMP data type.
    :param stream_id: int the stream which the message will be sent on.
    """
    message = {
        'msg': data_type,
        'stream_id': stream_id,
        'command': [u'closeStream', 0, None]
    }
    return message


def delete_stream(data_type, stream_id):
    """
    Construct a 'deleteStream' message to delete a closed stream between the client and server, on the server.
    :param data_type: int the RTMP data type.
    :param stream_id: int the stream which the message will be sent on.
    """
    message = {
        'msg': data_type,
        'stream_id': stream_id,
        'command': [u'deleteStream', 0, None, stream_id]
    }
    return message


def ping(data_type, event_type, ping_data=None):
    """
    Construct a 'PING' message to send either a 'PING_REQUEST' or 'PING_RESPONSE' to the server.
    :param data_type: int the RTMP data type.
    :param event_type: int the type of message you want to send (PING_REQUEST = 6 or PING_RESPONSE = 7).
    :param ping_data: bytes default bool None four bytes of blank data, the data you want to send to the server.
    """
    if ping_data is None:
        ping_data = b'\x00\x00\x00'

    message = {
        'msg': data_type,
        'event_type': event_type,
        'event_data': ping_data
    }
    return message
