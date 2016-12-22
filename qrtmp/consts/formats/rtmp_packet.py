""" Classes relevant to the basic RTMP packet structure; the packet header and body. """

import qrtmp.consts.formats.rtmp_header as rtmp_header


# TODO: Any other essential packet methods?
class RtmpPacket(object):
    """ A class to abstract the RTMP formats (received) which consists of an RTMP header and an RTMP body. """

    # Set up a packet blank header and blank body.
    header = rtmp_header.Header(-1)
    body = None

    # Set up header descriptors.
    header_timestamp_is_delta = None

    # Set up body descriptors.
    body_is_amf = None
    body_is_so = None

    # TODO: Possible "mutate" or "merge" header function to make it small as possible if we give it the current point
    #       in the RTMP stream and it judges by looking at the previous packet what it is.
    #       Or maybe give it the previous packet and current channels/streams being used.

    # TODO: Raise error message in the event that an invalid header and body is trying to be sent, this should prevent
    #       the message from going into the stream and crashing it.
    def __init__(self, set_header=None, set_body=None):
        """
        Initialise the packet by providing the header information and body data.

        NOTE:   The packet can be initialised without providing a header or a body, however,
                in order to use this packet, you must eventually assign the correct RTMP header and body.

                If you initialise the packet without these two, a default header with a chunk_stream_id value of -1
                will be used to encode/decode (with no packet body).

                In this case, you MUST NOT use the packet for encoding/decoding to/from the RTMP stream.

        :param set_header: L{Header} header with the appropriate values.
        :param set_body: dict the body of the rtmp packet, with each key being a section of the RTMP packet.
        """
        # TODO: Formatting of names: _chunk_type, _extended_timestamp, _timestamp_absolute or _timestamp_delta?
        # Handle the packet header.
        if set_header is not None:
            self.header.chunk_type = set_header.chunk_type
            self.header.chunk_stream_id = set_header.chunk_stream_id

            self.header.timestamp = set_header.timestamp
            self.header.body_length = set_header.body_length
            self.header.data_type = set_header.data_type
            self.header.stream_id = set_header.stream_id
            self.header.extended_timestamp = set_header.extended_timestamp

            # self.timestamp_absolute = set_header.timestamp_absolute
            self.timestamp_delta = set_header.timestamp_delta

        # TODO: Add this into the RtmpHeader.
        # Allow the recognition of whether the timestamp received from the server or being sent to the server
        # is delta (otherwise absolute).
        self.header_timestamp_is_delta = False

        # Handle the packet body.
        if set_body is not None:
            self.body = set_body

        # TODO: Add convenience methods to get the fixed parts of the AMF body
        #       (only applicable to command messages for now).
        # TODO: Possibly have an AMF body format attributes (.body_amf/.is_amf?)
        #       if the message received was a command (RPC).
        # Allow the recognition as whether the encoded/decoded was/is AMF (plainly or from a Shared Object).
        # This can only be used once the packet has been initialised.
        self.body_is_amf = False
        self.body_is_so = False

        # Handled descriptor to see if the packet was handled by default (otherwise it was not).
        self.handled = False

    # TODO: A 'get_type' method should also be added.
    # TODO: Abstract all the essential header variables that we can set e.g. data (message) type, body, timestamp.
    # Packet attribute convenience methods:
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

    # TODO: Should we have a convenience method for setting the timestamp; how do we handle
    #       the timestamp delta and an absolute timestamp in this case?
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

    # TODO: Should we have finalise for the chunk_type?
    # TODO: Is the order of branches in this method correct?
    def finalise(self):
        """
        Allows the packet to be finalised once all the necessary information is present.

        NOTE: This is only to be called once the packet's header is ready to be encoded and
              written onto the stream. We will need the chunk_stream_id, data_type, body.
        """
        # If the timestamp has still not been established by this point,
        # we set it to default (zero).
        if self.header.timestamp is -1:
            self.header.timestamp = 0

        if self.body is not None:
            self.header.body_length = len(self.body)

    # AMF-specific convenience methods:
    def get_command_name(self):
        """
        Returns the command name received from the server if the message was a COMMAND
        data-type and the body was AMF formatted.

        :return body['command_name']: str the command name from the COMMAND response or None if it's not present.
        """
        if self.body_is_amf and 'command_name' in self.body:
            return self.body['command_name']
        else:
            return None

    def get_transaction_id(self):
        """
        Returns the transaction id received from the server if the message was a COMMAND
        data-type and the body was AMF formatted.

        :return body['transaction_id']: int the transaction id of the message or None if it's not present.
        """
        if self.body_is_amf and 'transaction_id' in self.body:
            return int(self.body['transaction_id'])
        else:
            return None

    def get_command_object(self):
        """
        Returns the command object received from the server if the message was a COMMAND
        data-type and the body was AMF formatted.

        :return body['command_object']: list the command object retrieved from the message or None if it's not present.
        """
        if self.body_is_amf and 'command_object' in self.body:
            return self.body['command_object']
        else:
            return None

    def get_response(self):
        """
        Returns the response received from the server if the message was a COMMAND
        data-type and the body was AMF formatted.

        :return body['response']: list the response parsed from the AMF-encoded message or None if it's not present.
        """
        if self.body_is_amf and 'response' in self.body:
            return self.body['response']
        else:
            return None

    # TODO: Make a raw body contents function to get all the body content in a list. Like previously to use iparam.
    # def get_body(self):
    #     """
    #
    #     :return: list
    #     """
    #     pass

    # Handler convenience methods.
    def free_body(self):
        """ 'Free' (clear) the body content of the packet. """
        self.body = None

    def reset_packet(self):
        """ Resets the packet's contents to the original form with an invalid header and body. """
        self.header = rtmp_header.Header(-1)
        self.body = None

    # TODO: If we print() or log() with string formatting we are unable to use '__repr__'.
    def __repr__(self):
        """
        Return a printable representation of the contents of the header of the RTMPPacket.
        NOTE: We do not return a representation in the event that the packet was initialised plainly,
              with no RTMP header.

        :return repr: str printable representation of the header's attributes.
        """
        if self.header.chunk_type is not -1:  # timestamp_delta=%s
            return '<RtmpPacket.header> chunk_type=%s chunk_stream_id=%s timestamp=%s body_length=%s ' \
                   'data_type=%s stream_id=%s extended_timestamp=%s (timestamp_absolute=%s) <handled:%s>' % \
                   (self.header.chunk_type, self.header.chunk_stream_id, self.header.timestamp,
                    self.header.body_length, self.header.data_type, self.header.stream_id,
                    self.header.extended_timestamp, self.timestamp_delta, self.handled)  # self.timestamp_absolute,
