import threading
import time
import sys

from core import net_connection
from core.io.rtmp_writer import FLV

# from flashmedia import FLV, FLVError
# from flashmedia.tag import ScriptData
#
#
# def test_flv(filename):
#     """
#
#     :param filename:
#     :return:
#     """
#     fd_video = open(filename, 'rb')
#
#     try:
#         flv_video = FLV(fd_video)
#     except FLVError as err:
#         print("Invalid FLV")
#         sys.exit()
#
#     tag_count = 0
#
#     # Iterate over tags
#     for tag in flv_video:
#         # tag.data contains the parsed data, it's either a AudioData, VideoData or ScriptData object
#         try:
#             print("Tag with timestamp %d contains %s, data length: %s" % (tag.timestamp, tag.data, len(tag.data.data)))
#             tag_count += 1
#             print(tag_count)
#         except:
#             pass
#
#         # Modify the metadata
#         if isinstance(tag.data, ScriptData) and tag.data.name == "onMetaData":
#             # tag.data.value["description"] = "This file has been modified through python!"
#             print(tag.timestamp, repr(tag.data))
#
#         # Serialize the tag back into bytes
#         # data = tag.serialize()
#
#
# test_flv('video.flv')

flv_writer = FLV()
flv_writer.open('test.flv', type='record')

nc = net_connection.NetConnection()

# TODO: AMF3 createStream does not work.
# TODO: Implement getStreamLength to get duration for stream.
# TODO: Incorrect reading of timestamps in aggregate messages.

# nc.set_rtmp_server('s3b78u0kbtx79q.cloudfront.net')
nc.set_rtmp_server('184.18.181.10')
# tc_url = 'rtmp://s3b78u0kbtx79q.cloudfront.net:1935/cfx/st'
tc_url = 'rtmp://10.bteradio.com/vod'
swf_url = 'http://bteradio.com/swfs/videoPlayer.swf'
page_url = 'http://bteradio.com/BTEPlayer.html?source=rtmp://10.bteradio.com/vod/test.flv&type=vod&idx=8'
# nc.set_rtmp_parameters('cfx/st', tc_url=tc_url)
nc.set_rtmp_parameters('vod', tc_url=tc_url)

nc.flash_ver = nc.windows_flash_version
nc.set_handle_messages(True)
nc.return_handled_message(True)

# Connect to the rtmp stream.
nc.rtmp_connect()


def loop():
    while nc.active():
        try:
            message = nc.read_message()
            if message is not None:
                # print(message.get_body())

                message_type = message.get_type()
                # Handle audio/video messages coming through in order to save them.
                if message_type == 0x08 or message_type == 0x09:

                    # print('Message original timestamp:', message.get_timestamp())

                    d = message.get_timestamp() - nc._rtmp_reader.prevts.get((message.get_stream_id(),
                                                                             message.get_type()), 0)
                    offset = nc._rtmp_reader.tsoffset.get((message.get_stream_id(), message.get_type()), 0)

                    if d < 0:
                        # log.warning('Timestamp moving backwards! stream=%i, type=%i, d=%i, from %i to %i',
                        #             m.streamid, m.type, d, m.timestamp - d, m.timestamp)
                        print('Timestamp moving backwards.')
                        offset -= d
                        nc._rtmp_reader.tsoffset[message.get_stream_id(), message.get_type()] = offset

                    elif d > 2000:
                        # log.warning('Timestamp jumping forwards! stream=%i, type=%i, d=%i, from %i to %i',
                        #             m.streamid, m.type, d, m.timestamp - d, m.timestamp)
                        print('Timestamp jumping forward.')

                    nc._rtmp_reader.prevts[message.get_stream_id(), message.get_type()] = message.get_timestamp()

                    message.set_timestamp(message.get_timestamp() + offset)

                    # print(message.body_buffer)
                    flv_writer.write(message)
                    # print('Written A/V message to file:', repr(message))

                    if message.get_timestamp() == 31596:
                        flv_writer.close()

                elif message_type == 0x12 and message.get_body() is not None:
                    message_body = message.get_body()
                    print(message_body)

                    if message_body['data_name'] == 'onPlayStatus':
                        print('Got end of play.')
                        flv_writer.close()

        except Exception as err:
            print(err)
            flv_writer.close()
            break


threading.Thread(target=loop).start()

time.sleep(4)

# Change the rate at which data comes in on NetConnection stream.
nc.messages.send_set_buffer_length(0, 300)

# Create a stream call.
nc.call('createStream')

nc.messages.send_set_buffer_length(1, 36000000)

# Make a call to receive video/audio data from a stream.
# nc.play('honda_accord', start_time=-1)
nc.play('test', start_time=-1)
