/*
| ==============================================================================
| Copyright (C) 2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code opens and streams from the camera which IP address was given
| in the command line arguments. Each camera is open and streamed from a separate
| thread, so that if 3 cameras are given, there will be 3 threads.
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

// camera's data
typedef struct 
{
    int             ID;
    unsigned long   IP;
    tPvHandle       Handle;
    tPvFrame        Frame;
#ifdef _WINDOWS
    HANDLE          ThHandle;
    DWORD           ThId;
#else
    pthread_t       ThHandle;
#endif    
    
} tCamera;

// session data
typedef struct
{
    int      Count;
    tCamera* Cameras;
    bool     Stop;

} tSession;

///////////////

// global data
tSession GSession;

///////////////

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

// get and print the number of completed frames
void CameraStats(tCamera& Camera)
{
    unsigned long Completed;

    if(!PvAttrUint32Get(Camera.Handle,"StatFramesCompleted",&Completed))
        printf("[%u] : %9lu",Camera.ID,Completed); 
}

// stream from a camera using a single frame
void CameraStream(tCamera& Camera)
{
    tPvErr Err = ePvErrSuccess;
    
    while(!Err && !GSession.Stop)
    {
        Err = PvCaptureQueueFrame(Camera.Handle,&Camera.Frame,NULL);
        if(!Err)
        {                        
            Err = PvCaptureWaitForFrameDone(Camera.Handle,&Camera.Frame,PVINFINITE);
            if(!Err)
            {
                if(Camera.Frame.Status == ePvErrCancelled)
                    Err = ePvErrCancelled;  
            }   
        }
    }
}

// setup and start streaming
bool CameraStart(tCamera& Camera)
{
    unsigned long FrameSize = 0;

    // Auto adjust the packet size to max supported by the network, up to a max of 8228.
    // NOTE: In Vista, if the packet size on the network card is set lower than 8228,
    //       this call may break the network card's driver. See release notes.
    //
    //PvCaptureAdjustPacketSize(Camera.Handle,8228);

    // how big should the frame buffers be?
    if(!PvAttrUint32Get(Camera.Handle,"TotalBytesPerFrame",&FrameSize))
    {
        bool failed = false;

        // allocate the buffer for the frame
        Camera.Frame.ImageBuffer = new char[FrameSize];
        if(Camera.Frame.ImageBuffer)
            Camera.Frame.ImageBufferSize = FrameSize;
        else
            failed = true;

        if(!failed)

        {
            // set the camera is acquisition mode
            if(!PvCaptureStart(Camera.Handle))
            {
                // start the acquisition and make sure the trigger mode is "freerun"
                if(PvCommandRun(Camera.Handle,"AcquisitionStart"))
                {
                    // if that fail, we reset the camera to non capture mode
                    PvCaptureEnd(Camera.Handle) ;
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
void CameraStop(tCamera& Camera)
{
    PvCommandRun(Camera.Handle,"AcquisitionStop");
    PvCaptureEnd(Camera.Handle);  
}

// unsetup the camera
void CameraUnsetup(tCamera& Camera)
{
    // dequeue all the frame still queued (this will block until they all have been dequeued)
    PvCaptureQueueClear(Camera.Handle);
 
    // delete the allocated buffer
    delete [] (char*)Camera.Frame.ImageBuffer;
}

#ifdef _WINDOWS
unsigned long __stdcall ThreadFunc(void *pContext)
#else
void *ThreadFunc(void *pContext)
#endif
{
    tCamera* Camera = (tCamera*)pContext;

    if(!PvCameraOpenByAddr(Camera->IP,ePvAccessMaster,&(Camera->Handle)))
    {
        char IP[128];
        char Name[128];

        // read the sensor size
        if(!PvAttrStringGet(Camera->Handle,"DeviceIPAddress",IP,128,NULL) &&
           !PvAttrStringGet(Camera->Handle,"CameraName",Name,128,NULL))
        {
            printf("%u : camera %s (%s) was opened\n",Camera->ID,IP,Name);

            if(CameraStart(*Camera))
            {
                CameraStream(*Camera);
                CameraStop(*Camera);
                CameraUnsetup(*Camera);
            }
            else
                printf("%u : failed to start the stream on a camera\n",Camera->ID);
        }
        else
            printf("%u : camera was opened but there's some issues\n",Camera->ID);

        PvCameraClose(Camera->Handle);
        Camera->Handle = 0;
    }
    else
        printf("%u : camera failed to be opened\n",Camera->ID);

    return 0;
}

// CTRL-C handler
#ifdef _WINDOWS
BOOL WINAPI CtrlCHandler(DWORD dwCtrlType)
#else
void CtrlCHandler(int Signo)
#endif	
{
    // set the flag
    GSession.Stop = true;  

    // and dequeue any queued frames for each camera
    for(int i=0;i<GSession.Count;i++)
        if(GSession.Cameras[i].Handle)
            PvCaptureQueueClear(GSession.Cameras[i].Handle);
    
    #ifndef _WINDOWS
    signal(SIGINT, CtrlCHandler);
    #else
    return true;
    #endif
}

// main
int main(int argc, char* argv[])
{
    // initialise the Prosilica API
    if(!PvInitialize())
    { 
        memset(&GSession,0,sizeof(tSession));

        SetConsoleCtrlHandler(&CtrlCHandler, TRUE);
      
        if(argc>1)
        {
            GSession.Count = argc - 1;
            GSession.Cameras = new tCamera[GSession.Count];
            if(GSession.Cameras)
            {
                int i;
               
                memset(GSession.Cameras,0,sizeof(tCamera) * GSession.Count);

                for(i=1;i<argc;i++)
                {
                    GSession.Cameras[i-1].IP = inet_addr(argv[i]);
                    GSession.Cameras[i-1].ID = i;
                }

                printf("%d cameras are going to be opened\n",GSession.Count);
             
                // loop over the camera and spawn the associated threads
                for(i=0;i<GSession.Count;i++)
                {
                    if(GSession.Cameras[i].IP)
                    {
                        #ifdef _WINDOWS	
                        GSession.Cameras[i].ThHandle = CreateThread(NULL,NULL,ThreadFunc,&GSession.Cameras[i],NULL,&(GSession.Cameras[i].ThId));
                        #else
                        pthread_create(&GSession.Cameras[i].ThHandle,NULL,ThreadFunc,&GSession.Cameras[i]);
                        #endif    
                    }
                }

                // until CTRL-C is pressed we will display simple streaming statistics
                while(!GSession.Stop)
                {
                    for(i=0;i<GSession.Count;i++)
                    {
                        if(GSession.Cameras[i].Handle)
                            CameraStats(GSession.Cameras[i]);
                        if(i<GSession.Count - 1)
                            printf(" ");
                    }

                    printf("\r");

                    Sleep(30);
                }

                // loop over the camera and wait for the associated thread to terminate
                for(i=0;i<GSession.Count;i++)
                {
                    if(GSession.Cameras[i].ThHandle)
                    {
                        #ifdef _WINDOWS		
                        WaitForSingleObject(GSession.Cameras[i].ThHandle,INFINITE);
                        #else
                        pthread_join(GSession.Cameras[i].ThHandle,NULL);
                        #endif   
                    }
                }

                delete [] GSession.Cameras;
            }
        }
        else
            printf("usage: MultiStream <Camera IP #1> <Camera IP#2> ...\n");

        // uninitialise the API
        PvUnInitialize();
    }

    return 0;
}
