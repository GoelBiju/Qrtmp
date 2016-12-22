import pyamf
import pyamf.util.pure


class SocketDataTypeMixInFile(pyamf.util.pure.DataTypeMixIn):
    """

    """

    def __init__(self, socket_object):
        """

        :param socket_object:
        """
        self.fileobject = socket_object
        pyamf.util.pure.DataTypeMixIn.__init__(self)

    def read(self, length):
        """

        :param length:
        :return:
        """
        return self.fileobject.read(length)

    def write(self, data):
        """

        :param data:
        """
        self.fileobject.write(data)

    def flush(self):
        """

        :return:
        """
        self.fileobject.flush()

    # TODO: Figure out what this method does.
    @staticmethod
    def at_eof():
        """

        :return False:
        """
        return False


# TODO: If the socket is a file object and FileDataTypeMixIn inherited read/write, we can just alter
#       that to read data.
# TODO: Move this to it's own file, we will be retrieving data from this.
# TODO: We will have to enclose all BufferedByteStream actions with a recv/send to make sure
#       the data is present to do these actions.
# class RtmpByteStream(pyamf.util.pure.BufferedByteStream):
#     """
#     This is a wrapper for the buffered-bytestream class within PyAMF, which inherits
#     the functions from the StringIOProxy and the FileDataTypeMixIn file-object.
#
#     We will abstract the process of reading or writing data within the socket in this class.
#     """
#
#     def __init__(self, socket_object, buf_size=128):
#         """
#         To initialise we will need the socket object to be provided
#         :param socket_object:
#         :param buf_size: int (default 128) the buffer size to read/write data in the socket.
#         """
#         self.socket = socket_object
#         self.buf_size = int(buf_size)
#
#     def set_internal_buf_size(self, new_buf_size):
#         """
#         Set the amount of data we want to read from the socket usually.
#         :param new_buf_size:
#         """
#         self.buf_size = new_buf_size
#
#     def read(self, length=-1):
#         """
#         Override the default file-object read function and get the data from socket
#         with respect to our buffer size.
#         """
