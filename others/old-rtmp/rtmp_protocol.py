""" Provides classes for creating RTMP (Real Time Message Protocol) servers and clients. """

# This is an edited version of the old library developed by Prekageo and mixed with edits from Nortxort.
# Prekageo - https://github.com/prekageo/rtmp-python/
# Nortxort - https://github.com/nortxort/pinylib/

# Some edits made by GoelBiju (https://github.com/GoelBiju/)
# RTMP general information: http://www.adobe.com/devnet/rtmp.html
# RTMP Specification V1.0: http://wwwimages.adobe.com/content/dam/Adobe/en/devnet/rtmp/pdf/rtmp_specification_1.0.pdf

# TODO: Add in the extra imports.

import socket
import socks
import random
import logging

import data_types
import so_event_types
import user_control_types

# import pyamf.amf0
# import pyamf.amf3
# import pyamf.util.pure

import rtmp_protocol_base


log = logging.getLogger(__name__)


class FileDataTypeMixIn(pyamf.util.pure.DataTypeMixIn):
    """
    Provides a wrapper for a file object that enables reading and writing of raw
    data types for the file.
    """

    def __init__(self, fileobject):
        self.fileobject = fileobject
        pyamf.util.pure.DataTypeMixIn.__init__(self)

    def read(self, length):
        return self.fileobject.read(length)

    def write(self, data):
        self.fileobject.write(data)

    def flush(self):
        self.fileobject.flush()

    @staticmethod
    def at_eof():
        return False


class RtmpReader:
    """ This class reads RTMP messages from a stream. """

    # Default read chunk size.
    chunk_size = 128

    def __init__(self, stream):
        """ Initialize the RTMP reader and set it to read from the specified stream. """
        self.stream = stream

    def __iter__(self):
        return self

    def next(self):
        """ Read one RTMP message from the stream and return it. """
        if self.stream.at_eof():
            raise StopIteration

        # Read the message into body_stream. The message may span a number of
        # chunks (each one with its own header).
        message_body = []
        msg_body_len = 0
        header = rtmp_protocol_base.header_decode(self.stream)

        while True:
            read_bytes = min(header.body_length - msg_body_len, self.chunk_size)
            message_body.append(self.stream.read(read_bytes))
            msg_body_len += read_bytes
            if msg_body_len >= header.body_length:
                break

            # Decode the next header in the stream.
            rtmp_protocol_base.header_decode(self.stream)

            # WORKAROUND: even though the RTMP specification states that the
            # extended timestamp field DOES NOT follow type 3 chunks, it seems
            # that Flash player 10.1.85.3 and Flash Media Server 3.0.2.217 send
            # and expect this field here.
            if header.timestamp >= 0x00ffffff:
                self.stream.read_ulong()

        assert header.body_length == msg_body_len, (header, msg_body_len)
        body_stream = pyamf.util.BufferedByteStream(''.join(message_body))

        # Decode the message based on the data-type present in the header.
        ret = {'msg': header.data_type}

        if ret['msg'] == data_types.NONE:
            log.warning('WARNING: Message with no data-type received.')
            return self.next()

        elif ret['msg'] == data_types.UNKNOWN:
            return self.next()

        elif ret['msg'] == data_types.USER_CONTROL:
            ret['stream_id'] = header.stream_id
            ret['event_type'] = body_stream.read_ushort()
            ret['event_data'] = body_stream.read()

        elif ret['msg'] == data_types.ACKNOWLEDGEMENT:
            return self.next()

        elif ret['msg'] == data_types.WINDOW_ACK_SIZE:
            ret['window_ack_size'] = body_stream.read_ulong()

        elif ret['msg'] == data_types.SET_PEER_BANDWIDTH:
            ret['window_ack_size'] = body_stream.read_ulong()
            ret['limit_type'] = body_stream.read_uchar()

        elif ret['msg'] == data_types.SHARED_OBJECT:
            decoder = pyamf.amf0.Decoder(body_stream)
            obj_name = decoder.readString()
            curr_version = body_stream.read_ulong()
            flags = body_stream.read(8)

            # A shared object message may contain a number of events.
            events = []
            while not body_stream.at_eof():
                event = self.read_shared_object_event(body_stream, decoder)
                events.append(event)

            ret['obj_name'] = obj_name
            ret['curr_version'] = curr_version
            ret['flags'] = flags
            ret['events'] = events

        elif ret['msg'] == data_types.AMF3_SHARED_OBJECT:
            decoder = pyamf.amf3.Decoder(body_stream)
            obj_name = decoder.readString()
            curr_version = body_stream.read_ulong()
            flags = body_stream.read(8)
            # A shared object message may contain a number of events.
            events = []
            while not body_stream.at_eof():
                event = self.read_shared_object_event(body_stream, decoder)
                events.append(event)

            ret['obj_name'] = obj_name
            ret['curr_version'] = curr_version
            ret['flags'] = flags
            ret['events'] = events

        elif ret['msg'] == data_types.COMMAND:
            ret['stream_id'] = header.stream_id
            decoder = pyamf.amf0.Decoder(body_stream)
            commands = []
            while not body_stream.at_eof():
                commands.append(decoder.readElement())
            ret['command'] = commands

        elif ret['msg'] == data_types.AMF3_COMMAND:
            decoder = pyamf.amf3.Decoder(body_stream)
            commands = []
            while not body_stream.at_eof():
                commands.append(decoder.readElement())
            ret['command'] = commands

        elif ret['msg'] == data_types.SET_CHUNK_SIZE:
            ret['chunk_size'] = body_stream.read_ulong()

        elif ret['msg'] == data_types.DATA_MESSAGE:
            ret['stream_id'] = header.stream_id
            ret['metadata'] = message_body

        elif ret['msg'] == data_types.AUDIO_MESSAGE:
            ret['stream_id'] = header.stream_id
            ret['control'] = body_stream.read_uchar()
            ret['data'] = body_stream.read()

        elif ret['msg'] == data_types.VIDEO_MESSAGE:
            ret['stream_id'] = header.stream_id
            ret['control'] = body_stream.read_uchar()
            ret['data'] = body_stream.read()

        else:
            assert False, header

        log.debug('recv %r', ret)
        return ret

    @staticmethod
    def read_shared_object_event(body_stream, decoder):
        """
        Helper method that reads one shared object event found inside a shared
        object RTMP message.
        """
        so_body_type = body_stream.read_uchar()
        so_body_size = body_stream.read_ulong()

        event = {'type': so_body_type}
        if event['type'] == so_event_types.USE:
            assert so_body_size == 0, so_body_size
            event['data'] = ''
        elif event['type'] == so_event_types.RELEASE:
            assert so_body_size == 0, so_body_size
            event['data'] = ''
        elif event['type'] == so_event_types.CHANGE:
            start_pos = body_stream.tell()
            changes = {}
            while body_stream.tell() < start_pos + so_body_size:
                attrib_name = decoder.readString()
                attrib_value = decoder.readElement()
                assert attrib_name not in changes, (attrib_name, changes.keys())
                changes[attrib_name] = attrib_value
            assert body_stream.tell() == start_pos + so_body_size,\
                (body_stream.tell(), start_pos, so_body_size)
            event['data'] = changes
        elif event['type'] == so_event_types.SEND_MESSAGE:
            start_pos = body_stream.tell()
            msg_params = []
            while body_stream.tell() < start_pos + so_body_size:
                msg_params.append(decoder.readElement())
            assert body_stream.tell() == start_pos + so_body_size,\
                (body_stream.tell(), start_pos, so_body_size)
            event['data'] = msg_params
        elif event['type'] == so_event_types.CLEAR:
            assert so_body_size == 0, so_body_size
            event['data'] = ''
        elif event['type'] == so_event_types.REMOVE:
            event['data'] = decoder.readString()
        elif event['type'] == so_event_types.USE_SUCCESS:
            assert so_body_size == 0, so_body_size
            event['data'] = ''
        else:
            assert False, event['type']

        return event


class RtmpWriter:
    """ This class writes RTMP messages into a stream. """

    # Default write chunk size.
    chunk_size = 128

    def __init__(self, stream):
        """ Initialize the RTMP writer and set it to write into the specified stream. """
        self.stream = stream

    def flush(self):
        """ Flush the underlying stream. """
        self.stream.flush()

    # MESSAGES
    def write(self, message):
        log.debug('send %r', message)
        """ Encode and write the specified message into the stream. """
        datatype = message['msg']
        body_stream = pyamf.util.BufferedByteStream()
        encoder = pyamf.amf0.Encoder(body_stream)

        if datatype == data_types.USER_CONTROL:
            body_stream.write_ushort(message['event_type'])
            body_stream.write(message['event_data'])

        elif datatype == data_types.WINDOW_ACK_SIZE:
            body_stream.write_ulong(message['window_ack_size'])

        elif datatype == data_types.SET_CHUNK_SIZE:
            body_stream.write_long(message['chunk_size'])

        elif datatype == data_types.SET_PEER_BANDWIDTH:
            body_stream.write_ulong(message['window_ack_size'])
            body_stream.write_uchar(message['limit_type'])

        elif datatype == data_types.COMMAND:
            for command in message['command']:
                encoder.writeElement(command)

        elif datatype == data_types.AMF3_COMMAND:
            encoder = pyamf.amf3.Encoder(body_stream)
            for command in message['command']:
                encoder.writeElement(command)

        elif datatype == data_types.SHARED_OBJECT:
            encoder.serialiseString(message['obj_name'])
            body_stream.write_ulong(message['curr_version'])
            body_stream.write(message['flags'])

            for event in message['events']:
                self.write_shared_object_event(event, body_stream)

        elif datatype == data_types.AUDIO_MESSAGE:
            # Write an audio message into the stream.
            body_stream.write_uchar(message['body']['control'])  # Write control
            body_stream.write(message['body']['data'])  # Write data

        elif datatype == data_types.VIDEO_MESSAGE:
            # Write an video message into the stream.
            body_stream.write_uchar(message['body']['control'])  # Write control
            body_stream.write(message['body']['data'])  # Write data

        else:
            assert False, message

        self.send_msg(datatype, body_stream.getvalue(), message)

    @staticmethod
    def write_shared_object_event(event, body_stream):
        inner_stream = pyamf.util.BufferedByteStream()
        encoder = pyamf.amf0.Encoder(inner_stream)

        event_type = event['type']
        if event_type == so_event_types.USE:
            assert event['data'] == '', event['data']
        elif event_type == so_event_types.CHANGE:
            for attrib_name in event['data']:
                attrib_value = event['data'][attrib_name]
                encoder.serialiseString(attrib_name)
                encoder.writeElement(attrib_value)
        elif event['type'] == so_event_types.CLEAR:
            assert event['data'] == '', event['data']
        elif event['type'] == so_event_types.USE_SUCCESS:
            assert event['data'] == '', event['data']
        else:
            assert False, event

        body_stream.write_uchar(event_type)
        body_stream.write_ulong(len(inner_stream))
        body_stream.write(inner_stream.getvalue())

    # MESSAGES
    def send_msg(self, datatype, body, message=None, ch_id=3, st_id=0, timestamp=0):
        """
        Helper method that sends the specified message into the stream.
        Takes care to prepend the necessary headers and split the message into
        appropriately sized chunks.
        """
        # Values that just work. :-)
        if 1 <= datatype <= 7:
            channel_id = 2
            stream_id = 0
        else:
            channel_id = ch_id
            stream_id = st_id

        if 'stream_id' in message:
            # Set the stream ID, if it was specified.
            stream_id = message['stream_id']

            # Assign the channel ID depending if the command word is present in the body.
            if datatype == data_types.SET_CHUNK_SIZE:
                channel_id = 2
            elif 'play' in body:
                channel_id = 8
            elif 'publish' in body:
                channel_id = 8
            elif datatype == data_types.AUDIO_MESSAGE or datatype == data_types.VIDEO_MESSAGE:
                channel_id = random.randint(10, 50)
                if 'timestamp' in message:
                    timestamp = message['timestamp']
            elif 'closeStream' in body:
                channel_id = 8
            elif 'deleteStream' in body:
                channel_id = 3

        # Generate the RTMP message header.
        header = rtmp_protocol_base.Header(
            channel_id=channel_id,
            stream_id=stream_id,
            data_type=datatype,
            body_length=len(body),
            timestamp=timestamp)

        # Encode the RTMP message header.
        rtmp_protocol_base.header_encode(self.stream, header)

        # Write chunks into the stream (message body split up with the same header).
        for i in xrange(0, len(body), self.chunk_size):
            chunk = body[i:i + self.chunk_size]
            self.stream.write(chunk)
            if i+self.chunk_size < len(body):
                rtmp_protocol_base.header_encode(self.stream, header, header)


class FlashSharedObject:
    """
    This class represents a Flash Remote Shared Object. Its data are located
    inside the self.data dictionary.
    """

    def __init__(self, name):
        """
        Initialize a new Flash Remote SO with a given name and empty data.
        """
        self.name = name
        self.data = {}
        self.use_success = False

    def use(self, writer):
        """
        Initialize usage of the SO by contacting the Flash Media Server. Any
        remote changes to the SO should be now propagated to the client.
        """
        self.use_success = False

        msg = {
            'msg': data_types.SHARED_OBJECT,
            'curr_version': 0,
            'flags': '\x00\x00\x00\x00\x00\x00\x00\x00',
            'events': [
                {
                    'data': '',
                    'type': so_event_types.USE
                }
            ],
            'obj_name': self.name
        }
        writer.write(msg)
        writer.flush()

    def handle_message(self, message):
        """
        Handle an incoming RTMP message. Check if it is of any relevance for the
        specific SO and process it, otherwise ignore it.
        """
        if message['msg'] == data_types.SHARED_OBJECT and message['obj_name'] == self.name:
            events = message['events']

            if not self.use_success:
                assert events[0]['type'] == so_event_types.USE_SUCCESS, events[0]
                assert events[1]['type'] == so_event_types.CLEAR, events[1]
                events = events[2:]
                self.use_success = True

            self.handle_events(events)
            return True
        else:
            return False

    def handle_events(self, events):
        """ Handle SO events that target the specific SO. """
        for event in events:
            event_type = event['type']
            if event_type == so_event_types.CHANGE:
                for key in event['data']:
                    self.data[key] = event['data'][key]
                    self.on_change(key)
            elif event_type == so_event_types.REMOVE:
                key = event['data']
                assert key in self.data, (key, self.data.keys())
                del self.data[key]
                self.on_delete(key)
            elif event_type == so_event_types.SEND_MESSAGE:
                self.on_message(event['data'])
            else:
                assert False, event

    def on_change(self, key):
        """ Handle change events for the specific shared object. """
        pass

    def on_delete(self, key):
        """ Handle delete events for the specific shared object. """
        pass

    def on_message(self, data):
        """ Handle message events for the specific shared object. """
        pass


class RtmpClient:
    """ Represents an RTMP client. """

    def __init__(self, ip, port, tc_url, page_url, swf_url, app, swf_version,
                 room_type, prefix, room, version, cookie, account='', proxy=None):
        """ Initialize a new RTMP client. """
        self.socket = None
        self.stream = None
        self.file = None
        self.reader = None
        self.writer = None

        self.ip = ip
        self.port = port
        self.tc_url = tc_url
        self.page_url = page_url
        self.swf_url = swf_url
        self.app = app
        self.swf_version = swf_version
        self.shared_objects = []
        self.room_type = room_type
        self.prefix = prefix
        self.room_name = room
        self.version = version
        self.cookie = cookie
        self.account = account
        self.proxy = proxy

    @staticmethod
    def create_random_bytes(length):
        """ Creates random bytes for the handshake. """
        ran_bytes = ''
        i, j = 0, 0xff
        for x in xrange(0, length):
            ran_bytes += chr(random.randint(i, j))
        return ran_bytes

    # PRECONNECTION
    def handshake(self):
        """ Perform the handshake sequence with the server. """

        self.stream.write_uchar(3)
        c1 = rtmp_protocol_base.HandshakePacket()
        c1.first = 0
        c1.second = 0
        c1.payload = self.create_random_bytes(1528)
        c1.encode(self.stream)
        self.stream.flush()

        self.stream.read_uchar()
        s1 = rtmp_protocol_base.HandshakePacket()
        s1.decode(self.stream)

        c2 = rtmp_protocol_base.HandshakePacket()
        c2.first = s1.first
        c2.second = s1.second
        c2.payload = s1.payload
        c2.encode(self.stream)
        self.stream.flush()

        s2 = rtmp_protocol_base.HandshakePacket()
        s2.decode(self.stream)

    # PRECONNECTION
    def connect_rtmp(self, connect_params):
        """ Initiate a NetConnection with a Flash Media Server. """
        msg = {
            'msg': data_types.COMMAND,
            'command':
            [
                u'connect',
                1,
                {
                    'app': u'' + self.app,
                    'flashVer': u'' + self.swf_version,
                    'swfUrl': u'' + self.swf_url,
                    'tcUrl': u'' + self.tc_url,
                    'fpad': False,
                    'capabilities': 239,
                    'audioCodecs': 3575,
                    'videoCodecs': 252,
                    'videoFunction': 0,              # SUPPORT_VID_CLIENT_SEEK: default 0, it can be switched on (1)
                                                     #  if the client supports frame-accurate seeks.
                    'pageUrl': self.page_url,
                    'objectEncoding': 0
                },
                {
                    'cookie': u'' + self.cookie,     # Cauth cookie,
                    'type': u'' + self.room_type,    # 'show' if it's a registered room, else 'default',
                    'account': u'' + self.account,   # Tinychat account name,
                    'room': u'' + self.room_name,    # Name of the room,
                    'prefix': u'' + self.prefix,     # 'tinychat' or 'greenroom', respectively,
                    'version': u'' + self.version,   # Desktop version.
                }
            ]
        }

        msg['command'].extend(connect_params)
        self.writer.write(msg)
        self.writer.flush()

    # NETCONNECTION
    def connect(self, connect_params):
        """ Connect to the server with the given connect parameters. """
        if self.proxy:
            parts = self.proxy.split(':')
            ip = parts[0]
            port = int(parts[1])

            ps = socks.socksocket()
            ps.set_proxy(socks.HTTP, addr=ip, port=port)
            self.socket = ps
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Initialise basic socket and streams to temporarily record the data we receive.
        self.socket.connect((self.ip, self.port))
        self.file = self.socket.makefile()
        self.stream = FileDataTypeMixIn(self.file)

        # Turn on TCP keep-alive.
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        # Perform the handshake with the server and set the read and write classes to the stream.
        # Start the connection afterwards.
        self.handshake()
        self.reader = RtmpReader(self.stream)
        self.writer = RtmpWriter(self.stream)
        self.connect_rtmp(connect_params)

    # NETCONNECTION
    def handle_packet(self, amf_data):
        """ Handle default packets based on data-types. """
        if amf_data['msg'] == data_types.USER_CONTROL and amf_data['event_type'] == user_control_types.PING_REQUEST:
            ping_response = {
                'msg': data_types.USER_CONTROL,
                'event_type': user_control_types.PING_RESPONSE,
                'event_data': amf_data['event_data']
            }
            self.writer.write(ping_response)
            self.writer.flush()
            log.info('Handled PING_REQUEST packet with response: %s' % ping_response)
            return True

        elif amf_data['msg'] == data_types.WINDOW_ACK_SIZE:
            # The windows acknowledgement may actually vary, rather than the asserted one, we do not
            # actually handle for this.
            assert amf_data['window_ack_size'] == 2500000, amf_data
            ack_msg = {
                'msg': data_types.WINDOW_ACK_SIZE,
                'window_ack_size': amf_data['window_ack_size']
            }
            self.writer.write(ack_msg)
            self.writer.flush()
            log.info('Handled WINDOW_ACK_SIZE packet with response: %s' % ack_msg)
            return True

        elif amf_data['msg'] == data_types.SET_PEER_BANDWIDTH:
            assert amf_data['window_ack_size'] == 2500000, amf_data
            # Should we consider the other limit types: hard and soft (we can just assume dynamic)?
            assert amf_data['limit_type'] == 2, amf_data
            log.info('Handled SET_PEER_BANDWIDTH packet: %s' % amf_data)
            return True

        elif amf_data['msg'] == data_types.USER_CONTROL and amf_data['event_type'] == user_control_types.STREAM_BEGIN:
            assert amf_data['event_type'] == user_control_types.STREAM_BEGIN, amf_data
            assert amf_data['event_data'] == '\x00\x00\x00\x00', amf_data
            log.info('Handled STREAM_BEGIN packet: %s' % amf_data)
            return True

        elif amf_data['msg'] == data_types.SET_CHUNK_SIZE:
            assert 0 < amf_data['chunk_size'] <= 65536, amf_data
            self.reader.chunk_size = amf_data['chunk_size']
            log.info('Handled SET_CHUNK_SIZE packet with new chunk size: %s' % self.reader.chunk_size)
            return True

        else:
            return False

    # NETCONNECTION
    def shutdown(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def call(self, process_name, parameters=None, trans_id=0):
        """ Runs remote procedure calls (RPC) at the receiving end. """
        if parameters is None:
            parameters = {}

        msg = {
            'msg': data_types.COMMAND,
            'command':
            [
                process_name,
                trans_id,
                parameters
            ]
        }

        self.writer.write(msg)
        self.writer.flush()

    # NETCONNECTION
    def shared_object_use(self, so):
        """ Use a shared object and add it to the managed list of shared objects (SOs). """
        if so in self.shared_objects:
            return
        so.use(self.reader, self.writer)
        self.shared_objects.append(so)
