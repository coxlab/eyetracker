/*
| ==============================================================================
| Copyright (C) 2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code dumps, to a text file, all the attributes of a camera specified
| by its IP address, or of the first camera visible on the host computer.
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

// camera data
typedef struct 
{
    tPvHandle       Handle;
    tPvCameraInfo   Info;

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
#endif

// wait for a camera to be plugged
void WaitForCamera()
{
    printf("waiting for a camera");
    while(!PvCameraCount())
    {
        printf(".");fflush(stdout);
        Sleep(250);
    }
    printf("\n");
}

// get the first camera found
bool CameraGrab()
{
    return PvCameraList(&(GCamera.Info),1,NULL) >= 1;
}

// open the camera
bool CameraOpen()
{
    if(!PvCameraOpen(GCamera.Info.UniqueId,ePvAccessMonitor,&(GCamera.Handle)))
        return true;
    else
        return false;
}

// open the camera
bool CameraOpen(unsigned long IP)
{
    if(!PvCameraInfoByAddr(IP,&GCamera.Info,NULL))
        return CameraOpen();
    else
        return false;
}

// close the camera
void CameraClose()
{
    PvCameraClose(GCamera.Handle); 
}

// display info on a given attribute of the camera
void QueryAttribute(FILE* File,const char* Label)
{
    tPvAttributeInfo lInfo;

    if(!PvAttrInfo(GCamera.Handle,Label,&lInfo))
    {
        if(lInfo.Datatype != ePvDatatypeCommand && strcmp(lInfo.Category,"/Stats"))
        {
            fprintf(File,"%-30s",Label); 
            
            switch(lInfo.Datatype)
            {           
                case ePvDatatypeString:
                {
                    char lValue[128];
    
                    // we assume here that any string value will be less than 128 characters
                    // long, wich we may not be the case
                    
                    if(!PvAttrStringGet(GCamera.Handle,Label,lValue,128,NULL))
                        fprintf(File," = %s\n",lValue);
                    else
                        fprintf(File," = ERROR!\n");
    
                    break;                
                }
                case ePvDatatypeEnum:
                {
                    char lValue[128];
    
                    // we assume here that any string value will be less than 128 characters
                    // long, wich we may not be the case
                    
                    if(!PvAttrEnumGet(GCamera.Handle,Label,lValue,128,NULL))
                        fprintf(File," = %s\n",lValue);
                    else
                        fprintf(File," = ERROR!\n");
                    break;
                }
                case ePvDatatypeUint32:
                {
                    tPvUint32 lValue;
                    
                    if(!PvAttrUint32Get(GCamera.Handle,Label,&lValue))
                        fprintf(File," = %lu\n",lValue);
                    else
                        fprintf(File," = ERROR!\n");
                    break;
                }
                case ePvDatatypeFloat32:
                {
                    tPvFloat32 lValue;
                    
                    if(!PvAttrFloat32Get(GCamera.Handle,Label,&lValue))
                        fprintf(File," = %f\n",lValue);
                    else
                        fprintf(File," = ERROR!\n");
                    break;
                }
                default:
                    printf("\n");
            }
        }
    }
}

// list all the attributes
void ListAttributes()
{
    tPvUint32 lCount;
    tPvAttrListPtr lAttrs;
    FILE* file;
    char name[18];
    
    sprintf(name,"%s.txt",GCamera.Info.SerialString);
    
    if((file = fopen(name,"w")))
    {
        printf("writing camera attribute to %s\n",name);        
        
        fprintf(file,"%s\n\n",GCamera.Info.SerialString);
    
        if(!PvAttrList(GCamera.Handle,&lAttrs,&lCount))
        {
            for(tPvUint32 i=0;i<lCount;i++)
                QueryAttribute(file,lAttrs[i]);
        }
        
        fclose(file);
    }
    else
        printf("sorry, failed to create the output file\n");
}

int main(int argc, char* argv[])
{
    // initialise the Prosilica API
    if(!PvInitialize())
    { 
        memset(&GCamera,0,sizeof(tCamera));

        // the only command line argument accepted is the IP@ of the camera to be open
        if(argc>1)
        {
            unsigned long IP = inet_addr(argv[1]);
             
            if(IP)
            {           
                // open the camera
                if(CameraOpen(IP))
                {
                    ListAttributes();
    
                    // unsetup the camera
                    CameraClose();
                }
                else
                    printf("Failed to open the camera (maybe not found?)\n");
            }
            else
                printf("a valid IP address must be entered\n");
        }
        else
        {
            // wait for a camera to be plugged
            WaitForCamera();
    
            if(CameraGrab())
            {
                // open the camera
                if(CameraOpen())
                {
                    ListAttributes();
    
                    // unsetup the camera
                    CameraClose();
                }
                else
                    printf("failed to open the camera\n");
            }
            else
                printf("failed to grab a camera!\n");
        }

        // uninitialise the API
        PvUnInitialize();
    }
    else
        printf("failed to initialise the API\n");
    

	return 0;
}
