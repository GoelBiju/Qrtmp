"""
Provides classes for creating RTMP (Real Time Message Protocol) for servers and clients.

prekageo - https://github.com/prekageo/rtmp-python/
nortxort - https://github.com/nortxort/pinylib/

RTMP general information: http://www.adobe.com/devnet/rtmp.html
RTMP Specification V1.0: http://wwwimages.adobe.com/content/dam/Adobe/en/devnet/rtmp/pdf/rtmp_specification_1.0.pdf
"""

# TODO: Information regarding background and authors.

import logging

import pyamf
import pyamf.amf0
import pyamf.amf3

from qrtmp.consts.formats import rtmp_packet
from qrtmp.consts.formats import rtmp_header
from qrtmp.consts.formats import types

log = logging.getLogger(__name__)


class RtmpReader:
    """ This class reads RTMP messages from a stream. """

    def __init__(self, rtmp_stream):
        """
        Initialise the RTMP reader and set it to read from the specified stream.
        :param rtmp_stream:
        """
        self._rtmp_stream = rtmp_stream

        # Default read chunk size.
        self.chunk_size = 128

        self.previous_header = None

    def __iter__(self):
        """

        :return self: class object
        """
        return self

    # # TODO: Not properly decoding headers may result in the loop decoding here until a restart.
    # # TODO: Read packet and the actual decoding of the packet should be in two different sections.
    # def read_packet(self):
    #     """
    #     Abstracts the process of decoding the data and then generating an RtmpPacket.
    #     :return: RtmpPacket (with header and body).
    #     """
    #     if not self.stream.at_eof():
    #         decoded_header, decoded_body = self.decode_stream()
    #         # print('Decoding next header and body ...')
    #         # print(decoded_header, decoded_body)
    #         # print('Generating next RtmpPacket ....')
    #         rtmp_packet = self.generate_packet(decoded_header, decoded_body)
    #
    #         # Handle default packet messages.
    #         if self.handle_default_messages:
    #
    #         print(rtmp_packet)
    #         return rtmp_packet
    #     else:
    #         # TODO: Is this the right raise error to call?
    #         raise StopIteration

    def decode_rtmp_stream(self):
        """
        Decodes the header and body from the RTMP stream.

        :return decoded_header, decoded_body:
        """
        # TODO: Simplify (if we can) the header decode and read process.
        # The message may span a number of chunks (each one with its own header).
        # message_body = []
        msg_body_len = 0

        decoded_header = rtmp_header.decode(self._rtmp_stream)
        decoded_body = pyamf.util.BufferedByteStream('')

        log.debug('read_packet() header %s' % decoded_header)
        # print('Decoded header: %s' % decoded_header)

        # TODO: Work out how the 'previous_header' really functions.
        # if decoded_header.data_type == -1:
        #     decoded_header = self.previous_header

        # TODO: Temporary fix to the body length being -1 due to a CONTINUATION header type 3 being received.
        if (decoded_header.data_type is -1) or (decoded_header.body_length is -1):
            decoded_header = self.previous_header
        self.previous_header = decoded_header

        # Loop and read the content of the message until we exceed or equal the expected message body size.
        while True:
            # TODO: Rename 'read_bytes'.
            # The read bytes will allow us to see the length of data we need to read from the stream.
            # We keep on passing in the body length of the full message and the
            read_bytes = min(decoded_header.body_length - msg_body_len, self.chunk_size)

            # Compare the message body length with the bytes read.
            # message_body.append(self.stream.read(read_bytes))
            # TODO: Removed the use of the list, we can use the append function in pyamf BufferedByteStream.
            decoded_body.append(self._rtmp_stream.read(read_bytes))

            msg_body_len += read_bytes
            if msg_body_len >= decoded_header.body_length:
                break

            # Decode the next header in the stream.
            next_header = rtmp_header.decode(self._rtmp_stream)

            # TODO: Evaluate the need for this; is this consistent with all RTMP implementations?
            # WORKAROUND: Even though the RTMP specification states that the extended timestamp
            #             field DOES NOT follow type 3 chunks, it seems that Flash player 10.1.85.3
            #             and Flash Media Server 3.0.2.217 send and expect this field here.
            if decoded_header.timestamp >= 0x00ffffff:
                self._rtmp_stream.read_ulong()

            # TODO: Assertion tests to see if the next header we get is generated with the constant -1 (default) values.
            assert next_header.timestamp == -1, (rtmp_header, next_header)
            assert next_header.body_length == -1, (rtmp_header, next_header)
            assert next_header.data_type == -1, (rtmp_header, next_header)
            assert next_header.stream_id == -1, (rtmp_header, next_header)

        # Make sure the body length we read is equal to the expected body length from the RTMP header.
        assert decoded_header.body_length == msg_body_len, (rtmp_header, msg_body_len)

        # decoded_body = pyamf.util.BufferedByteStream(''.join(message_body))

        return decoded_header, decoded_body

    @staticmethod
    def read_shared_object_event(body_stream, decoder):
        """
        Helper method that reads one shared object event found inside a shared
        object RTMP message.
        :param body_stream:
        :param decoder:
        """
        so_body_type = body_stream.read_uchar()
        so_body_size = body_stream.read_ulong()

        event = {'type': so_body_type}
        if event['type'] == types.SO_USE:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        elif event['type'] == types.SO_RELEASE:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        elif event['type'] == types.SO_CHANGE:
            start_pos = body_stream.tell()
            changes = {}
            while body_stream.tell() < start_pos + so_body_size:
                attrib_name = decoder.readString()
                attrib_value = decoder.readElement()
                assert attrib_name not in changes, (attrib_name, changes.keys())
                changes[attrib_name] = attrib_value
            assert body_stream.tell() == start_pos + so_body_size, \
                (body_stream.tell(), start_pos, so_body_size)
            event['data'] = changes

        elif event['type'] == types.SO_SEND_MESSAGE:
            start_pos = body_stream.tell()
            msg_params = []
            while body_stream.tell() < start_pos + so_body_size:
                msg_params.append(decoder.readElement())
            assert body_stream.tell() == start_pos + so_body_size, \
                (body_stream.tell(), start_pos, so_body_size)
            event['data'] = msg_params

        elif event['type'] == types.SO_CLEAR:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        elif event['type'] == types.SO_REMOVE:
            event['data'] = decoder.readString()

        elif event['type'] == types.SO_USE_SUCCESS:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        else:
            assert False, event['type']

        return event

    # TODO: Statistics element to each packet in the generation process, the number of the packet and the time in which
    #       it was received by the client.
    def generate_packet(self, decoded_header, decoded_body):
        """
        Generate an RtmpPacket based on the header and body we decoded from the RTMP stream.
        :param decoded_header:
        :param decoded_body:
        :return: The generated RtmpPacket or None if the packet could not be generated.
        """
        # TODO: Include in the ret, distinctly, the header and the body.
        # Decode the message based on the data-type present in the header.
        # Initialise an RTMP packet instance, to store the information we received,
        # by providing the header.
        received_packet = rtmp_packet.RtmpPacket(decoded_header)

        # Given the header message type id (data_type), let us decode the message body appropriately.
        # TODO: Re-organise these branches to match that of the RtmpWriters.
        if received_packet.header.data_type == types.DT_SET_CHUNK_SIZE:

            received_packet.body = {
                'chunk_size': decoded_body.read_ulong()
            }

        elif received_packet.header.data_type == types.DT_ABORT:

            received_packet.body = {
                'chunk_stream_id': decoded_body.read_ulong()
            }

        elif received_packet.header.data_type == types.DT_ACKNOWLEDGEMENT:

            # TODO: Make sure we can parse this acknowledgment packet.
            #       The header has a format of 3 and typically it arrives on chunk stream id 2.
            #       The body consists of a 'Sequence number' - 7+ (59 bytes) in length.

            received_packet.body = {
                'sequence_number': decoded_body.read_ulong()
            }

        elif received_packet.header.data_type == types.DT_USER_CONTROL:

            received_packet.body = {
                'event_type': decoded_body.read_ushort(),
                'event_data': decoded_body.read()
            }

        elif received_packet.header.data_type == types.DT_WINDOW_ACKNOWLEDGEMENT_SIZE:

            received_packet.body = {
                'window_acknowledgement_size': decoded_body.read_ulong()
            }

        elif received_packet.header.data_type == types.DT_SET_PEER_BANDWIDTH:

            received_packet.body = {
                'window_acknowledgement_size': decoded_body.read_ulong(),
                'limit_type': decoded_body.read_uchar()
            }

        elif received_packet.header.data_type == types.DT_AUDIO_MESSAGE:

            received_packet.body = {
                'control': None,
                'audio_data': None
            }

            # TODO: Handle in the event that there is no RTMP body in the message.
            if len(decoded_body) is not 0:
                received_packet.body['control'] = decoded_body.read_uchar()
                received_packet.body['audio_data'] = decoded_body.read()

        elif received_packet.header.data_type == types.DT_VIDEO_MESSAGE:

            received_packet.body = {
                'control': None,
                'video_data': None
            }

            # TODO: Handle in the event that there is no RTMP body in the message.
            if len(decoded_body) is not 0:
                received_packet.body['control'] = decoded_body.read_uchar()
                received_packet.body['video_data'] = decoded_body.read()

        elif received_packet.header.data_type == types.DT_AMF3_SHARED_OBJECT:

            decoder = pyamf.amf3.Decoder(decoded_body)
            obj_name = decoder.readString()
            curr_version = decoded_body.read_ulong()
            flags = decoded_body.read(8)

            # A shared object message may contain a number of events.
            events = []
            while not decoded_body.at_eof():
                so_event = self.read_shared_object_event(decoded_body, decoder)
                events.append(so_event)

            received_packet.body = {
                'obj_name': obj_name,
                'curr_version': curr_version,
                'flags': flags,
                'events': events
            }

            # The body we decoded was a Shared Object.
            received_packet.body_is_so = True

        # TODO: Implement similarly to AMF3_COMMAND.
        elif received_packet.header.data_type == types.DT_AMF3_COMMAND:

            decoder = pyamf.amf3.Decoder(decoded_body)
            # commands = []
            received_packet.body = {
                'command_name': decoder.readElement(),
                'transaction_id': decoder.readElement(),
                'response': []
            }

            # TODO: Test to see if we are able to use readElement when handling multiple objects.
            # We can keep on trying to decode an element in the byte content,
            # until the position of the indicator is at the end of the stream of data.
            # commands.append()

            # TODO: How should we handle the command object in this case? We can assume it will be a null type,
            #       however, there maybe exceptions where may get iterable content? Can we check what read as an
            #       element?
            # command_message['command_object'] = None
            while not decoded_body.at_eof():
                # commands.append(decoder.readElement())
                # command_message['response'].append(decoder.readElement())
                received_packet.body['response'].append(decoder.readElement())

            # received_packet.body = {
            #     'command': commands
            # }

            # received_packet.body = command_message

            # The body we decoded was AMF formatted.
            received_packet.body_is_amf = True

        elif received_packet.header.data_type == types.DT_DATA_MESSAGE:

            decoder = pyamf.amf0.Decoder(decoded_body)
            received_packet.body = {
                'data_name': decoder.readElement(),
                'data_content': []
            }

            while not decoded_body.at_eof():
                received_packet.body['data_content'].append(decoder.readElement())

        elif received_packet.header.data_type == types.DT_SHARED_OBJECT:

            decoder = pyamf.amf0.Decoder(decoded_body)
            obj_name = decoder.readString()
            curr_version = decoded_body.read_ulong()
            flags = decoded_body.read(8)

            # A shared object message may contain a number of events.
            events = []
            while not decoded_body.at_eof():
                so_event = self.read_shared_object_event(decoded_body, decoder)
                events.append(so_event)

            received_packet.body = {
                'obj_name': obj_name,
                'curr_version': curr_version,
                'flags': flags,
                'events': events
            }

        # TODO: Options and iteration is an issue.
        # TODO: Will reading the command_object without iteration be an issue?
        elif received_packet.header.data_type == types.DT_COMMAND:

            decoder = pyamf.amf0.Decoder(decoded_body)
            # commands = []
            command_message = {
                'command_name': decoder.readElement(),
                'transaction_id': decoder.readElement(),
                # TODO: Would we ever need to iterate here over the command_object, or is it only one object?
                'command_object': decoder.readElement(),
                'response': []
            }

            # TODO: Test to see if we are able to use readElement when handling multiple objects.
            # We can keep on trying to decode an element in the byte content,
            # until the position of the indicator is at the end of the stream of data.
            # commands.append()

            while not decoded_body.at_eof():
                # commands.append(decoder.readElement())
                command_message['response'].append(decoder.readElement())

            # received_packet.body = {
            #     'command': commands
            # }

            received_packet.body = command_message

            # The body we decoded was AMF formatted.
            received_packet.body_is_amf = True

        else:
            # TODO: An assertion here to none causes the whole script on the output application to stop.
            #       We need to display this another way.
            assert None, received_packet

        log.debug('Generated RtmpPacket: %r' % repr(received_packet))
        # print('[Read] %s' % repr(received_packet))
        return received_packet
