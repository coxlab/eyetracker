#
#  KVCCompliant.py
#  EyeTracker
#
#  Created by David Cox on 3/12/09.
#  Copyright (c) 2009 Harvard University. All rights reserved.
#

class KVCCompliant(object):

    # KVC compliance
    def getValue(self, key):
        if(self.__dict__.has_key(key)):
            return self.__dict__[key]
        else:
            return None
            
    def setValue(self, key, value):
        print "setting ", key, " to ", value
        self.__dict__[key] = value
        
    def getKeys(self):
        return self.__dict__.keys()