/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
| 
|==============================================================================
|
| This sample code, continuously get the list of cameras and display it
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
#include <time.h>
#include <signal.h>
#include <arpa/inet.h>
#endif

#include <PvApi.h>

#ifndef _WINDOWS
#define TRUE 0
#endif

#define MAX_CAMERA_LIST 20
    
bool gStop = false;

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

// CTRL-C handler
#ifdef _WINDOWS
BOOL WINAPI CtrlCHandler(DWORD dwCtrlType)
#else
void CtrlCHandler(int Signo)
#endif
{
    gStop = true;     
   
    #ifndef _WINDOWS
    signal(SIGINT, CtrlCHandler);
    #else
    return true;
    #endif  
}

void ListCameras()
{
    tPvCameraInfo   cameraList[MAX_CAMERA_LIST];
    unsigned long   cameraNum = 0;
    unsigned long   cameraRle;

    while(!gStop)
    {
        printf("***********************************\n");

        // first, get list of reachable cameras.
        cameraNum = PvCameraList(cameraList,MAX_CAMERA_LIST,NULL);

       // keep how many cameras listed are reachable
        cameraRle = cameraNum;    

        // then we append the list of unreachable cameras.
        if (cameraNum < MAX_CAMERA_LIST)
        {
            cameraNum += PvCameraListUnreachable(&cameraList[cameraNum],
                                                 MAX_CAMERA_LIST-cameraNum,
                                                 NULL);
        }

        if(cameraNum)
        {
            struct in_addr addr;
            tPvIpSettings Conf;
            tPvErr lErr;
            
            // and display them
            for(unsigned long i=0;i<cameraNum;i++)
            {
                if(i < cameraRle)
                {
                    // get the camera's IP configuration
                    if((lErr = PvCameraIpSettingsGet(cameraList[i].UniqueId,&Conf)) == ePvErrSuccess)
                    {
                        addr.s_addr = Conf.CurrentIpAddress;
                        printf("%s - %8s - Unique ID = % 8lu IP@ = %15s [%s]\n",cameraList[i].SerialString,
                                                                    cameraList[i].DisplayName,
                                                                    cameraList[i].UniqueId,
                                                                    inet_ntoa(addr),
                                                                    cameraList[i].PermittedAccess & ePvAccessMaster ? "available" : "in use");
                    }
                    else
                        printf("%s - %8s - Unique ID = % 8lu (unavailable, %u)\n",cameraList[i].SerialString,
                               cameraList[i].DisplayName,
                               cameraList[i].UniqueId,lErr);      
                }
                else
                    printf("%s - %8s - Unique ID = % 8lu (*)\n",cameraList[i].SerialString,
                                                              cameraList[i].DisplayName,
                                                              cameraList[i].UniqueId);      
            }

            if(cameraNum != cameraRle)
                printf("(*) camera is not reachable\n");
        }
        else
            printf("No camera detected ...\n");
        
        fflush(stdout);

        Sleep(1500);
    }
    
    printf("**************************************\n");
}

int main(int argc, char* argv[])
{
    // initialise the Prosilica API
    if(!PvInitialize())
    { 
        // set the handler for CTRL-C
        SetConsoleCtrlHandler(CtrlCHandler, TRUE);
	
        // the following call will only return upon CTRL-C
        ListCameras();
        
        // uninit the API
        PvUnInitialize();
    }
    else
        printf("failed to initialise the API\n");
    

	return 0;
}
