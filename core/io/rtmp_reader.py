import logging, pyamf, pyamf.amf0, pyamf.amf3
from core.protocol import rtmp_packet
from core.protocol.types import enum_rtmp_packet
log = logging.getLogger(__name__)

class RtmpReader(object):
    """ """

    def __init__(self, rtmp_stream, rtmp_header_handler):
        """
        
        :param rtmp_stream:
        :param rtmp_header_handler:
        """
        self._reader_stream = rtmp_stream
        self._reader_header_handler = rtmp_header_handler
        self.chunk_size = 128
        self._previous_header = None
        return

    def __iter__(self):
        """
        
        :return:
        """
        return self

    def decode_rtmp_stream(self):
        """
        
        :return:
        """
        msg_body_len = 0
        decoded_header = self._reader_header_handler.decode_from_stream()
        decoded_body = pyamf.util.BufferedByteStream()
        print 'Decoded header: %s' % decoded_header
        if (decoded_header.data_type == -1) | (decoded_header.body_length == -1):
            decoded_header = self._previous_header
        self._previous_header = decoded_header
        while True:
            read_bytes = min(decoded_header.body_length - msg_body_len, self.chunk_size)
            decoded_body.append(self._reader_stream.read(read_bytes))
            msg_body_len += read_bytes
            if msg_body_len >= decoded_header.body_length:
                break
            next_header = self._reader_header_handler.decode_from_stream()
            if decoded_header.timestamp >= 16777215:
                self._reader_stream.read_ulong()
            assert next_header.timestamp == -1, (decoded_header, next_header)
            assert next_header.body_length == -1, (decoded_header, next_header)
            assert next_header.data_type == -1, (decoded_header, next_header)
            if not next_header.stream_id == -1:
                raise AssertionError((decoded_header, next_header))

        assert decoded_header.body_length == msg_body_len, (decoded_header, msg_body_len)
        # print (
        #  'Decoded body: ', decoded_body)
        return (
         decoded_header, decoded_body)

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
        if event['type'] == enum_rtmp_packet.SO_USE:
            assert so_body_size == 0, so_body_size
            event['data'] = ''
        else:
            if event['type'] == enum_rtmp_packet.SO_RELEASE:
                assert so_body_size == 0, so_body_size
                event['data'] = ''
            else:
                if event['type'] == enum_rtmp_packet.SO_CHANGE:
                    start_pos = body_stream.tell()
                    changes = {}
                    while body_stream.tell() < start_pos + so_body_size:
                        attrib_name = decoder.readString()
                        attrib_value = decoder.readElement()
                        assert attrib_name not in changes, (attrib_name, changes.keys())
                        changes[attrib_name] = attrib_value

                    assert body_stream.tell() == start_pos + so_body_size, (
                     body_stream.tell(), start_pos, so_body_size)
                    event['data'] = changes
                else:
                    if event['type'] == enum_rtmp_packet.SO_SEND_MESSAGE:
                        start_pos = body_stream.tell()
                        msg_params = []
                        while body_stream.tell() < start_pos + so_body_size:
                            msg_params.append(decoder.readElement())

                        assert body_stream.tell() == start_pos + so_body_size, (
                         body_stream.tell(), start_pos, so_body_size)
                        event['data'] = msg_params
                    else:
                        if event['type'] == enum_rtmp_packet.SO_CLEAR:
                            assert so_body_size == 0, so_body_size
                            event['data'] = ''
                        else:
                            if event['type'] == enum_rtmp_packet.SO_REMOVE:
                                event['data'] = decoder.readString()
                            else:
                                if event['type'] == enum_rtmp_packet.SO_USE_SUCCESS:
                                    assert so_body_size == 0, so_body_size
                                    event['data'] = ''
                                else:
                                    assert False, event['type']
        return event

    @staticmethod
    def generate_message(decoded_header, decoded_body):
        """
        Given the decoded packet header and body an RTMP Packet
        can be created with this function.
        
        :param decoded_header:
        :param decoded_body:
        :return:
        """
        received_packet = rtmp_packet.RtmpPacket(decoded_header)
        if received_packet.header.data_type == enum_rtmp_packet.DT_SET_CHUNK_SIZE:
            received_packet.body = {'chunk_size': decoded_body.read_ulong()}
        else:
            if received_packet.header.data_type == enum_rtmp_packet.DT_ABORT:
                received_packet.body = {'chunk_stream_id': decoded_body.read_ulong()}
            else:
                if received_packet.header.data_type == enum_rtmp_packet.DT_ACKNOWLEDGE_BYTES:
                    received_packet.body = {'sequence_number': decoded_body.read_ulong()}
                else:
                    if received_packet.header.data_type == enum_rtmp_packet.DT_USER_CONTROL:
                        received_packet.body = {'event_type': decoded_body.read_ushort(), 
                           'event_data': decoded_body.read()}
                    else:
                        if received_packet.header.data_type == enum_rtmp_packet.DT_WINDOW_ACKNOWLEDGEMENT_SIZE:
                            received_packet.body = {'window_acknowledgement_size': decoded_body.read_ulong()}
                        else:
                            if received_packet.header.data_type == enum_rtmp_packet.DT_SET_PEER_BANDWIDTH:
                                received_packet.body = {'window_acknowledgement_size': decoded_body.read_ulong(), 
                                   'limit_type': decoded_body.read_uchar()}
                            else:
                                if received_packet.header.data_type == enum_rtmp_packet.DT_AUDIO_MESSAGE:
                                    received_packet.body = {'control': None, 
                                       'audio_data': None}
                                    if len(decoded_body) is not 0:
                                        received_packet.body['control'] = decoded_body.read_uchar()
                                        received_packet.body['audio_data'] = decoded_body.read()
                                else:
                                    if received_packet.header.data_type == enum_rtmp_packet.DT_VIDEO_MESSAGE:
                                        received_packet.body = {'control': None, 
                                           'video_data': None}
                                        if len(decoded_body) is not 0:
                                            received_packet.body['control'] = decoded_body.read_uchar()
                                            received_packet.body['video_data'] = decoded_body.read()
                                    else:
                                        if received_packet.header.data_type == enum_rtmp_packet.DT_AMF3_COMMAND:
                                            decoder = pyamf.amf3.Decoder(decoded_body)
                                            received_packet.body = {'command_name': decoder.readElement(), 
                                               'transaction_id': decoder.readElement(), 
                                               'response': []}
                                            while not decoded_body.at_eof():
                                                received_packet.body['response'].append(decoder.readElement())

                                            received_packet.body_is_amf = True
                                        else:
                                            if received_packet.header.data_type == enum_rtmp_packet.DT_METADATA_MESSAGE:
                                                decoder = pyamf.amf0.Decoder(decoded_body)
                                                received_packet.body = {'data_name': decoder.readElement(), 
                                                   'data_content': []}
                                                while not decoded_body.at_eof():
                                                    received_packet.body['data_content'].append(decoder.readElement())

                                            else:
                                                if received_packet.header.data_type == enum_rtmp_packet.DT_COMMAND:
                                                    decoder = pyamf.amf0.Decoder(decoded_body)
                                                    command_message = {'command_name': decoder.readElement(), 
                                                       'transaction_id': decoder.readElement(), 
                                                       'command_object': decoder.readElement(), 
                                                       'response': []}
                                                    while not decoded_body.at_eof():
                                                        command_message['response'].append(decoder.readElement())

                                                    received_packet.body = command_message
                                                    received_packet.body_is_amf = True
                                                else:
                                                    assert None, received_packet
        print '[Read] %s' % repr(received_packet)
        return received_packet
