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
| for capturing. It then wait for the user to press a key before triggering the
| camera and saving the frame to a TIFF file if the capture was successful
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
#include <time.h>
#endif

#include <PvApi.h>
#include <ImageLib.h>

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

// wait for the user to press q
bool WaitForUserToQuitOrSnap()
{
    char c;

    do
    {
        c = getc(stdin);

    } while(c != 'q' && c != 's');

    return c == 's';
}

// get the first camera found
bool CameraGet(tCamera* Camera)
{
    tPvUint32 count,connected;
    tPvCameraInfo list;

    count = PvCameraList(&list,1,&connected);
    if(count == 1)
    {
        Camera->UID = list.UniqueId;
        printf("got camera %s\n",list.SerialString);
        return true;
    
    }
    else
        return false;
}

// open the camera
bool CameraSetup(tCamera* Camera)
{
    return !PvCameraOpen(Camera->UID,ePvAccessMaster,&(Camera->Handle));   
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
        Camera->Frame.Context[0]  = Camera;
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
    PvCaptureEnd(Camera->Handle);  
}

// snap and save a frame from the camera
void CameraSnap(tCamera* Camera)
{
    if(!PvCaptureQueueFrame(Camera->Handle,&(Camera->Frame),NULL))
    {
        printf("triggering the camera ...\n");

        PvCommandRun(Camera->Handle,"FrameStartTriggerSoftware");

        printf("waiting for the frame to be done ...\n");

        while(PvCaptureWaitForFrameDone(Camera->Handle,&(Camera->Frame),10) == ePvErrTimeout)
            printf("still waiting ...\n");

        if(Camera->Frame.Status == ePvErrSuccess)
        {
            sprintf(Camera->Filename,"./snap%04lu.tiff",++Camera->Counter);

            if(!ImageWriteTiff(Camera->Filename,&(Camera->Frame)))
                printf("Failed to save the grabbed frame!");
            else
                printf("frame saved\n");
        }
        else
            printf("the frame failed to be captured ... %u\n",Camera->Frame.Status);
    }
    else
        printf("failed to enqueue the frame\n");
}

// unsetup the camera
void CameraUnsetup(tCamera* Camera)
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

        // wait for a camera to be plugged
        WaitForCamera();

        // get a camera from the list
        if(CameraGet(&Camera))
        {
            // setup the camera
            if(CameraSetup(&Camera))
            {
                // strat streaming from the camera
                if(CameraStart(&Camera))
                {
                    printf("camera is ready now. Press q to quit or s to take a picture\n");
                    // wait for the user to quit or snap
                    while(WaitForUserToQuitOrSnap())
                    {
                        // snap now
                        CameraSnap(&Camera);
                        printf("camera is waiting trigger. Press q to quit or s to take a picture\n");
                    }
                    // stop the streaming
                    CameraStop(&Camera);
                }
                else
                    printf("failed to start streaming\n");

                // unsetup the camera
                CameraUnsetup(&Camera);
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
