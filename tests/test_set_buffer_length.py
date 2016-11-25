""" Test packing/unpacking User Control Message - SET_BUFFER_LENGTH event data (packed body). """

import struct

# Buffer length as a single integer (in milliseconds).
buffer_length = 3000

# Packed stream id of zero (4-byte) - unsigned integer.
print([struct.pack('>I', 0)])

# Unpacked stream id from the binary data, resulting in zero.
print([struct.unpack('>I', '\x00\x00\x00\x00')])

# Pack the buffer length (4-byte) - unsigned integer.
print([struct.pack('>I', buffer_length)])
