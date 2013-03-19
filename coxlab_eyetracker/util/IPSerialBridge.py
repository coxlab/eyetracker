#
#  IPSerialBridge.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 11/12/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#

import errno
import logging
import time
import socket
import select


class IPSerialBridge:

    def __init__(self, address, port):
        self.socket = None
        self.address = address
        self.port = port

    def __del__(self):
        self.disconnect()

    def connect(self):
        logging.info("connecting: %s %s" % (self.address, self.port))
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # next two lines are to speed up the communication, by removing the default 50 ms delay
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.socket.settimeout(1)#timeout)
        self.socket.connect((self.address, self.port))
        self.socket.setblocking(0)

    def disconnect(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
    
    def parse_response(self, response):
        # Overload this
        return response
    
    def read_ready(self, timeout=0.1):
        r, _, _  = select.select([self.socket], [], [], timeout)
        return bool(len(r))
    
    def new_read(self):
        #print "reading", self.port
        # test if socket ready for reading
        response = ""
        while self.read_ready():
            try:
                response += self.socket.recv(16)
            except Exception as E:
                logging.error("Socket read attempt returned: %s" % str(E))
                time.sleep(0.1)
        logging.debug("IPSerial %s read: %s" % (self, response.strip()))
        return self.parse_response(response)
    
    def old_read(self):
        still_reading = 1
        response = ""
        while(still_reading):
            try:
                response += self.socket.recv(1)
            except socket.error, (value, message):
                if(value == errno.EWOULDBLOCK or value == errno.EAGAIN):
                    pass
                    #still_reading = 0
                else:
                    logging.error("Network error")
                    pass  # TODO deal with this
            if(response != None and len(response) > 0 and response[-1] == '\n'):
                still_reading = 0

        if(self.verbose):
            logging.debug("RECEIVED (%s; %s): %s" % (self.address, str(self), response))

        logging.debug("IPSerial %s read: %s" % (self, response.strip()))
        return response

    read = new_read
    
    def old_send(self, message, noresponse=0):

        # check the socket to see if there is junk in there already on the receive side
        # if so, this is here in error, and should be flushed
        (ready_to_read, ready_to_write, in_error) = select.select([self.socket], [], [self.socket], 0)
        if(len(ready_to_read) != 0):
            self.read()

        # send the outgoing message
        self.socket.send(message + "\n\r")
        logging.debug("IPSerial %s sent: %s" % (self, message.strip()))

        self.verbose = 0
        if(self.verbose):
            logging.debug("SENDING (%s; %s): %s\n\r" % (self.address, str(self), message))

        #time.sleep(0.2)  # allow some time to pass

        if(noresponse):
            return

        #read the response
        ready = 0
        retry_timeout = 0.1
        timeout = 5.0
        tic = time.time()
        while(not ready):
            (ready_to_read, ready_to_write, in_error) = select.select([self.socket], [], [self.socket], retry_timeout)
            if(len(ready_to_read) != 0):
                ready = 1
            if(time.time() - tic > timeout):
                return ""

        return self.read()
    
    def new_send(self, message, noresponse = 0):
        #print "writing", self.port, message
        while self.read_ready():
            ret = self.read()
            logging.error("Sending message %s before reading %s" % (message, ret))
        
        # check if write ready?
        self.socket.send(message + "\n\r")
        logging.debug("IPSerial %s sent: %s" % (self, message.strip()))
        
        if noresponse: return
        
        return self.read()
    
    send = new_send


if __name__ == "__main__":

    print "Instantiating"
    bridge = IPSerialBridge("192.168.0.10", 100)

    print "Connecting"
    bridge.connect()

    print "Sending"
    response = bridge.send("Test")

    print "Response :", response
