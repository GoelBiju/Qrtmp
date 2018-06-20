""" RtmpPacket defines a single RTMP message with its header and body contents. """

from core.protocol import rtmp_header
from core.protocol.types import enum_rtmp_packet


class RtmpPacket(object):
    """ A class to abstract the RTMP formats (received) which consists of an RTMP header and an RTMP body. """
    __slots__ = ['header', 'body', 'body_buffer', 'timestamp_absolute', 'timestamp_delta',
                 'body_is_amf', 'is_inbound', 'handled']

    def __init__(self, set_header=None, set_body=None):
        """
        Initialise the packet by providing the header information and body data.
        
        NOTE:   The packet can be initialised without providing a header or a body, however,
                in order to use this packet, you must eventually assign the correct RTMP header and body.
        
                If you initialise the packet without these two, a default header with a chunk_stream_id value of -1
                will be used to encode/decode (with no packet body).
        
                In this case, you MUST NOT use the packet for encoding/decoding to/from the RTMP stream.
        
        :param set_header: L{Header} header with the appropriate values.
        :param set_body: dict the body of the RTMP packet, with each key being a section of the RTMP packet.
        """
        self.header = rtmp_header.RtmpHeader(-1)
        self.body = None
        self.body_buffer = None

        if set_header is not None:
            self.header.chunk_type = set_header.chunk_type
            self.header.chunk_stream_id = set_header.chunk_stream_id
            self.header.timestamp = set_header.timestamp
            self.header.body_length = set_header.body_length
            self.header.data_type = set_header.data_type
            self.header.stream_id = set_header.stream_id
            self.header.extended_timestamp = set_header.extended_timestamp
            self.timestamp_absolute = set_header.timestamp_absolute
            self.timestamp_delta = set_header.timestamp_delta

        if set_body is not None:
            self.body = set_body

        self.body_is_amf = False
        self.is_inbound = False
        self.handled = False

    def get_chunk_stream_id(self):
        """
        A convenience method to allow the message chunk stream id to be retrieved without having to
        point to the RtmpHeader directly.
        
        :return header.chunk_stream_id:
        """
        return self.header.chunk_stream_id

    def get_timestamp(self):
        """
        A convenience method to allow the message timestamp to be retrieved without having to
        point to the RtmpHeader directly.
        
        :return header.timestamp:
        """
        return self.header.timestamp

    def get_body_length(self):
        """
        A convenience method to allow the message body length from the body buffer without having to
        point to the packet directly.
        
        :return len(body_buffer):
        """
        return len(self.body_buffer)

    def get_type(self):
        """
        A convenience method to allow the message data-type to be retrieved without having to
        point to the RtmpHeader directly.
        
        :return header.data_type:
        """
        return self.header.data_type

    def get_stream_id(self):
        """
        A convenience method to allow the message stream id to be retrieved without having to
        point to the RtmpHeader directly.
        
        :return header.stream_id:
        """
        return self.header.stream_id

    def set_chunk_stream_id(self, new_chunk_stream_id):
        """
        A convenience method to allow the message chunk stream id to be set without having to
        point to the RtmpHeader initially.
        
        :param new_chunk_stream_id:
        """
        self.header.chunk_stream_id = new_chunk_stream_id

    def set_timestamp(self, new_timestamp):
        """
        A convenience method ot allow the message timestamp to be set without having to
        point to the RtmpPacket header initially.
        
        :param new_timestamp:
        """
        self.header.timestamp = new_timestamp

    def set_type(self, new_data_type):
        """
        A convenience method to allow the message data type to be set without having to
        point to the RtmpPacket header initially.
        
        :param new_data_type:
        """
        self.header.data_type = new_data_type

    def set_stream_id(self, new_stream_id):
        """
        A convenience method to allow the message stream id to be set without having to
        point to the RtmpPacket header initially.
        
        :param new_stream_id:
        """
        self.header.stream_id = new_stream_id

    def get_command_name(self):
        """
        Returns the command name received from the server if the message was a COMMAND
        data-type and the body was AMF formatted.
        
        :return body['command_name']: str the command name from the COMMAND response or None if it's not present.
        """
        if self.body_is_amf and 'command_name' in self.body:
            return self.body['command_name']
        return None

    def get_transaction_id(self):
        """
        Returns the transaction id received from the server if the message was a COMMAND
        data-type and the body was AMF formatted.
        
        :return body['transaction_id']: int the transaction id of the message or None if it's not present.
        """
        if self.body_is_amf and 'transaction_id' in self.body:
            return int(self.body['transaction_id'])
        return None

    def get_command_object(self):
        """
        Returns the command object received from the server if the message was a COMMAND
        data-type and the body was AMF formatted.
        
        :return body['command_object']: list the command object retrieved from the message or None if it's not present.
        """
        if self.body_is_amf and 'command_object' in self.body:
            return self.body['command_object']
        return None

    def get_response(self):
        """
        Returns the response received from the server if the message was a COMMAND data-type
        and the body was AMF formatted.
        
        :return body['response']: list the response parsed from the AMF-encoded message or None if it's not present.
        """
        if self.body_is_amf and 'response' in self.body:
            return self.body['response']
        return None

    def get_body(self):
        """
        Returns a list of how the RTMP packet's body would be without sorting it.
        
        :return rtmp_body: list the RTMP packet's body.
        """
        if self.body_is_amf and self.header.data_type == enum_rtmp_packet.DT_COMMAND:
            rtmp_body = list((
                self.body['command_name'],
                self.body['transaction_id'],
                self.body['command_object'])
            )

            if 'response' in self.body:
                for data in range(len(self.body['response'])):
                    rtmp_body.append(self.body['response'][data])

            return rtmp_body
        return self.body

    def free_body(self):
        """ 'Free' (clear) the body content of the packet. """
        self.body = None
        return

    def finalise(self):
        """
        """
        if self.body_buffer is not None:
            self.header.body_length = len(self.body_buffer)

        if self.header.timestamp is -1:
            self.header.timestamp = 0

    def reset(self):
        """ Resets the packet's contents to the original form with an invalid header and body. """
        self.header = rtmp_header.RtmpHeader(-1)
        self.body = None
        self.body_buffer = None
        self.timestamp_absolute = None
        self.timestamp_delta = None

        self.body_is_amf = False
        self.is_inbound = False
        self.handled = False

    def __repr__(self):
        """
        Return a printable representation of the contents of the header of the RtmpPacket.
        
        :return repr: str printable representation of the header's attributes.
        """
        return '<RtmpPacket.header> chunk_type=%s chunk_stream_id=%s timestamp=%s body_length=%s data_type=%s ' \
               'stream_id=%s extended_timestamp=%s (timestamp_delta=%s, timestamp_absolute=%s) ' \
               '<inbound:%s> <handled:%s>' % \
               (self.header.chunk_type, self.header.chunk_stream_id, self.header.timestamp,
                self.header.body_length, self.header.data_type, self.header.stream_id,
                self.header.extended_timestamp, self.header.timestamp_delta, self.header.timestamp_absolute,
                self.is_inbound, self.handled)
