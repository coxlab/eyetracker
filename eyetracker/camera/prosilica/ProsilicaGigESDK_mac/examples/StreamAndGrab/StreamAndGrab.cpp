/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code, open the first camera found on the host computer alternate
| streaming and grabbing of a single frame
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
#include <signal.h>
#endif

#include <PvApi.h>

#ifdef _WINDOWS
#define _STDCALL __stdcall
#else
#define _STDCALL
#define TRUE     0
#endif

#define FRAMESCOUNT 15

typedef struct 
{
    unsigned long   UID;
    tPvHandle       Handle;
    tPvFrame        Frames[FRAMESCOUNT];
    tPvFrame        Frame;
    bool            Abort;

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

void SetConsoleCtrlHandler(void (*func)(int), int junk)
{
    signal(SIGINT, func);
}
#endif

// callback called when the camera is plugged/unplugged
void _STDCALL CameraEventCB(void* Context,
                             tPvInterface Interface,
                             tPvLinkEvent Event,
                             unsigned long UniqueId)
{
    switch(Event)
    {
        case ePvLinkAdd:
        {
            printf("camera %lu plugged\n",UniqueId);
            break;
        }
        case ePvLinkRemove:
        {
            printf("camera %lu unplugged\n",UniqueId);
            break;
        }
        default:
            break;
    }
}

// wait for a camera to be plugged
void WaitForCamera()
{
    printf("waiting for a camera ...\n");
    while(!PvCameraCount()) 
        Sleep(250);
    printf("\n");
}

// callback called when a frame is done
void _STDCALL FrameDoneCB(tPvFrame* pFrame)
{
    printf("frame returned with status = %u\n",pFrame->Status);
  
    // if the frame was completed we re-enqueue it
    if(pFrame->Status != ePvErrUnplugged && pFrame->Status != ePvErrCancelled)
    {
        //printf(".");fflush(stdout);
        PvCaptureQueueFrame(GCamera.Handle,pFrame,FrameDoneCB);
    }      
}

// get the first camera found
bool CameraGrab()
{
    tPvUint32 count,connected;
    tPvCameraInfo list;

    count = PvCameraList(&list,1,&connected);
    if(count == 1)
    {
        GCamera.UID = list.UniqueId;
        printf("grabbing camera %s\n",list.SerialString);
        return true;
    
    }
    else
        return false;
}

// open the camera
bool CameraSetup()
{
    // open the camera and allocate the buffers we need for streaming
    if(!PvCameraOpen(GCamera.UID,ePvAccessMaster,&(GCamera.Handle)))
    {
        unsigned long FrameSize = 0;

        // Auto adjust the packet size to max supported by the network, up to a max of 8228.
        // NOTE: In Vista, if the packet size on the network card is set lower than 8228,
        //       this call may break the network card's driver. See release notes.
        //
        //PvCaptureAdjustPacketSize(GCamera.Handle,8228);
    
        // how big should the frame buffers be?
        if(!PvAttrUint32Get(GCamera.Handle,"TotalBytesPerFrame",&FrameSize))
        {
            bool failed = false;
    
            // allocate the buffer for each frames
            for(int i=0;i<FRAMESCOUNT && !failed;i++)
            {
                GCamera.Frames[i].ImageBuffer = new char[FrameSize];
                if(GCamera.Frames[i].ImageBuffer)
                    GCamera.Frames[i].ImageBufferSize = FrameSize;
                else
                    failed = true;
            }

            if(!failed)
            {
                GCamera.Frame.ImageBuffer = new char[FrameSize];
                if(GCamera.Frame.ImageBuffer)
                    GCamera.Frame.ImageBufferSize = FrameSize;
                else
                    failed = true;
            }

            if(failed)
            {
                PvCameraClose(GCamera.Handle);
                GCamera.Handle = NULL;
                return false;
            }
            else
                return true;
        }
        else
        {
            PvCameraClose(GCamera.Handle);
            GCamera.Handle = NULL;
            return false;
        }
    }
    else
        return false;
}

bool CameraSnap()
{
    // set the camera is acquisition mode
    if(!PvCaptureStart(GCamera.Handle))
    {
        // set the acquisition mode to continuous
        if(PvCommandRun(GCamera.Handle,"AcquisitionStart"))
        {
            // if that fail, we reset the camera to non capture mode
            PvCaptureEnd(GCamera.Handle) ;
            return false;
        }
        else
        {
            bool failed = false;
        
            // enqueue the single frame
            if(!PvCaptureQueueFrame(GCamera.Handle,&(GCamera.Frame),NULL))
            {
                printf("waiting for the frame ...\n");
                failed = PvCaptureWaitForFrameDone(GCamera.Handle,&(GCamera.Frame),PVINFINITE) != 0;
                printf("frame's done ...\n");
            }
            else        
                failed = true;
                   
            PvCommandRun(GCamera.Handle,"AcquisitionStop");
            PvCaptureEnd(GCamera.Handle);
            
            return !failed;
        }
    }
    else
        return false;

}

// setup and start streaming
bool CameraStart()
{
    tPvErr Err;

    // set the camera is acquisition mode
    if(!(Err = PvCaptureStart(GCamera.Handle)))
    {
        // set the acquisition mode to continuous
        if(PvCommandRun(GCamera.Handle,"AcquisitionStart"))
        {
            // if that fail, we reset the camera to non capture mode
            PvCaptureEnd(GCamera.Handle) ;
            printf("PvCommandRun() failed\n");
            return false;
        }
        else
        {
            for(int i=0;i<FRAMESCOUNT;i++)
                PvCaptureQueueFrame(GCamera.Handle,&(GCamera.Frames[i]),FrameDoneCB);
                
            return true;
        }
    }
    else
    {
        printf("PvCaptureStart() failed with error code %u\n",Err);
        return false;
    }
}

// stop streaming
void CameraStop()
{
    PvCommandRun(GCamera.Handle,"AcquisitionStop");
    PvCaptureEnd(GCamera.Handle);
    // dequeue all the frame still queued (this will block until they all have been dequeued)
    PvCaptureQueueClear(GCamera.Handle);
}

// unsetup the camera
void CameraUnsetup()
{
    printf("closing the camera now ...\n");
    // then close the camera
    PvCameraClose(GCamera.Handle);
    printf("closed\n");

    // delete all the allocated buffers
    for(int i=0;i<FRAMESCOUNT;i++)
        delete [] (char*)GCamera.Frames[i].ImageBuffer;

    delete [] (char*)GCamera.Frame.ImageBuffer;

    GCamera.Handle = NULL;
}

// CTRL-C handler
#ifdef _WINDOWS
BOOL WINAPI CtrlCHandler(DWORD dwCtrlType)
#else
void CtrlCHandler(int Signo)
#endif  
{  
    printf("interrupting!\n");    
    
    GCamera.Abort = true;    
    
    if(GCamera.Handle) 
        CameraStop(); 
    
    #ifndef _WINDOWS
    signal(SIGINT, CtrlCHandler);
    #else
    return true;
    #endif
}

void DoStream()
{
    if(CameraStart())
    {
        printf("streaming started ...\n");
        Sleep(800);
        CameraStop();
        printf("streaming stopped ...\n");
    }
    else
        printf("streaming failed ...\n");    
}

void DoSnap()
{
    if(CameraSnap())
        printf("snapping done\n");
    else
        printf("snapping failed\n");
}

int main(int argc, char* argv[])
{
    // initialise the Prosilica API
    if(!PvInitialize())
    { 
        memset(&GCamera,0,sizeof(tCamera));

        SetConsoleCtrlHandler(CtrlCHandler, TRUE);
	
        PvLinkCallbackRegister(CameraEventCB,ePvLinkAdd,NULL);
        PvLinkCallbackRegister(CameraEventCB,ePvLinkRemove,NULL);        
        
        // wait for a camera to be plugged
        WaitForCamera();

        // grab a camera from the list
        if(CameraGrab())
        {
            // setup the camera
            if(CameraSetup())
            { 
              if(!GCamera.Abort)
                DoSnap();
              if(!GCamera.Abort)
                DoSnap();
              if(!GCamera.Abort)
                DoStream();
              if(!GCamera.Abort)
                DoStream();
              if(!GCamera.Abort)
                DoSnap();
              if(!GCamera.Abort)
                DoStream();
              if(!GCamera.Abort)
                DoStream();
                
                // unsetup the camera
                CameraUnsetup();
            }
            else
                printf("failed to setup the camera\n");
        }
        else
            printf("failed to find a camera\n");

        PvLinkCallbackUnRegister(CameraEventCB,ePvLinkAdd);
        PvLinkCallbackUnRegister(CameraEventCB,ePvLinkRemove);
        
        // uninitialise the API
        PvUnInitialize();
    }
    else
        printf("failed to initialise the API\n");
            
    return 0;
}
