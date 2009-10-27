#
#  IPSerialBridge.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 11/12/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#

import errno
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
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.address, self.port))
        self.socket.setblocking(0)
        
    def disconnect(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
      
    
    def read(self):
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
                    print "Network error"
                    pass  # TODO deal with this
            if(response != None and len(response) > 0 and response[-1] == '\n'):
                still_reading = 0
        
        
        if(self.verbose):
            print("RECEIVED (%s; %s): %s" % (self.address, str(self), response))
        
        return response
        
    
    def send(self, message, noresponse = 0):
        
        # check the socket to see if there is junk in there already on the receive side
        # if so, this is here in error, and should be flushed
        (ready_to_read, ready_to_write, in_error) = select.select([self.socket],[],[self.socket], 0)
        if(len(ready_to_read) != 0):
            self.read()
        
        # send the outgoing message
        self.socket.send(message + "\n\r")
        
        self.verbose = 0
        if(self.verbose):
            print("SENDING (%s; %s): %s\n\r" % (self.address, str(self),message))
        
        #time.sleep(0.2)  # allow some time to pass
        
        if(noresponse):
            return
        
        #read the response
        ready = 0
        retry_timeout = 0.1
        timeout = 30.0
        tic = time.time()
        while(not ready):
            (ready_to_read, ready_to_write, in_error) = select.select([self.socket],[],[self.socket], retry_timeout)
            if(len(ready_to_read) != 0):
                ready = 1
            if(time.time() - tic > timeout):
                return ""
        
        return self.read()
        



if __name__ == "__main__":

    print "Instantiating"
    bridge = IPSerialBridge("192.168.0.10", 100)
    
    print "Connecting"
    bridge.connect()
    
    print "Sending"
    response = bridge.send("Test")
    
    print "Response :", response