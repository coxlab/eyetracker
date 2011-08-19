/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code, open the first camera found on the host computer and change
| its Region of Interest (ROI).
|
|==============================================================================
|
| THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS" AND ANY EXPRESS OR IMPLIED
| WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE,
| NON-INFRINGEMENT, MERCHANTABILITY AND FITNESS FOR A PARTICULAR  PURPOSE ARE
| DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
| INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
| LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
| OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED  AND ON ANY THEORY OF
| LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
| NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
| EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
|
|==============================================================================
*/

#ifdef _WINDOWS
#include "StdAfx.h"
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WINDOWS
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#endif

#if defined(_LINUX) || defined(_QNX) || defined(_OSX)
#include <unistd.h>
#include <time.h>
#endif

#include <PvApi.h>

#ifndef _WINDOWS
#define TRUE 0
#endif

// camera data
typedef struct 
{
    tPvHandle       Handle;
    tPvCameraInfo   Info;

} tCamera;

// global camera data
tCamera GCamera;

#if defined(_LINUX) || defined(_QNX) || defined(_OSX)
void Sleep(unsigned int time)
{
    struct timespec t,r;
    
    t.tv_sec    = time / 1000;
    t.tv_nsec   = (time % 1000) * 1000000;    
    
    while(nanosleep(&t,&r)==-1)
        t = r;
}
#endif

// wait for a camera to be plugged
void WaitForCamera()
{
    printf("waiting for a camera");
    while(!PvCameraCount())
    {
        printf(".");fflush(stdout);
        Sleep(250);
    }
    printf("\n");
}

// get the first camera found
bool CameraGrab()
{
    return PvCameraList(&(GCamera.Info),1,NULL) >= 1;
}

// open the camera
bool CameraOpen()
{
    if(!PvCameraOpen(GCamera.Info.UniqueId,ePvAccessMaster,&(GCamera.Handle)))
    {
        printf("Camera open : %s\n",GCamera.Info.SerialString);
        return true;
    }
    else
        return false;
}

// close the camera
void CameraClose()
{
    if(GCamera.Handle)
        PvCameraClose(GCamera.Handle); 
}

// change some camera settings
void CameraChange()
{
    tPvErr Err;
    unsigned long sWidth,sHeight;
    unsigned long rWidth,rHeight;
    unsigned long CenterX,CenterY;

    // read the sensor size
    if(!(Err = PvAttrUint32Get(GCamera.Handle,"SensorWidth",&sWidth)) &&
       !(Err = PvAttrUint32Get(GCamera.Handle,"SensorHeight",&sHeight)))
    {
        rWidth  = sWidth / 2;
        rHeight = sHeight / 2;

        CenterX = rWidth - 1;
        CenterY = rHeight - 1;

        printf("Camera's sensor is %lux%lu, changing it to %lux%lu\n",sWidth,sHeight,rWidth,rHeight);
    
        // set the width&height
        if(!(Err = PvAttrUint32Set(GCamera.Handle,"Width",rWidth)) &&
           !(Err = PvAttrUint32Set(GCamera.Handle,"Height",rHeight)))
           {
               if(!(Err = PvAttrUint32Set(GCamera.Handle,"RegionX",CenterX - rWidth / 2)))
                Err = PvAttrUint32Set(GCamera.Handle,"RegionY",CenterY - rHeight / 2);
           }
    }

    if(!Err)
        printf("ROI changed\n");
    else
        printf("ROI failed to be changed\n");    
}

int main(int argc, char* argv[])
{
    // initialise the Prosilica API
    if(!PvInitialize())
    { 
        memset(&GCamera,0,sizeof(tCamera));
	
        // wait for a camera to be plugged
        WaitForCamera();

        if(CameraGrab())
        {
            // open the camera
            if(CameraOpen())
            {
                // change some attributes
                CameraChange();
                        
                // unsetup the camera
                CameraClose();
            }
            else
                printf("failed to open the camera\n");
        }
        else
            printf("failed to grab a camera!\n");

        // uninitialise the API
        PvUnInitialize();
    }
    else
        printf("failed to initialise the API\n");
    
	return 0;
}
