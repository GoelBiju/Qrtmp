import threading

from core import net_connection

nc = net_connection.NetConnection()

nc.set_rtmp_server('s3b78u0kbtx79q.cloudfront.net')
tc_url = 'rtmp://s3b78u0kbtx79q.cloudfront.net:1935/cfx/st'
nc.set_rtmp_parameters('cfx/st', tc_url=tc_url)
nc.flash_ver = nc.linux_flash_version

nc.set_handle_messages(True)
nc.return_handled_message(True)
nc.rtmp_connect()


def loop():
    while nc.active():
        print('Received Message:', nc.read_message().get_body())


threading.Thread(target=loop).start()
