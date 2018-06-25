import threading
import time
# import sys

from core import net_connection
from core.io.rtmp_writer import FLV

# from core.io.flashmedia import FLV, FLVError
# from core.io.flashmedia.tag import ScriptData
#
# fd_video = open('test.flv', 'rb')
#
# try:
#     flv_video = FLV(fd_video)
# except FLVError as err:
#     print("Invalid FLV")
#     sys.exit()
#
#
# # Iterate over tags
# for tag in flv_video:
#     # tag.data contains the parsed data, it's either a AudioData, VideoData or ScriptData object
#     print("Tag with timestamp %d contains %s" % (tag.timestamp, tag.data))
#
#     # Modify the metadata
#     if isinstance(tag.data, ScriptData) and tag.data.name == "onMetaData":
#     #     tag.data.value["description"] = "This file has been modified through python!"
#         continue
#
#     # Serialize the tag back into bytes
#     # data = tag.serialize()


flv_writer = FLV()
flv_writer.open('test.flv', type='record')

nc = net_connection.NetConnection()

# TODO: Stream possibly sends aggregate messages.
# TODO: Implement getStreamLength to get duration for stream.
#       Currently I have not managed to implement reading of aggregate messages.
nc.set_rtmp_server('s3b78u0kbtx79q.cloudfront.net')
tc_url = 'rtmp://s3b78u0kbtx79q.cloudfront.net:1935/cfx/st'
nc.set_rtmp_parameters('cfx/st', tc_url=tc_url)

nc.flash_ver = nc.windows_flash_version
nc.set_handle_messages(True)
nc.return_handled_message(True)

# Connect to the rtmp stream.
nc.rtmp_connect()


def loop():
    while nc.active():
        message = nc.read_message()
        if message is not None:
            message_type = message.get_type()
            if message_type == 0x08 or message_type == 0x09:
                print('A/V:', message)
                # print(message.body_buffer)
                flv_writer.write(message)
                print('Written A/V message to file.')

            elif message_type == 0x12 and message.get_body() is not None:
                message_body = message.get_body()
                print(message_body)

                if message_body['data_name'] == 'onPlayStatus':
                    print('Got end of play.')
                    flv_writer.close()


threading.Thread(target=loop).start()

time.sleep(4)

# Change the rate at which data comes in on NetConnection stream.
nc.messages.send_set_buffer_length(0, 300)

# Create a stream call.
nc.call('createStream')

# Make a call to receive video/audio data from a stream.
nc.play('honda_accord')

# Change the rate at which data comes in on NetStream - stream id 1 which is playing the stream.
nc.messages.send_set_buffer_length(1, 36000000)


