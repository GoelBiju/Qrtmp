import os
import struct


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
        output = amf.BytesIO()
        amfWriter = amf.AMF0(output)  # TODO: use AMF3 if needed
        amfWriter.write('onMetaData')
        amfWriter.write({"duration": duration, "videocodecid": 2})
        output.seek(0);
        data = output.read()
        length, ts = len(data), 0

        # TODO: Base on METADATA data type
        data = struct.pack('>BBHBHB', Message.DATA, (length >> 16) & 0xff, length & 0x0ffff, (ts >> 16) & 0xff,
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
        if message.type == Message.AUDIO or message.type == Message.VIDEO:
            length, ts = message.size, message.time
            # if _debug: print 'FLV.write()', message.type, ts
            if self.tsr0 is None: self.tsr0 = ts - self.tsr1
            self.tsr, ts = ts, ts - self.tsr0
            # if message.type == Message.AUDIO: print 'w', message.type, ts
            data = struct.pack('>BBHBHB', message.type, (length >> 16) & 0xff, length & 0x0ffff, (ts >> 16) & 0xff,
                               ts & 0x0ffff, (ts >> 24) & 0xff) + '\x00\x00\x00' + message.data
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