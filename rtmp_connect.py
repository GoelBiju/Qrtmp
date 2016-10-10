""" This file illustrates a sample connection to an FMS server. """

# GoelBiju (2016)

# Background regarding this example:
# ---------------------------------
# For this example we focus on utilising a stable connection between an FMS server
# and us, the client. For this we will use HDW Player's RTMP test page, located at
# http://www.hdwplayer.com/rtmp-streaming-video-player/.
#
# An example PCAP (from monitoring in WireShark) can be found in the sample_pcap folder.
# From the analysis of the PCAP file we can derive the pertinent information required to
# establish a successful connection with the FMS server:
#
# WireShark Data:
# --------------
# RTMP URL: rtmp://184.72.239.149/vod
# RTMP Body:
#     String 'connect'
#     Number 1
#     Object (11 items)
#         AMF0 type: Object (0x03)
#         Property 'app' String 'vod'
#         Property 'flashVer' String 'WIN 23,0,0,162'
#         Property 'swfUrl' String 'https://www.hdwplayer.com/en/components/com_hdwplayer/player.swf?r=1520043216'
#         Property 'tcUrl' String 'rtmp://184.72.239.149/vod'
#         Property 'fpad' Boolean false
#         Property 'capabilities' Number 239
#         Property 'audioCodecs' Number 3575
#         Property 'videoCodecs' Number 252
#         Property 'videoFunction' Number 1
#         Property 'pageUrl' String 'https://www.hdwplayer.com/rtmp-streaming-video-player/'
#         Property 'objectEncoding' Number 0
#         End Of Object Marker

# 1. Import essential modules.
import time
import threading

from qrtmp import rtmp

# 2. Establish our TCP connection parameters:
ip_address = '184.72.239.149'

# 3. Establish our RTMP connection parameters:
app = 'vod'
tc_url = 'rtmp://184.72.239.149/vod'
swf_url = 'https://www.hdwplayer.com/en/components/com_hdwplayer/player.swf?r=1520043216'
page_url = 'https://www.hdwplayer.com/rtmp-streaming-video-player/'

# 4. Setup client and its parameters:
connection = rtmp.RtmpClient(ip_address, app=app, tc_url=tc_url, page_url=page_url)

#   - set our rtmp client to be recognised as running on Windows:
connection.flash_ver = connection.windows_flash_version

# 5. Attempt a connection with the server and return a boolean:
# stating if we have made a connection or not:
valid_connection = connection.connect()


def packet_loop():
    """ A method to loop and handle the packets we receive. """
    while valid_connection:
        # Read a packet we receive from the server:
        received_packet = connection.reader.read_packet()
        print('Packet:', received_packet.body)

        # Handle the packet by the internal parser:
        # Some typical RTMP messages we may need to handle include that of:
        #   - 'Window Acknowledgement Size'
        #   - 'Set Peer Bandwidth'
        #   - 'Stream Begin'
        #   - 'Set Chunk Size'
        #   - '_result' (NetConnection.Connect.Success)

        handled = connection.handle_packet(received_packet)
        if handled:
            print('Handled packet: ', received_packet.body)


# 6. Loop the replies we receive from the server and handle them
#    appropriately using the packet loop function in a thread:
threading.Thread(target=packet_loop).start()

# Wait several seconds before we continue to ensure that we have a successful connection.
time.sleep(7)

# Sending NetConnection and NetStream specific messages:
#   - call a 'createStream' request.
connection.call('createStream', transaction_id=2)  # typically 2 since we already used 1 for the connection packet.
#   - send a 'SET_BUFFER_LENGTH' User Control Message with the stream id 0 and 3000ms buffer time.
connection.send_set_buffer_length(0, 3000)

#   - call a 'play' request on the file we want to stream.
mp4_file_name = 'mp4:BigBuckBunny_115k.mov'
#   - send a 'SET_BUFFER_LENGTH' User Control Message with this time a stream id of 1 and the same 3000ms buffer time.
#     NOTE: We override the chunk stream id here since play should be sent on the STREAM CHANNEL (0x08).
connection.call('play', parameters=[mp4_file_name], stream_id=1, override_csid=0x08)
connection.send_set_buffer_length(1, 3000)