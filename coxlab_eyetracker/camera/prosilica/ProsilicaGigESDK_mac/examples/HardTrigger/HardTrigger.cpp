/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code, open the first camera found on the host computer and set it
| for capturing. It then wait for an hardware trigger and saving the frame to a
| TIFF file if the capture was successful
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

#ifdef _WINDOWS
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#endif

#if defined(_LINUX) || defined(_QNX) || defined(_OSX)
#include <unistd.h>
#include <pthread.h>
#include <signal.h>
#include <sys/times.h>
#include <arpa/inet.h>
#endif

#include <PvApi.h>
#include <ImageLib.h>

#ifdef _WINDOWS
#define _STDCALL __stdcall
#else
#define _STDCALL
#define TRUE     0
#endif


// camera's data
typedef struct 
{
    unsigned long   UID;
    tPvHandle       Handle;
    tPvFrame        Frame;
    tPvUint32       Counter;
    char            Filename[20];
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

// wait for a camera to be plugged
void WaitForCamera()
{
    printf("waiting for a camera ");
    while(!PvCameraCount())
    {
        printf(".");
        Sleep(250);
    }
    printf("\n");
}


// CTRL-C handler
#ifdef _WINDOWS
BOOL WINAPI CtrlCHandler(DWORD dwCtrlType)
#else
void CtrlCHandler(int Signo)
#endif	
{  
    GCamera.Abort = true; 
    
    if(GCamera.Handle)
        PvCaptureQueueClear(GCamera.Handle);
        
    #ifndef _WINDOWS
    signal(SIGINT, CtrlCHandler);
    #else
    return true;
    #endif
}

// get the first camera found
bool CameraGet()
{
    tPvUint32 count,connected;
    tPvCameraInfo list;

    count = PvCameraList(&list,1,&connected);
    if(count == 1)
    {
        GCamera.UID = list.UniqueId;
        printf("got camera %s\n",list.SerialString);
        return true;
    
    }
    else
        return false;
}

// open the camera
bool CameraSetup()
{
    return !PvCameraOpen(GCamera.UID,ePvAccessMaster,&(GCamera.Handle));   
}

// setup and start streaming
bool CameraStart()
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

        // allocate the buffer for the single frame we need
        GCamera.Frame.ImageBuffer = new char[FrameSize];
        if(GCamera.Frame.ImageBuffer)
            GCamera.Frame.ImageBufferSize = FrameSize;
        else
            failed = true;

        if(!failed)
        {
            // set the camera is capture mode
            if(!PvCaptureStart(GCamera.Handle))
            {
                // and set the acquisition mode into continuous and hardware trigger mode
                if(PvAttrEnumSet(GCamera.Handle,"FrameStartTriggerMode","SyncIn1") ||
                   PvCommandRun(GCamera.Handle,"AcquisitionStart"))
                {
                    // if that fail, we reset the camera to non capture mode
                    PvCaptureEnd(GCamera.Handle) ;
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
void CameraStop()
{
    PvCommandRun(GCamera.Handle,"AcquisitionStop");
    PvCaptureEnd(GCamera.Handle);  
}

// snap and save a frame from the camera
void CameraSnap()
{
    if(!PvCaptureQueueFrame(GCamera.Handle,&(GCamera.Frame),NULL))
    {
        printf("waiting for a frame ...\n");

        while(PvCaptureWaitForFrameDone(GCamera.Handle,&(GCamera.Frame),1500) == ePvErrTimeout)
            printf("still waiting ...\n");

        if(GCamera.Frame.Status == ePvErrSuccess)
        {
            sprintf(GCamera.Filename,"./snap%04lu.tiff",++GCamera.Counter);

            if(!ImageWriteTiff(GCamera.Filename,&(GCamera.Frame)))
                printf("Failed to save the grabbed frame!");
            else
                printf("frame saved\n");
        }
        else
        if(GCamera.Frame.Status != ePvErrCancelled)
            printf("the frame failed to be captured ... %u\n",GCamera.Frame.Status);
    }
    else
        printf("failed to enqueue the frame\n");
}

// unsetup the camera
void CameraUnsetup()
{
    PvCameraClose(GCamera.Handle);
    // and free the image buffer of the frame
    delete [] (char*)GCamera.Frame.ImageBuffer;
}

int main(int argc, char* argv[])
{
    // initialise the Prosilica API
    if(!PvInitialize())
    { 
        memset(&GCamera,0,sizeof(tCamera));

        SetConsoleCtrlHandler(&CtrlCHandler, TRUE);

        // wait for a camera to be plugged
        WaitForCamera();

        // get a camera from the list
        if(CameraGet())
        {
            // setup the camera
            if(CameraSetup())
            {
                // strat streaming from the camera
                if(CameraStart())
                {
                    printf("The camera is ready now. \n");
                    // snap now
                    while(!GCamera.Abort)
                        CameraSnap();
                    // stop the streaming
                    CameraStop();
                }
                else
                    printf("failed to start streaming\n");

                // unsetup the camera
                CameraUnsetup();
            }
            else
                printf("failed to setup the camera\n");
        }
        else
            printf("failed to find a camera\n");
       
        // uninitialise the API
        PvUnInitialize();
    }
    else
        printf("failed to initialise the API\n");
    
	return 0;
}
