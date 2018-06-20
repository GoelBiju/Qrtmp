""" """

import logging

import pyamf
import pyamf.amf0
import pyamf.amf3

from core.protocol import rtmp_packet
from core.protocol.types import enum_rtmp_packet, enum_rtmp_header

log = logging.getLogger(__name__)


class RtmpWriter(object):
    """ """

    def __init__(self, rtmp_stream, rtmp_header_handler):
        """
        
        :param rtmp_stream:
        :param rtmp_header_handler:
        """
        self._writer_stream = rtmp_stream
        self._writer_header_handler = rtmp_header_handler

        self.chunk_size = 128
        self.transaction_id = 0

    def _stream_flush(self):
        """ """
        self._writer_stream.flush()

    @staticmethod
    def new_packet():
        """
        
        :return:
        """
        return rtmp_packet.RtmpPacket()

    def setup_packet(self, write_packet):
        """
        
        :param write_packet:
        """
        temp_buffer = pyamf.util.BufferedByteStream('')

        if write_packet.header.data_type == enum_rtmp_packet.DT_SET_CHUNK_SIZE:
            write_packet.header.chunk_stream_id = enum_rtmp_header.CS_CONTROL
            write_packet.header.stream_id = 0

            temp_buffer.write_long(write_packet.body['chunk_size'])

        elif write_packet.header.data_type == enum_rtmp_packet.DT_ACKNOWLEDGE_BYTES:
                write_packet.header.chunk_stream_id = enum_rtmp_header.CS_CONTROL
                write_packet.header.stream_id = 0

                temp_buffer.write_ulong(write_packet.body['sequence_number'])

        elif write_packet.header.data_type == enum_rtmp_packet.DT_ABORT:
                write_packet.header.chunk_stream_id = enum_rtmp_header.CS_CONTROL
                write_packet.header.stream_id = 0

                temp_buffer.write_ulong(write_packet.body['chunk_stream_id'])

        elif write_packet.header.data_type == enum_rtmp_packet.DT_USER_CONTROL:
                write_packet.header.chunk_stream_id = enum_rtmp_header.CS_CONTROL
                write_packet.header.stream_id = 0

                if 'event_type' in write_packet.body:
                    temp_buffer.write_ushort(write_packet.body['event_type'])

                if 'event_data' in write_packet.body:
                    temp_buffer.write(write_packet.body['event_data'])

        elif write_packet.header.data_type == enum_rtmp_packet.DT_WINDOW_ACKNOWLEDGEMENT_SIZE:
                write_packet.header.chunk_stream_id = enum_rtmp_header.CS_CONTROL
                write_packet.header.stream_id = 0

                temp_buffer.write_ulong(write_packet.body['window_acknowledgement_size'])

        elif write_packet.header.data_type == enum_rtmp_packet.DT_SET_PEER_BANDWIDTH:
                write_packet.header.chunk_stream_id = enum_rtmp_header.CS_CONTROL
                write_packet.header.stream_id = 0

                temp_buffer.write_ulong(write_packet.body['window_acknowledgement_size'])
                temp_buffer.write_uchar(write_packet.body['limit_type'])

        elif write_packet.header.data_type == enum_rtmp_packet.DT_AUDIO_MESSAGE:
                write_packet.header.chunk_stream_id = enum_rtmp_header.CS_CUSTOM_AUDIO
                write_packet.header.stream_id = 1

                temp_buffer.write_uchar(write_packet.body['control'])
                temp_buffer.write(write_packet.body['audio_data'])

        elif write_packet.header.data_type == enum_rtmp_packet.DT_VIDEO_MESSAGE:
                write_packet.header.chunk_stream_id = enum_rtmp_header.CS_CUSTOM_VIDEO
                write_packet.header.stream_id = 1

                temp_buffer.write_uchar(write_packet.body['control'])
                temp_buffer.write(write_packet.body['video_data'])

        elif write_packet.header.data_type == enum_rtmp_packet.DT_COMMAND or \
                write_packet.header.data_type == enum_rtmp_packet.DT_AMF3_COMMAND:

                if write_packet.body['command_name'] == 'play':
                    write_packet.header.chunk_stream_id = enum_rtmp_header.CS_NET_STREAM
                else:
                    write_packet.header.chunk_stream_id = enum_rtmp_header.CS_NET_CONNECTION

                if write_packet.header.data_type == enum_rtmp_packet.DT_AMF3_COMMAND:
                    encoder = pyamf.amf3.Encoder(temp_buffer)
                else:
                    encoder = pyamf.amf0.Encoder(temp_buffer)

                encoder.writeElement(write_packet.body['command_name'])
                transaction_id = write_packet.body['transaction_id']
                encoder.writeElement(transaction_id)

                command_object = write_packet.body['command_object']
                if type(command_object) is list:
                    if len(command_object) is not 0:
                        for command_info in command_object:
                            encoder.writeElement(command_info)
                else:
                    encoder.writeElement(command_object)

                if write_packet.body['command_name'] != 'play':
                    encoder.writeElement(None)

                options = write_packet.body['options']
                if type(options) is list:
                    if len(options) is not 0:
                        for optional_parameter in options:
                            encoder.writeElement(optional_parameter)

                write_packet.body_is_amf = True
                if transaction_id != 0:
                    self.transaction_id += 1
        else:
            assert False, write_packet

        write_packet.body_buffer = temp_buffer.getvalue()
        print('Body buffer:', write_packet.body_buffer)
        write_packet.finalise()

        self.send_packet(write_packet)

    @staticmethod
    def write_shared_object_event(event, body_stream):
        """
        
        :param event: dict
        :param body_stream: PyAMF BufferedByteStream object
        """
        inner_stream = pyamf.util.BufferedByteStream()
        encoder = pyamf.amf0.Encoder(inner_stream)

        event_type = event['type']
        if event_type == enum_rtmp_packet.SO_USE:
            assert event['data'] == '', event['data']

        elif event_type == enum_rtmp_packet.SO_CHANGE:
            for attrib_name in event['data']:
                attrib_value = event['data'][attrib_name]
                encoder.serialiseString(attrib_name)
                encoder.writeElement(attrib_value)

        elif event['type'] == enum_rtmp_packet.SO_CLEAR:
            assert event['data'] == '', event['data']

        elif event['type'] == enum_rtmp_packet.SO_USE_SUCCESS:
            assert event['data'] == '', event['data']

        else:
            assert False, event

        body_stream.write_uchar(event_type)
        body_stream.write_ulong(len(inner_stream))
        body_stream.write(inner_stream.getvalue())

    def send_packet(self, packet):
        """
        
        :param packet:
        """
        self._writer_header_handler.encode_into_stream(packet.header)
        print('Encoded first header into stream:', packet.header)

        for i in xrange(0, packet.header.body_length, self.chunk_size):
            write_size = i + self.chunk_size
            chunk = packet.body_buffer[i:write_size]
            self._writer_stream.write(chunk)

            if write_size < packet.header.body_length:
                print('Writing remaining body header.')
                self._writer_header_handler.encode_into_stream(packet.header, packet.header)

        self._stream_flush()
        print('Flushed RTMP stream and sent all written data.')


class FlashSharedObject:
    """ This class represents a Flash Remote Shared Object. """

    def __init__(self, name):
        """
        Initialize a new Flash Remote SO with a given name and empty data.
        
        NOTE: The data regarding the shared object is located inside the self.data dictionary.
        """
        self.name = name
        self.data = {}
        self.use_success = False

    def use(self, writer):
        """
        Initialize usage of the SO by contacting the Flash Media Server.
        Any remote changes to the SO should be now propagated to the client.
        
        :param writer:
        """
        self.use_success = False
        so_use = writer.new_packet()

        so_use.header.data_type = enum_rtmp_packet.DT_SHARED_OBJECT
        so_use.body = {
            'curr_version': 0,
            'flags': '\x00\x00\x00\x00\x00\x00\x00\x00',
            'events': [{
                'data': '',
                'type': enum_rtmp_packet.SO_USE}],
            'obj_name': self.name
        }

        writer.setup_packet(so_use)

    def handle_message(self, message):
        """
        Handle an incoming RTMP message. Check if it is of any relevance for the
        specific SO and process it, otherwise ignore it.
        
        :param message:
        """
        if message['data_type'] == enum_rtmp_packet.DT_SHARED_OBJECT and message['obj_name'] == self.name:
            events = message['events']

            if not self.use_success:
                assert events[0]['type'] == enum_rtmp_packet.SO_USE_SUCCESS, events[0]
                assert events[1]['type'] == enum_rtmp_packet.SO_CLEAR, events[1]
                events = events[2:]
                self.use_success = True

            self.handle_events(events)
            return True
        return False

    def handle_events(self, events):
        """
        Handle SO events that target the specific SO.
        
        :param events:
        """
        for event in events:
            event_type = event['type']
            if event_type == enum_rtmp_packet.SO_CHANGE:
                for key in event['data']:
                    self.data[key] = event['data'][key]
                    self.on_change(key)

            elif event_type == enum_rtmp_packet.SO_REMOVE:
                key = event['data']
                assert key in self.data, (key, self.data.keys())
                del self.data[key]
                self.on_delete(key)

            elif event_type == enum_rtmp_packet.SO_SEND_MESSAGE:
                self.on_message(event['data'])

            elif not False:
                raise AssertionError(event)

    @staticmethod
    def on_change(key):
        """
        Handle change events for the specific shared object.
        
        :param key:
        """
        pass

    @staticmethod
    def on_delete(key):
        """
        Handle delete events for the specific shared object.
        
        :param key:
        """
        pass

    @staticmethod
    def on_message(data):
        """
        Handle message events for the specific shared object.
        
        :param data:
        """
        pass
