/*
 *  EyeTrackerLEDDevice.h
 *  EyeTrackerStageDriver
 *
 *  Created by Davide Zoccolan on 5/16/08.
 *  Copyright 2008 __MyCompanyName__. All rights reserved.
 *
 */

#ifndef EYE_TRACKER_LEDDevice_H_
#define EYE_TRACKER_LEDDevice_H_


class EyeTrackerLEDDevice {
	
	public:
		
        EyeTrackerLEDDevice();
        virtual ~EyeTrackerLEDDevice(){ }
        
		virtual bool initialize() {};		
		virtual bool turnLightOn(int Ch, int Iset) {};
		virtual bool turnLightOff(int Ch) {};
        
        virtual bool getStatus(int Ch){ }
        virtual int getCurrent(int Ch){ }
	
};


#endif

