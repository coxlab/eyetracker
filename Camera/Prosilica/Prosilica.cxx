/*
 *  ProsilicaCamera.cpp
 *  EyeTrackerStageDriver
 *
 *  Created by David Cox on 6/18/08.
 *  Copyright 2008 __MyCompanyName__. All rights reserved.
 *
 */

#include "Prosilica.h"
bool ProsilicaCamera::prosilica_initialized;

void frame_callback(tPvFrame *frame){
    //cerr << "Called back" << endl;
    ProsilicaCamera *cam = (ProsilicaCamera *)frame->Context[FRAME_CONTEXT_CAMERA];
    cam->frameCompleted(frame);
}

void _frameTo1DArray(tPvFrame frame, short *array, int dim){

    short *buffer = (short *)frame.ImageBuffer;
    memcpy(array, buffer, dim);
}

void initializeProsilica(){
	PvInitialize();	
}

std::vector<tPvCameraInfo> getCameraList() {
    tPvCameraInfo camera_list[32];
    unsigned long connected_num;
    
    int n = PvCameraList((tPvCameraInfo *)camera_list, 32, &connected_num);
    
    std::vector<tPvCameraInfo> camera_vector;
    for(int i =0; i < n; i++){
        camera_vector.push_back(camera_list[i]);
    }
    
    return camera_vector;
}

void test_it(short *array, int dim){
    for(int i = 0; i < dim-1; i++){
	array[i] = 1;
    }	
}

tPvFrame *test_it2(){ 
	tPvFrame *frame = new tPvFrame[1];
	frame->Width = 200;
	frame->Height = 100;
	frame->ImageBuffer = (void *)calloc(frame->Width * frame->Height, sizeof(unsigned short));
	
	for(int i = 0; i < 200; i++){
		for(int j = 0; j < 100; j++){
			((unsigned short *)frame->ImageBuffer)[i*100 + j] = i*100+j;
		}
	}
		
	return frame;
}
