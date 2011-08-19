/*
| ==============================================================================
| Copyright (C) 2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code streams from a specified camera and render the image as ASCII
| art using the AA library. No scaling of the image is performed, the ROI is set
| to match what can be rendered.
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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <aalib.h>

#include <time.h>
#include <unistd.h>
#include <signal.h>
#include <sys/times.h>
#include <arpa/inet.h>

#include <PvApi.h>

#define FRAMESCOUNT 8

typedef struct 
{
    unsigned long   UID;
    tPvHandle       Handle;
    tPvFrame        Frames[FRAMESCOUNT];
    bool            Abort;
    aa_context*     Context;
    
} tCamera;


// global camera data
tCamera         GCamera;

struct tms      gTMS;
unsigned long   gT0 = times(&gTMS);

void Sleep(unsigned int time)
{
    struct timespec t,r;
    
    t.tv_sec    = time / 1000;
    t.tv_nsec   = (time % 1000) * 1000000;    
    
    while(nanosleep(&t,&r)==-1)
        t = r;
}

void SetConsoleCtrlHandler(void (*func)(int))
{
    signal(SIGINT, func);
}

// wait forever (at least until the user CTRL-C)
void WaitForEver()
{
  while(!GCamera.Abort)
        Sleep(500);
}

// render the specified frame
void FrameRender(tPvFrame* pFrame)
{
    unsigned char* src = (unsigned char*)pFrame->ImageBuffer;
    unsigned char* dst = aa_image(GCamera.Context);
    
    // copy data in the buffer
    memcpy(dst,src,pFrame->ImageBufferSize);
            
    // render
    aa_fastrender(GCamera.Context,0,0,
                  aa_scrwidth(GCamera.Context),
                  aa_scrheight(GCamera.Context));
    aa_flush(GCamera.Context);    
}

// callback called when a frame is done
void FrameDoneCB(tPvFrame* pFrame)
{    
    // if the frame was completed (or if data were missing/lost) we re-enqueue it
    if(pFrame->Status == ePvErrSuccess  || 
       pFrame->Status == ePvErrDataLost ||
       pFrame->Status == ePvErrDataMissing)
    {
        // render the frame
        if(pFrame->Status == ePvErrSuccess)
            FrameRender(pFrame);        
        // re-enqueue
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
bool CameraOpen(unsigned long IP)
{
   return !PvCameraOpenByAddr(IP,ePvAccessMaster,&(GCamera.Handle));
}

// setup  streaming
bool CameraSetup(int w,int h)
{
    unsigned long FrameSize = 0;
    unsigned long sWidth,sHeight;
    unsigned long rWidth,rHeight;
    unsigned long CenterX,CenterY;
    tPvErr Err;
        
    // camera is forced in mono8 streaming and with the specified ROI
    if(!(Err = PvAttrEnumSet(GCamera.Handle,"PixelFormat","Mono8")) &&
       !(Err = PvAttrUint32Get(GCamera.Handle,"SensorWidth",&sWidth)) &&
       !(Err = PvAttrUint32Get(GCamera.Handle,"SensorHeight",&sHeight)))
    {
        rWidth  = sWidth / 2;
        rHeight = sHeight / 2;

        CenterX = rWidth - 1;
        CenterY = rHeight - 1;
        
        rWidth = w;
        rHeight = h;
    
        // set the width&height
        if(!(Err = PvAttrUint32Set(GCamera.Handle,"Width",rWidth)) &&
             !(Err = PvAttrUint32Set(GCamera.Handle,"Height",rHeight)))
        {
            if(!(Err = PvAttrUint32Set(GCamera.Handle,"RegionX",CenterX - rWidth / 2)))
                Err = PvAttrUint32Set(GCamera.Handle,"RegionY",CenterY - rHeight / 2);
        }
    }
   
    if(!Err)
    {
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
                    
            return !failed;
        }
        else
            return false;
    }
    else
        return false;
}

// start  streaming
bool CameraStart()
{
    // set the camera is acquisition mode
    if(!PvCaptureStart(GCamera.Handle))
    {
        // start the acquisition and make sure the trigger mode is "FixedRate" & 30fps
        if(PvAttrFloat32Set(GCamera.Handle,"FrameRate",30) ||
           PvCommandRun(GCamera.Handle,"AcquisitionStart") ||
           PvAttrEnumSet(GCamera.Handle,"FrameStartTriggerMode","FixedRate"))
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
        
            return true;
        }
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

void CtrlCHandler(int Signo)
{  
    GCamera.Abort = true;    
    signal(SIGINT, CtrlCHandler);
}

int main(int argc, char* argv[])
{
    // initialise the Prosilica API
    if(!PvInitialize())
    { 
        memset(&GCamera,0,sizeof(tCamera));

        SetConsoleCtrlHandler(&CtrlCHandler);
                
         // the only command line argument accepted is the IP@ of the camera to be open
        if(argc>1)
        {
            unsigned long IP = inet_addr(argv[1]);
             
            if(IP)
            {                               
                // initialise AA (with default)
                if((GCamera.Context = aa_autoinit(&aa_defparams)))
                {
                    printf("AA initialised (%ux%u)\n",aa_imgwidth(GCamera.Context),aa_imgheight(GCamera.Context));    
                    
                    // setup the camera
                    if(CameraOpen(IP))
                    {
                        // setup the camera to stream with a given ROI
                        if(CameraSetup(aa_imgwidth(GCamera.Context),aa_imgheight(GCamera.Context)))
                        {
                            // and start the streaming
                            if(CameraStart())
                            {
                                printf("camera is streaming now. Press CTRL-C to terminate\n");
        
                                // we wait until the user press CTRL-C
                                WaitForEver();
                            }
                        }
                        else
                            printf("failed to start streaming\n");
        
                        // unsetup the camera
                        CameraUnsetup();
                    }
                    else
                        printf("failed to open the camera\n"); 
                  
                    aa_close(GCamera.Context);
                }
                else
                    printf("sorry, failed to initialise AA\n");                 
            }
            else
                printf("the supplied IP @ isn't valid\n");       
        }
        else
            printf("usage: AAViewer <IP @>\n");
       
        // uninitialise the API
        PvUnInitialize();
    }
    else
        printf("failed to initialise the API\n");
    

	return 0;
}
