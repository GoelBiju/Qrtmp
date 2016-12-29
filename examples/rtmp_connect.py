""" This file illustrates a sample RTMP connection with an FMS server. """

# GoelBiju (2016)

# Background regarding this example:
# ---------------------------------
# For this example we focus on utilising a stable connection between an FMS server
# and us, the client. For this we will use HDW Player's RTMP test page, located at
# http://www.hdwplayer.com/rtmp-streaming-video-player/.
#
# An example PCAP (from monitoring in WireShark) can be found in the sample_pcap folder.
# From the analysis of the PCAP file we can get the information required to establish
# a connection with the FMS server:
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
import threading

# from qrtmp import rtmp
from qrtmp.base import net_connection

# Initialise the NetConnection object.
nc = net_connection.NetConnection()

# 2. Establish our TCP connection parameters:
ip_address = '184.72.239.149'

nc.set_rtmp_server(ip_address)

# 3. Establish our RTMP connection parameters:
app = 'vod'
tc_url = 'rtmp://184.72.239.149/vod'
swf_url = 'https://www.hdwplayer.com/en/components/com_hdwplayer/player.swf?r=1520043216'
page_url = 'https://www.hdwplayer.com/rtmp-streaming-video-player/'

# 4. Setup client and its parameters:
nc.set_rtmp_parameters(app, tc_url=tc_url, swf_url=swf_url, page_url=page_url)

#   - set our rtmp client to be recognised as running Windows flash player:
# nc.flash_ver = nc.windows_flash_version
nc.return_handled_message(True)

# 5. Attempt a connection with the server and return a boolean:
#    stating if we have made a connection or not:
nc.rtmp_connect()


# def packet_loop():
#     """ A method to loop and handle the formats we receive. """
#     while nc.active_connection:
#         Read a packet we receive from the server:
        # received_packet = nc.read_packet()
        # print('Received packet:', received_packet.get_body())

# 6. Loop the replies we receive from the server and handle them
#    appropriately using the packet loop function in a thread:
# threading.Thread(target=packet_loop).start()

while nc.active_connection:
    print(nc.read_packet())

# Wait several seconds before we continue to ensure that we have a successful connection.
# time.sleep(7)

# Sending NetConnection and NetStream specific messages:
#   - call a 'createStream' request.
# nc.messages.send_create_stream()

#   - send a 'SET_BUFFER_LENGTH' User Control Message with the stream id 0 and 3000ms buffer time.
# nc.messages.send_set_buffer_length(stream_id=0, buffer_length=3000)

#   - call a 'play' request on the file we want to stream.
# mp4_file_name = 'mp4:BigBuckBunny_115k.mov'
#   - send a 'SET_BUFFER_LENGTH' User Control Message with this time a stream id of 1 and the same 3000ms buffer time.
# connection.send_play(stream_id=1, stream_name=mp4_file_name)
# connection.send_set_buffer_length(stream_id=1, buffer_length=3000)
