""" """

import pyamf
import pyamf.util.pure


class BaseConnectionDataMix(pyamf.util.pure.DataTypeMixIn):
    """
    """

    def __init__(self, socket_object):
        """
        
        :param socket_object:
        """
        self.file_object = socket_object
        pyamf.util.pure.DataTypeMixIn.__init__(self)

    def read(self, length):
        """
        
        :param length:
        :return:
        """
        return self.file_object.read(length)

    def write(self, data):
        """
        
        :param data:
        :return:
        """
        self.file_object.write(data)

    def flush(self):
        """
        
        :return:
        """
        self.file_object.flush()

    def at_eof(self):
        """
        
        :return:
        """
        return False
