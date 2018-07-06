""" """

import logging

import os
import struct

import pyamf
import pyamf.amf0
import pyamf.amf3

from core.protocol import rtmp_packet
from core.protocol.types import enum_rtmp_packet, enum_rtmp_header

log = logging.getLogger(__name__)


class FLV(object):
    '''An FLV file which converts between RTMP message and FLV tags.'''

    def __init__(self):
        self.fname = self.fp = self.type = None
        self.tsp = self.tsr = 0;
        self.tsr0 = None

    def open(self, path, type='read', mode=0775):
        '''Open the file for reading (type=read) or writing (type=record or append).'''
        if str(path).find('/../') >= 0 or str(path).find('\\..\\') >= 0: raise ValueError('Must not contain .. in name')
        # if _debug: print 'opening file', path
        print('opening file: ', path)
        self.tsp = self.tsr = 0;
        self.tsr0 = None;
        self.tsr1 = 0;
        self.type = type

        if type in ('record', 'append'):
            try:
                os.makedirs(os.path.dirname(path), mode)
            except:
                pass
            if type == 'record' or not os.path.exists(path):  # if file does not exist, use record mode
                self.fp = open(path, 'w+b')
                self.fp.write('FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00')  # the header and first previousTagSize
                self.writeDuration(0.0)
            else:
                self.fp = open(path, 'r+b')
                self.fp.seek(-4, os.SEEK_END)
                ptagsize, = struct.unpack('>I', self.fp.read(4))
                self.fp.seek(-4 - ptagsize, os.SEEK_END)
                bytes = self.fp.read(ptagsize)
                type, len0, len1, ts0, ts1, ts2, sid0, sid1 = struct.unpack('>BBHBHBBH', bytes[:11])
                ts = (ts0 << 16) | (ts1 & 0x0ffff) | (ts2 << 24)
                self.tsr1 = ts + 20;  # some offset after the last packet
                self.fp.seek(0, os.SEEK_END)
        else:
            self.fp = open(path, 'rb')
            magic, version, flags, offset = struct.unpack('!3sBBI', self.fp.read(9))
            # if _debug: print 'FLV.open() hdr=', magic, version, flags, offset
            print('FLV.open() hdr=', magic, version, flags , offset)

            if magic != 'FLV': raise ValueError('This is not a FLV file')
            if version != 1: raise ValueError('Unsupported FLV file version')
            if offset > 9: self.fp.seek(offset - 9, os.SEEK_CUR)
            self.fp.read(4)  # ignore first previous tag size
        return self

    def close(self):
        '''Close the underlying file for this object.'''
        # if _debug: print 'closing flv file'
        print('closing flv file')
        if self.type in ('record', 'append') and self.tsr0 is not None:
            self.writeDuration((self.tsr - self.tsr0) / 1000.0)
            # self.writeDuration(120.0)
        if self.fp is not None:
            try:
                self.fp.close()
            except:
                pass
            self.fp = None

    def delete(self, path):
        '''Delete the underlying file for this object.'''
        try:
            os.unlink(path)
        except:
            pass

    def writeDuration(self, duration):
        # if _debug: print 'writing duration', duration
        print('writing duration', duration)

        # TODO: Convert to use PyAMF
        # output = amf.BytesIO()
        # amfWriter = amf.AMF0(output)  # TODO: use AMF3 if needed
        # amfWriter.write('onMetaData')
        # amfWriter.write({"duration": duration, "videocodecid": 2})
        # output.seek(0);
        # data = output.read()

        temp_buffer = pyamf.util.BufferedByteStream('')
        amf0_encoder = pyamf.amf0.Encoder(temp_buffer)

        amf0_encoder.writeElement('onMetaData')
        meta_data = {"duration": duration, "videocodecid": 2}
        amf0_encoder.writeElement(meta_data)

        data = temp_buffer.getvalue()

        length, ts = len(data), 0

        # TODO: Base on METADATA data type
        data = struct.pack('>BBHBHB', enum_rtmp_packet.DT_METADATA_MESSAGE,
                           (length >> 16) & 0xff, length & 0x0ffff, (ts >> 16) & 0xff,
                           ts & 0x0ffff, (ts >> 24) & 0xff) + '\x00\x00\x00' + data
        data += struct.pack('>I', len(data))
        lastpos = self.fp.tell()
        if lastpos != 13: self.fp.seek(13, os.SEEK_SET)
        self.fp.write(data)
        if lastpos != 13: self.fp.seek(lastpos, os.SEEK_SET)

    def write(self, message):
        '''Write a message to the file, assuming it was opened for writing or appending.'''
        #        if message.type == Message.VIDEO:
        #            self.videostarted = True
        #        elif not hasattr(self, "videostarted"): return
        # TODO: Audio and video data type
        if message.get_type() == enum_rtmp_packet.DT_AUDIO_MESSAGE or message.get_type() == enum_rtmp_packet.DT_VIDEO_MESSAGE:
            # length, ts = message.size, message.time
            # TODO: Timestamp issue - does not match what is actually downloaded.
            length, ts = message.get_body_length(), message.get_timestamp()
            # if _debug: print 'FLV.write()', message.type, ts
            print('FLV.write()', message.get_type(), ts)
            if self.tsr0 is None: self.tsr0 = ts - self.tsr1
            self.tsr, ts = ts, ts - self.tsr0
            # if message.type == Message.AUDIO: print 'w', message.type, ts
            # print(ts, message.body_buffer)
            data = struct.pack('>BBHBHB', message.get_type(), (length >> 16) & 0xff, length & 0x0ffff, (ts >> 16) & 0xff,
                               ts & 0x0ffff, (ts >> 24) & 0xff) + '\x00\x00\x00' + message.body_buffer
            data += struct.pack('>I', len(data))
            self.fp.write(data)

    def seek(self, offset):
        '''For file reader, try seek to the given time. The offset is in millisec'''
        if self.type == 'read':
            # if _debug: print 'FLV.seek() offset=', offset, 'current tsp=', self.tsp
            print('FLV.seek() offset=', offset, 'current tsp=', self.tsp)
            self.fp.seek(0, os.SEEK_SET)
            magic, version, flags, length = struct.unpack('!3sBBI', self.fp.read(9))
            if length > 9: self.fp.seek(length - 9, os.SEEK_CUR)
            self.fp.seek(4, os.SEEK_CUR)  # ignore first previous tag size
            self.tsp, ts = int(offset), 0
            while self.tsp > 0 and ts < self.tsp:
                bytes = self.fp.read(11)
                if not bytes: break
                type, len0, len1, ts0, ts1, ts2, sid0, sid1 = struct.unpack('>BBHBHBBH', bytes)
                length = (len0 << 16) | len1;
                ts = (ts0 << 16) | (ts1 & 0x0ffff) | (ts2 << 24)
                self.fp.seek(length, os.SEEK_CUR)
                ptagsize, = struct.unpack('>I', self.fp.read(4))
                if ptagsize != (length + 11): break
            # if _debug: print 'FLV.seek() new ts=', ts, 'tell', self.fp.tell()
            print('FLV.seek() new ts=', ts, 'tell', self.fp.tell())


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

                # TODO: Chunkstream for netstream messages should be already otherwise specified.
                #       Should not be here, hardcoded..
                if write_packet.body['command_name'] == 'play':
                    write_packet.header.chunk_stream_id = enum_rtmp_header.CS_NET_STREAM
                else:
                    write_packet.header.chunk_stream_id = enum_rtmp_header.CS_NET_CONNECTION

                if write_packet.header.data_type == enum_rtmp_packet.DT_AMF3_COMMAND:
                    encoder = pyamf.amf3.Encoder(temp_buffer)
                else:
                    encoder = pyamf.amf0.Encoder(temp_buffer)

                # Write the invoked commands name and the message transaction id.
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

                if 'options' in write_packet.body:
                    options = write_packet.body['options']
                    if type(options) is list:
                        if len(options) is not 0:
                            for optional_parameter in options:
                                encoder.writeElement(optional_parameter)
                    else:
                        print('RtmpWriter Error: Options is not a list, instead: ', type(options))

                write_packet.body_is_amf = True
                if transaction_id != 0:
                    self.transaction_id += 1
        else:
            assert False, write_packet

        write_packet.body_buffer = temp_buffer.getvalue()
        print('Body buffer:', len(write_packet.body_buffer))
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
