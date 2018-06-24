import threading
import time

from core import net_connection

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
        print(nc.read_message().get_body())


threading.Thread(target=loop).start()

time.sleep(4)

# Create a stream call.
nc.call('createStream')

# Make a call to receive video/audio data from a stream.
nc.play('honda_accord')
