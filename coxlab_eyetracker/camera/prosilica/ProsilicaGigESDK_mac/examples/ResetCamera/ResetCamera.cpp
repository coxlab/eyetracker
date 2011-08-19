/*
| ==============================================================================
| Copyright (C) 2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code resets a given camera, specified by its IP address
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
#include <arpa/inet.h>
#endif

#include <PvApi.h>
#include <PvRegIo.h>

#ifndef _WINDOWS
#define TRUE 0
#endif

// open the camera
tPvHandle CameraOpen(unsigned long IP)
{
    tPvHandle Handle;
    
    if(PvCameraOpenByAddr(IP,ePvAccessMaster,&Handle) == ePvErrSuccess)
        return Handle;
    else
        return NULL;
}

// close the camera
void CameraClose(tPvHandle Handle)
{
    PvCameraClose(Handle); 
}

// reset the camera
void CameraReset(tPvHandle Handle)
{
  unsigned long Address = 0x10008;  // register @
  unsigned long Value   = 2;        // hard-reset value
  
  PvRegisterWrite(Handle,1,&Address,&Value,NULL);
}


int main(int argc, char* argv[])
{
    // initialise the Prosilica API
    if(!PvInitialize())
    { 
        // the only command line argument accepted is the IP@ of the camera to be open
        if(argc>1)
        {
            unsigned long IP = inet_addr(argv[1]);
             
            if(IP)
            {           
                tPvHandle Handle; 
                
                // open the camera
                if((Handle = CameraOpen(IP)) != NULL)
                {
                    // send reset command
                    CameraReset(Handle);
                    // close the camera
                    CameraClose(Handle);
                }
                else
                    printf("Failed to open the camera (maybe not found?)\n");
            }
            else
                printf("a valid IP address must be entered\n");
        }
        else
            printf("usage : ResetCamera <IP@>\n");

        // uninitialise the API
        PvUnInitialize();
    }
    else
        printf("failed to initialise the API\n");
    

	return 0;
}
