/*
| ==============================================================================
| Copyright (C) 2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code demonstrates how to retreive the Genicam XML file from the
| camera onboard memory.
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

unsigned int BruteQuadlets(unsigned int aValue)
{
    while(aValue % 4)
        aValue++;

    return aValue;
}
    
// open the camera
tPvHandle CameraOpen(unsigned long IP)
{
    tPvHandle Handle;
    
    if(PvCameraOpenByAddr(IP,ePvAccessMonitor,&Handle) == ePvErrSuccess)
        return Handle;
    else
        return NULL;
}

// close the camera
void CameraClose(tPvHandle Handle)
{
    PvCameraClose(Handle); 
}

// read a specified number of memory register from the camera
unsigned long CameraMemRead(tPvHandle Handle,unsigned long From,unsigned long Quad,char* Buffer)
{
    unsigned long  Index = 0;
    unsigned long  Address = From;
    unsigned long  Memory;
    unsigned int*  Store = (unsigned int*)Buffer;
    
    for(Index=0;Index<Quad;Index++)
    {
        if(PvRegisterRead(Handle,1,&Address,&Memory,NULL) != ePvErrSuccess)
            break;
        else
        {
            // as PvRegisterRead() will convert the register value into the host format,
            // we swap it back to the network format (which is the camera's format)
            Store[Index] = htonl(Memory);
            Address += 4;         
        }
    }
    
    return Index;
}

// reset the camera
void CameraGetFile(tPvHandle Handle)
{
    char buffer[512];
        
    // read the XML file name & details
    if(CameraMemRead(Handle,0x0200,128,buffer) == 128)
    {
        unsigned int reg,len,got,step = 512;
        char name[64];
               
        // scan the string to retreive the filename, register offset and length
        sscanf(buffer,"Local:%24s;%x;%x",name,&reg,&len); 
       
        if(reg && len)
        {
            FILE* file = fopen(name,"w+");
            
            if(file)
            {
                printf("downloading XML data to %s ",name);
                
                while(len)
                {
                    got = CameraMemRead(Handle,reg,step / 4,buffer);
                    if(got)
                    {
                        fwrite(buffer,1,got * 4,file);
                        reg  += step;
                        len -= got;
                        if(len && len < step)
                        {
                            step = got = len;
                            if(step % 4)
                                step = BruteQuadlets(step);
                        }
                        printf(".");
                        fflush(stdout);
                    }
                    else
                        break;
                } 
                
                printf("\n");
                fclose(file);
            }
            else
                printf("sorry, couldn't create the XML file\n");
        }    
    }
    else
        printf("sorry, failed to read XML file register\n");
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
                    // get the XML file
                    CameraGetFile(Handle);
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
            printf("usage : GetXMLFile <IP@>\n");

        // uninitialise the API
        PvUnInitialize();
    }
    else
        printf("failed to initialise the API\n");
    

	return 0;
}
