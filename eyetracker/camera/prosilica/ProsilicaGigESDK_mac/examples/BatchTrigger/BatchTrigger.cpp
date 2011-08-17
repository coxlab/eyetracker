/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code, open the specified camera and use software trigger to
| "stream" from it using a single frame for a specified amount of time.
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
#include <string.h>
#include <stdlib.h>

#ifdef _WINDOWS
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <Winsock2.h>
#endif

#if defined(_LINUX) || defined(_QNX) || defined(_OSX)
#include <unistd.h>
#include <time.h>
#include <arpa/inet.h>
#define _STDCALL
#else
#define _STDCALL __stdcall
#endif

#include <PvApi.h>

// camera's data
typedef struct 
{
    unsigned long   UID;
    tPvHandle       Handle;
    tPvFrame        Frame;
    tPvUint32       Counter;
    char            Filename[20];

} tCamera;

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

// callback called when a frame is done
void _STDCALL FrameDoneCB(tPvFrame* pFrame)
{
    // if the camera hasn't been unplugged or cancelled, we will re-enqueue it
    // and use software trigger
    if(pFrame->Status != ePvErrUnplugged && pFrame->Status != ePvErrCancelled)
    {
        tCamera *Camera = (tCamera*)pFrame->Context[0];
        
	    #ifdef _x64
        printf("frame %04u captured\r",((unsigned long long*)pFrame->Context)[1]);
	    #else
        printf("frame %04u captured\r",((int*)pFrame->Context)[1]);
	    #endif
        fflush(stdout);
        
        // reenqueue
        if(!PvCaptureQueueFrame(Camera->Handle,pFrame,FrameDoneCB))
        {
            #ifdef _x64
            ((unsigned long long*)pFrame->Context)[1]++;
            #else
            ((int*)pFrame->Context)[1]++;
            #endif
            // trigger
            PvCommandRun(Camera->Handle,"FrameStartTriggerSoftware"); 
        }  
    }
}

// open the camera
bool CameraOpen(unsigned long IP,tCamera* Camera)
{
    tPvCameraInfo list;
    tPvIpSettings sets;
    
    if(!PvCameraInfoByAddr(IP,&list,&sets))
    {
        printf("camera %s detected \n",list.SerialString);
        
        Camera->UID = list.UniqueId;
                  
        return !PvCameraOpen(Camera->UID,ePvAccessMaster,&(Camera->Handle)); 
    }
    else
        return false;
}

// setup and start streaming
bool CameraStart(tCamera* Camera)
{
    unsigned long FrameSize = 0;

    // Auto adjust the packet size to max supported by the network, up to a max of 8228.
    // NOTE: In Vista, if the packet size on the network card is set lower than 8228,
    //       this call may break the network card's driver. See release notes.
    //
    //PvCaptureAdjustPacketSize(Camera->Handle,8228);

    // how big should the frame buffers be?
    if(!PvAttrUint32Get(Camera->Handle,"TotalBytesPerFrame",&FrameSize))
    {
        bool failed = false;

        // allocate the buffer for the single frame we need
        Camera->Frame.Context[0] = Camera;
        #ifdef _x64
        ((unsigned long long*)Camera->Frame.Context)[1] = 1;
        #else
        ((int*)Camera->Frame.Context)[1] = 1;
        #endif
        Camera->Frame.ImageBuffer = new char[FrameSize];
        if(Camera->Frame.ImageBuffer)
            Camera->Frame.ImageBufferSize = FrameSize;
        else
            failed = true;

        if(!failed)
        {
            // set the camera is capture mode
            if(!PvCaptureStart(Camera->Handle))
            {
                // and set the acquisition mode into continuous and software trigger mode
                if(PvAttrEnumSet(Camera->Handle,"FrameStartTriggerMode","Software") ||
                   PvCommandRun(Camera->Handle,"AcquisitionStart"))
                {
                    // if that fail, we reset the camera to non capture mode
                    PvCaptureEnd(Camera->Handle) ;
                    return false;
                }
                else
                    return true;
            }
            else
                return false;
        }
        else
            return false;
    }
    else
        return false;
}

// stop streaming
void CameraStop(tCamera* Camera)
{
    PvCommandRun(Camera->Handle,"AcquisitionStop");
    PvCaptureQueueClear(Camera->Handle);
    PvCaptureEnd(Camera->Handle);  
    
    #ifdef _x64
    printf("a total of %llu frames were captured\n",((unsigned long long*)Camera->Frame.Context)[1]);
    #else
    printf("a total of %u frames were captured\n",((int*)Camera->Frame.Context)[1]);
    #endif
}

// start the batch 'process'
bool CameraBatch(tCamera* Camera)
{
    if(!PvCaptureQueueFrame(Camera->Handle,&(Camera->Frame),FrameDoneCB))
        return !PvCommandRun(Camera->Handle,"FrameStartTriggerSoftware");
    else
    {
        printf("failed to enqueue the frame\n");
        return false;
    }
}

// close the camera
void CameraClose(tCamera* Camera)
{
    PvCameraClose(Camera->Handle);
    // and free the image buffer of the frame
    delete [] (char*)Camera->Frame.ImageBuffer;
}

int main(int argc, char* argv[])
{
    // initialise the Prosilica API
    if(!PvInitialize())
    { 
        tCamera Camera;

        memset(&Camera,0,sizeof(tCamera));

        if(argc>2)
        {
            unsigned long IP = inet_addr(argv[1]);
            unsigned long Time = atol(argv[2]);
             
            if(Time)
            {    
                // if we got a valid IP@ we'll open the camera
                if(IP && CameraOpen(IP,&Camera))
                {
                    // start streaming from the camera
                    if(CameraStart(&Camera))
                    {
                        // start the batch & snooze
                        if(CameraBatch(&Camera))
                            Sleep(Time * 1000);   
                        else
                            printf("failed to start the batch ...\n");
                        // stop the streaming
                        CameraStop(&Camera);
                    }
                    else
                        printf("failed to start streaming\n");
    
                    // close the camera
                    CameraClose(&Camera);             
                }
                else
                    printf("sorry, I couldn't find that camera %s\n",argv[1]);
            }
            else
                printf("usage: BatchTrigger <camera IP> <duration (in seconds)\n");    
        }   
        else
            printf("usage: BatchTrigger <camera IP> <duration (in seconds)\n");   
        
        // uninitialise the API
        PvUnInitialize();
    }
    else
        printf("failed to initialise the API\n");
    
	return 0;
}
