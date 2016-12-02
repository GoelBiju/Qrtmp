""" A broadcast/camera managing module to handle streaming FLV data. """

import os
import struct

import pyamf.amf0
import pyamf.amf3

# A/V types
AUDIO = 0x08
VIDEO = 0x09

# Video control types
KEY_FRAME = 0x12
INTER_FRAME = 0x22
DISPOSABLE_FRAME = 0x32
GENERATED_FRAME = 0x42

manager_state = '<FLVManager>'


class FLV(object):
    """ """

    def __init__(self, state, path):
        """
        Allows for an FLV object to be created and with it it's information to be stored.

        :param state: str 'read' or 'write' depending if the file exists and we should read from the file or
                      if we should write to a new file in a location.
        :param path: str the path to read from or write to.
        """
        if state == 'read':
            self.flv_content = open(path, 'rb')
        elif state == 'write':
            self.flv_content = open(path, 'w+b')

        self.flv_location = path
        self.tags = None

        self.tsr0 = None
        self.tsa = 0
        self.tsv = 0

    def set_tags(self, flv_tags):
        """
        Set the retrieved tags into the flv object.
        :param flv_tags:
        """
        self.tags = flv_tags


# TODO: Inherit a core background class for parsing - FLVHandle?
class FLVManager:
    """ The FLV manager instance. """

    # TODO: Init with also the configurations to broadcast, audio/video on/off & length, time..
    def __init__(self):
        """ """
        self._flv_tags = []

    @staticmethod
    def load_flv(flv_location):
        """
        Load an FLV file to parse it's tag data from.
        :param flv_location:
        """
        loaded_flv = FLV('read', flv_location)
        return loaded_flv

    def new_flv(self, flv_location):
        """
        Allows for a new FLV file to be created in a specified folder.

        :param flv_location:
        :return:
        """
        write_flv = FLV('write', flv_location)
        new_flv = self.setup_new_flv(write_flv)
        return new_flv

    def get_tags(self, tag_flv):
        """
        Retrieve the frames
        :return:
        """
        read_flv = self.iterate_frames(tag_flv)
        read_flv.flv_content.close()
        return read_flv

    def write_duration(self, write_flv, duration):
        """

        @param duration:
        @return:
        """
        amf0_buffer = pyamf.util.BufferedByteStream()
        encoder = pyamf.amf0.Encoder(amf0_buffer)
        encoder.writeElement('onMetaData')
        encoder.writeElement({'duration': 0.0, 'videocodecid': 2})

        amf0_buffer.seek(0)
        data_buffer = amf0_buffer.read()
        length, ts = len(data_buffer), 0

        packed_data = struct.pack('>BBHBHB', 0x12, (length >> 16) & 0xff, length & 0x0ffff, (ts >> 16) & 0xff,
                                  ts & 0x0ffff, (ts >> 24) & 0xff) + '\x00\x00\x00' + data_buffer
        packed_data += struct.pack('>I', len(packed_data))

        last_position = write_flv.flv_content.tell()

        if last_position != 13:
            write_flv.flv_content.seek(13, os.SEEK_SET)
            write_flv.flv_content.write(packed_data)

            write_flv.flv_content.seek(last_position, os.SEEK_SET)

        return write_flv

    def setup_new_flv(self, write_flv):
        """
        """
        # Write the FLV header into the file.
        write_flv.flv_content.write('FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00')
        return write_flv

    def write_flv_data(self, write_flv, tag_type, data, timestamp, size):
        """

        :param tag_type:
        :param data:
        :param timestamp:
        :param size:
        :return:
        """
        if tag_type == AUDIO or tag_type == VIDEO:
            length, ts = size, timestamp

            if write_flv.tsr0 is None:
                write_flv.tsr0 = ts - write_flv.tsr1
            write_flv.tsr, ts = ts, ts - write_flv.tsr0

            packed_data = struct.pack('>BBHBHB', tag_type, (length >> 16) & 0xff, length & 0x0ffff, (ts >> 16) & 0xff,
                                      ts & 0x0ffff, (ts >> 24) & 0xff) + '\x00\x00\x00' + data
            packed_data += struct.pack('>I', len(packed_data))

            write_flv.flv_content.write(packed_data)

    @staticmethod
    def iterate_frames(read_flv):
        """
        Loop over the content of an FLV file to generate tag/frame data.
        Once looped, return a list containing all the appropriate packet(s) i.e. audio/video packet.
        :param read_flv: FLV object with the data (opened to read bytes) to be loaded.
        """
        magic, version, flags, offset = struct.unpack('!3sBBI', read_flv.flv_content.read(9))

        if magic != 'FLV':
            raise ValueError('This is not an FLV file.')

        if version != 1:
            raise ValueError('Unsupported FLV file version.')

        if offset > 9:
            read_flv.flv_content.seek(offset - 9, os.SEEK_CUR)

        read_flv.flv_content.read(4)

        saved_tags = []

        while True:
            data_bytes = read_flv.flv_content.read(11)
            if len(data_bytes) is not 0:
                data_type, len0, len1, ts0, ts1, ts2, sid0, sid1 = struct.unpack('>BBHBHBBH', data_bytes)
                read_length = (len0 << 16) | len1
                ts = (ts0 << 16) | (ts1 & 0x0ffff) | (ts2 << 24)
                # TODO: An extra character at the start of the body causes the body to become unreadable,
                #       reading past the first character fixes this.
                body = read_flv.flv_content.read(read_length)[1:]

                previous_tag_size, = struct.unpack('>I', read_flv.flv_content.read(4))
                if previous_tag_size != (read_length + 11):
                    # print('Invalid previous tag size found:', previous_tag_size)
                    pass

                # control = 0x22
                if data_type == AUDIO:
                    read_flv.tsa, ts = ts, ts - max(read_flv.tsa, read_flv.tsv)
                    control = 0x22
                elif data_type == VIDEO:
                    read_flv.tsv, ts = ts, ts - max(read_flv.tsa, read_flv.tsv)
                    control = INTER_FRAME
                else:
                    continue

                if ts < 0:
                    ts = 0
                # elif ts > 0:
                #     time.sleep(ts/1000.0)

                # print([body])

                saved_tags.append([data_type, body, control, ts])
            else:
                break

        read_flv.tags = saved_tags
        # print('Length of tags saved:', len(saved_tags))
        # print("DONE!")
        return read_flv

        # Parse the tags from the FLV file.
        # try:
        #     flv_content = FLV(flv_file)
        # except FLVError as ex:
            # On an error print the exception and return null.
            # print('%s Invalid FLV: %s' % (manager_state, ex))
            # return None

        # List where all the tag data will be stored within.
        # saved_tags = []

        # print('%s Iterating over FLV content.' % manager_state)
        # Iterate over tags.
        # for tag in flv_content:
            # On any Null type, stop iteration of FLV tags/frames.
            # if tag is not None:
                # Skip metadata in the file.
                # if isinstance(tag.data, ScriptData) and tag.data.name == 'onMetaData':
                #     continue
                # else:
                #     Load audio tag.
                    # if tag.type == AUDIO:
                    #     control = 0x22

                        # Record tag/frame information.
                        # saved_tags.append([tag.type, tag.data.data, control, tag.timestamp])

                    # Load video tag.
                    # elif tag.type == VIDEO:
                    #     control = KEY_FRAME

                        # Record tag/frame information.
                        # saved_tags.append([tag.type, tag.data.data, control, tag.timestamp])

        # print('%s Saved frames (%s) into tag list.' % (manager_state, len(saved_tags)))
        # Returned the iterated tags.

        # self.read_flv_tags = saved_tags


manage = FLVManager()
# flv_file = manage.load_flv('football.flv')
# read_flv = manage.get_tags(flv_file)

flv_file = manage.new_flv('sample.flv')
