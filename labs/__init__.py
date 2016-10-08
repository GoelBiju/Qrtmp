"""
This package is responsible for encoding/decoding RTMP (and AMF) messages.
The sub-modules contains classes/methods to establish a connection to a RTMP server,
and to read/write amf messages on a connected stream.

It also contains the PySocks (https://github.com/Anorov/PySocks) module to enable
a connection to an RTMP server via a proxy.
"""

# TODO: Added exceptions to __init__.

__author__ = 'GoelBiju'
__authors__ = ['prekageo', 'Anorov', 'hydralabs', 'nortxort']
__credits__ = __authors__
