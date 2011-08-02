/*
| ==============================================================================
| Copyright (C) 2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code demonstrates how to read and write to the user-defined memory
| of the camera
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
#include <ctype.h>

#ifdef _WINDOWS
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <Winsock2.h>
#include "XGetopt.h"
#endif

#if defined(_LINUX) || defined(_QNX) || defined(_OSX)
#include <unistd.h>
#include <time.h>
#include <signal.h>
#include <arpa/inet.h>
#include <strings.h>
#endif

#include <PvApi.h>
#include <PvRegIo.h>

#if defined(_LINUX) || defined(_QNX) || defined(_OSX)
// put the calling thread to sleep for a given amount of millisecond
void Sleep(unsigned int time)
{
    struct timespec t,r;
    
    t.tv_sec    = time / 1000;
    t.tv_nsec   = (time % 1000) * 1000000;    
    
    while(nanosleep(&t,&r)==-1)
        t = r;
}
#endif

// display the usage details
void ShowUsage()
{
    printf("usage: CamMemory -u <camera unique ID>| -i <camera IP> -g|-s [<string>]\n");
    printf("-u\tcamera unique ID\n");
    printf("-i\tcamera IP address\n");
    printf("-g\tget string\n");
    printf("-s\tset string\n");
}

// Read from the user-defined memory and print the contents
tPvErr MemRead(tPvHandle aCamera)
{
    tPvErr lErr;
    unsigned char lBuffer[512];
    
    lErr = PvMemoryRead(aCamera,0x17200,512,lBuffer);
    
    if(lErr == ePvErrSuccess)
    {
        printf("value = '%s'\n",lBuffer);
        
        for(int i=0;i<512;i++)
        {
            printf("0x%02X ",lBuffer[i]);
            if(!((i + 1) % 16))
                printf("\n");       
        }
        
        printf("\n");
    }
    
    return lErr;   
}

// Write the given string to the user supplied memory
tPvErr MemWrite(tPvHandle aCamera,const char* aString)
{ 
    if(strlen(aString) < 512)
    {
        unsigned char lBuffer[512];
        unsigned long Size;
    
        memset(lBuffer,0,512);
    
        strcpy((char*)lBuffer,aString);
    
        return PvMemoryWrite(aCamera,0x17200,512,lBuffer,&Size);  
    }
    else
        return ePvErrBadParameter;
}


int main(int argc, char* argv[])
{
    int err = 0;

    // initialise the Prosilica API
    if(!PvInitialize())
    {
        int c;
        unsigned long uid = 0;
        unsigned long addr = 0;
        bool bGet = false;
        bool bSet = false;
    
        while ((c = getopt (argc, argv, "u:i:gs:h?")) != -1)
        {
            switch(c)
            {
                case 'u':
                {
                    if(optarg)
                        uid = atol(optarg);
                    
                    break;    
                }
                case 'i':
                {
                    if(optarg)
                        addr = inet_addr(optarg);
                    
                    break;    
                }                
                case 'g':
                {
                    bGet = true;
                    break;
                }
                case 's':
                {
                    bSet = true;
                    break;
                }
                case '?':
                case 'h':
                {
                    ShowUsage();
                    break;    
                }
                default:
                    break;
            }
        }

        if(uid || addr)
        {
            tPvHandle       Camera;
            tPvAccessFlags  Flags = (bSet ? ePvAccessMaster : ePvAccessMonitor);
            tPvErr          Err;

            if(uid)
            {
                // wait a bit to leave some time to the API to detect any camera
                Sleep(500);
                // and open the camera
                Err = PvCameraOpen(uid,Flags,&Camera);
            }
            else
                Err = PvCameraOpenByAddr(addr,Flags,&Camera);
                
            if(!Err)
            {   
                if(bGet) // get value
                    Err = MemRead(Camera);
                else
                if(bSet) // set value
                    Err = MemWrite(Camera,argv[argc-1]);          

                if(Err)
                    fprintf(stderr,"sorry, an error occured (%u)\n",Err);

                err = 1;

                // close the camera
                PvCameraClose(Camera);
            }
            else
            {
                if(Err == ePvErrNotFound || Err == ePvErrUnplugged)
                    fprintf(stderr,"sorry, couldn't found the camera\n");
                else
                if(Err == ePvErrAccessDenied)
                    fprintf(stderr,"sorry, this camera is already in use\n");
                else
                    fprintf(stderr,"sorry, couldn't open the camera for some reason\n");

                err = 1;    
            }    
        }
        else
        {
            ShowUsage();
            err = 1;  
        }

        // uninitialise the API
        PvUnInitialize();
    }
    else
    {
        err = 1;
        fprintf(stderr,"failed to initialise the API\n");
    }
    
	return err;
}

