""" """


class Node(object):

    __slots__ = ['packet', 'next_packet']

    def __init__(self, packet):
        """ """
        self.packet = packet
        self.next_packet = None

    # def next(self):
    #     """
    #
    #     :return:
    #     """
    #     return self._next_packet


# class List:
#     """ Holds a queue of RTMP Packet objects to be output. """
#
#     first_node = None
#
#     def __init__(self, first_node=None):
#         """ """
#         self.first_node = first_node


class PacketQueue:
    """ """
    # TODO: Issue with empty() or size is not kept up to date properly.

    front = None
    # TODO: Implement the last node and keep a count of it.
    back = None

    _size = -1

    def __init__(self, first_node=None):
        """ """
        self.front = first_node
        self._size = 0

    def _insert_head(self, new_node):
        """ """
        new_node.next_packet = self.front
        self.front = new_node
        self.back = new_node

    def pop(self):
        """

        :return: RtmpPacket at the front of the queue.
        """
        packet = None
        if self.empty() is False:
            # Return the packet object in the Node.
            packet = self.front.packet

            # Assign the next packet as the front.
            self.front = self.front.next_packet
            self._size -= 1

        return packet

    def push(self, packet):
        """

        :param packet: RtmpPacket object, holding packet header and content, to store in the list.
        """
        # Create the node object for the packet.
        new_node = Node(packet)

        # current_node = self.front
        # current_last_node = current_node

        if self.empty():
            self._insert_head(new_node)
        else:
            if self.back is not None:
                self.back.next_packet = new_node

                # Point the new node as the back of the queue.
                self.back = new_node
            else:
                print('PacketQueue Error: self.back was None, so RtmpPacket could not be pushed.')

            # else:
            # while current_node is not None:
            #     current_last_node = current_node
            #     current_node = current_node.next_packet

            # Set the final element of the list to be the new node.
            # current_last_node.next_packet = new_node
            # new_node.next_packet = None

        self._size += 1

    def size(self):
        """ """
        return self._size

    def empty(self):
        """ """
        # return self.front is None
        return self._size is 0
