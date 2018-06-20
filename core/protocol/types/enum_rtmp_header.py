"""
Identifies the RTMP header types and RTMP chunk streams.

HR: RTMP Packet - header type.
CS: RTMP Packet - chunk stream id.
"""

HR_TYPE_0_FULL = 0

HR_TYPE_1_SAME_STREAM = 1

HR_TYPE_2_SAME_LENGTH_AND_STREAM = 2

HR_TYPE_3_CONTINUATION = 3

CS_CONTROL = 2

CS_NET_CONNECTION = 3

CS_NET_STREAM = 8

CS_CUSTOM_AUDIO = 6

CS_CUSTOM_VIDEO = 7
