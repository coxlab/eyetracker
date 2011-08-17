/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code, open the first camera found on the host computer and streams
| frames from it until the user terminate it
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
#include <Winsock2.h>
#endif

#if defined(_LINUX) || defined(_QNX) || defined(_OSX)
#include <unistd.h>
#include <pthread.h>
#include <signal.h>
#include <sys/times.h>
#include <arpa/inet.h>
#endif

#include <PvApi.h>

#ifdef _WINDOWS
#define _STDCALL __stdcall
#else
#define _STDCALL
#define TRUE     0
#endif

#define FRAMESCOUNT 10

typedef struct 
{
    unsigned long   UID;
    tPvHandle       Handle;
    tPvFrame        Frames[FRAMESCOUNT];
#ifdef _WINDOWS
    HANDLE          ThHandle;
    DWORD           ThId;
#else
    pthread_t       ThHandle;
#endif    
    bool            Abort;
    
} tCamera;


// global camera data
tCamera         GCamera;

#if defined(_LINUX) || defined(_QNX) || defined(_OSX)
struct tms      gTMS;
unsigned long   gT00 = times(&gTMS);

void Sleep(unsigned int time)
{
    struct timespec t,r;
    
    t.tv_sec    = time / 1000;
    t.tv_nsec   = (time % 1000) * 1000000;    
    
    while(nanosleep(&t,&r)==-1)
        t = r;
}

unsigned long GetTickCount()
{
    unsigned long lNow = times(&gTMS);

    if(lNow < gT00)
        gT00 = lNow;
    
    return (unsigned long)((float)(lNow - gT00) * 10000000.0 / (float)CLOCKS_PER_SEC);
}

void SetConsoleCtrlHandler(void (*func)(int), int junk)
{
    signal(SIGINT, func);
}
#endif

#ifdef _WINDOWS
unsigned long __stdcall ThreadFunc(void *pContext)
#else
void *ThreadFunc(void *pContext)
#endif
{
    unsigned long Completed,Dropped,Done;
    unsigned long Before,Now,Total,Elapsed;
    unsigned long Missed,Errs;
    double Fps;
    float Rate;
    tPvErr Err;

    Fps = 0;
    Elapsed = 0;
    Total = 0;
    Done = 0;
    Before = GetTickCount();

    while(!GCamera.Abort &&
          !(Err = PvAttrUint32Get(GCamera.Handle,"StatFramesCompleted",&Completed)) &&
          !(Err = PvAttrUint32Get(GCamera.Handle,"StatFramesDropped",&Dropped)) &&
          !(Err = PvAttrUint32Get(GCamera.Handle,"StatPacketsMissed",&Missed)) &&
          !(Err = PvAttrUint32Get(GCamera.Handle,"StatPacketsErroneous",&Errs)) &&
          !(Err = PvAttrFloat32Get(GCamera.Handle,"StatFrameRate",&Rate)))
    {
        Now = GetTickCount();
        Total += Completed - Done;
        Elapsed += Now-Before;

        if(Elapsed >= 500)
        {
            Fps = (double)Total * 1000.0 / (double)Elapsed;
            Elapsed = 0;
            Total = 0;
        }

        printf("completed : %9lu dropped : %9lu missed : %9lu err. : %9lu rate : %5.2f (%5.2f)\r",
		Completed,Dropped,Missed,Errs,Rate,Fps);
        Before = GetTickCount();
        Done = Completed;

        Sleep(20);
    }
    
    printf("\n");

    return 0;
}

// spawn a thread
void SpawnThread()
{
#ifdef _WINDOWS	
    GCamera.ThHandle = CreateThread(NULL,NULL,ThreadFunc,&GCamera,NULL,&(GCamera.ThId));
#else
    pthread_create(&GCamera.ThHandle,NULL,ThreadFunc,(void *)&GCamera);
#endif    
}

// wait for the thread to be over
void WaitThread()
{
    #ifdef _WINDOWS		
    WaitForSingleObject(GCamera.ThHandle,INFINITE);
    #else
    pthread_join(GCamera.ThHandle,NULL);
    #endif
}

// wait for a camera to be plugged
void WaitForCamera()
{
    printf("waiting for a camera ...\n");
    while(!PvCameraCount() && !GCamera.Abort)
        Sleep(250);
    printf("\n");
}

// wait forever (at least until CTRL-C)
void WaitForEver()
{
  while(!GCamera.Abort)
        Sleep(500);
}

// callback called when a frame is done
void _STDCALL FrameDoneCB(tPvFrame* pFrame)
{
    // if the frame was completed (or if data were missing/lost) we re-enqueue it
    if(pFrame->Status == ePvErrSuccess  || 
       pFrame->Status == ePvErrDataLost ||
       pFrame->Status == ePvErrDataMissing)
        PvCaptureQueueFrame(GCamera.Handle,pFrame,FrameDoneCB);  
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
    return !PvCameraOpen(GCamera.UID,ePvAccessMaster,&(GCamera.Handle));   
}

// open the camera
bool CameraSetup(unsigned long IP)
{
    return !PvCameraOpenByAddr(IP,ePvAccessMaster,&(GCamera.Handle));
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
            // set the camera is acquisition mode
            if(!PvCaptureStart(GCamera.Handle))
            {
                // start the acquisition and make sure the trigger mode is "freerun"
                if(PvCommandRun(GCamera.Handle,"AcquisitionStart") ||
	               PvAttrEnumSet(GCamera.Handle,"FrameStartTriggerMode","Freerun"))
                {
                    // if that fail, we reset the camera to non capture mode
                    PvCaptureEnd(GCamera.Handle) ;
                    return false;
                }
                else                
                {
                    // then enqueue all the frames
                
                    for(int i=0;i<FRAMESCOUNT;i++)
                        PvCaptureQueueFrame(GCamera.Handle,&(GCamera.Frames[i]),FrameDoneCB);

                    printf("frames queued ...\n");

                    return true;
                }
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
    printf("stopping streaming\n");
    PvCommandRun(GCamera.Handle,"AcquisitionStop");
    PvCaptureEnd(GCamera.Handle);  
}

// unsetup the camera
void CameraUnsetup()
{
    // dequeue all the frame still queued (this will block until they all have been dequeued)
    PvCaptureQueueClear(GCamera.Handle);
    // then close the camera
    PvCameraClose(GCamera.Handle);

    // delete all the allocated buffers
    for(int i=0;i<FRAMESCOUNT;i++)
        delete [] (char*)GCamera.Frames[i].ImageBuffer;
}

// CTRL-C handler
#ifdef _WINDOWS
BOOL WINAPI CtrlCHandler(DWORD dwCtrlType)
#else
void CtrlCHandler(int Signo)
#endif	
{  
    GCamera.Abort = true;    
        
    #ifndef _WINDOWS
    signal(SIGINT, CtrlCHandler);
    #else
    return true;
    #endif
}

int main(int argc, char* argv[])
{
    // initialise the Prosilica API
    if(!PvInitialize())
    { 
        memset(&GCamera,0,sizeof(tCamera));

        SetConsoleCtrlHandler(&CtrlCHandler, TRUE);
        
         // the only command line argument accepted is the IP@ of the camera to be open
        if(argc>1)
        {
            unsigned long IP = inet_addr(argv[1]);
             
            if(IP != INADDR_NONE)
            {
                // setup the camera
                if(CameraSetup(IP))
                {
                    // strat streaming from the camera
                    if(CameraStart())
                    {
                        printf("camera is streaming now. Press CTRL-C to terminate\n");
    
                        // spawn a thread
                        SpawnThread();
    
                        // we wait until the user press CTRL-C
                        WaitForEver();
                           
                        // then wait for the thread to finish
                        if(GCamera.ThHandle)
                            WaitThread(); 
                                            
                        // stop the camera
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
               
        }
        else
        {
            // wait for a camera to be plugged
            WaitForCamera();
    
            // grab a camera from the list
            if(!GCamera.Abort && CameraGrab())
            {
                // setup the camera
                if(CameraSetup())
                {
                    // strat streaming from the camera
                    if(CameraStart())
                    {
                        printf("camera is streaming now. Press CTRL-C to terminate\n");
    
                        // spawn a thread
                        SpawnThread();
    
                        // we wait until there is no more camera
                        WaitForEver();
    
                        // then wait for the thread to finish
                        if(GCamera.ThHandle)
                            WaitThread();     
                                       
                        // stop the camera
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
        }
       
        // uninitialise the API
        PvUnInitialize();
    }
    else
        printf("failed to initialise the API\n");
    

	return 0;
}
