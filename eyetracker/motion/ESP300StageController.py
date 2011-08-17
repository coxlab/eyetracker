#
#  ESP300StageController.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 11/12/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#

from eyetracker.util import IPSerialBridge
import numpy

class ESP300StageController(IPSerialBridge):

    x_axis = 1
    y_axis = 2
    r_axis = 3

    def __init__(self, address, port):
        IPSerialBridge.__init__(self, address, port)
    
    
    def setup(self):
        return
        
    
    def home(self, axis):
        self.send("%dOR" % axis,1)
    
    def move_absolute(self, axis, pos):
        self.send("%dPA%.4f" % (axis, float(pos)),1)
        self.send("%dWS" % axis, 1)
        self.send("%dTP" % axis)
    
    def move_relative(self, axis, pos):
        self.send("%dPR%.4f" % (axis, float(pos)),1)
        self.send("%dWS" % axis, 1)
        self.send("%dTP" % axis)

    def move_composite_absolute(self, axes, new_positions):
        # should produce a simultaneous movement on multiple axes, for now just 
        # do serially
        #for a in range(0, len(axes)):
        #    self.move_absolute(axes[a], float(new_positions[a]))
        
        if(len(axes) == 2):
                  
            self.send("%dPA%.4f" % (axes[0], new_positions[0]), 1 ) 
            self.send("%dPA%.4f" % (axes[1], new_positions[1]), 1 ) 
            self.send("%dWS" % axes[0], 1)
            self.send("%dWS" % axes[1], 1)
            self.send("%dTP" % axes[0] )
            self.send("%dTP" % axes[1] )
            
            # assign the axes to a group
            #self.send("1HN%d,%d" % axes, 1)
            
            # turn the group on
            #self.send("1HO", 1)
            
            # set the group velocity, acceleration, and decelleration to something reasonable
            #self.send("1HV4.0", 1)
            #self.send("1HA15.0", 1)
            #self.send("1HD15.0", 1)
            
            # make the move
            #self.send("1HL%.4f,%.4f" % new_positions, 1)
        
        if(len(axes) == 3):
            self.send("%dPA%.4f" % (axes[0], new_positions[0]), 1 ) 
            self.send("%dPA%.4f" % (axes[1], new_positions[1]), 1 )
            self.send("%dPA%.4f" % (axes[2], new_positions[2]), 1 ) 
            self.send("%dWS" % axes[0], 1)
            self.send("%dWS" % axes[1], 1)
            self.send("%dWS" % axes[2], 1)
            self.send("%dTP" % axes[0] )
            self.send("%dTP" % axes[1] )
            self.send("%dTP" % axes[2] )

        # wait for complition of group movement
        #self.send("1HW200", 1)
        
        # delete the group
        #self.send("1HX", 1)
    
    def move_composite_relative(self, axes, new_positions):
        # should produce a simultaneous movement on multiple axes, for now just 
        # do serially
        #for a in range(0, len(axes)):
        #    self.move_relative(axes[a], float(new_positions[a]))
        
        target_positions = []
        for i in range(0, len(axes)):
            self.wait_for_completion(axes[i])
            target_positions.append(float(self.current_position(axes[i])) + float(new_positions[i]));
        
        self.move_composite_absolute(axes, tuple(target_positions))

        
    def current_position(self, axis):
        okayp = 0
        retries = 20
        while (not okayp and retries > 0):
            result_string = self.send("%dTP" % axis)
            #print "result_string in current_position in while loop:", result_string       
            
            if(len(result_string) == 0):
                time.sleep(0.01)
                retries -= 1
            else:
                okayp = 1
        
        if not okayp:
            return numpy.inf
        
        #print "Length of result_string = ", len(result_string)
        if len(result_string) > 1:
            #print "first element of result_string in current_position:", result_string          
            return float(result_string)
        else:
            print "result_string in current_position:", result_string            
            return float(result_string)

    def wait_for_completion(self, axis):
        t_wait = 150 #150 #100
        self.send("%dWS%.4f" % (axis, t_wait), 1)

    def power_down(self, axis):
        self.send("%dMF", axis)




