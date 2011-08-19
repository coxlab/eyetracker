/*
| ==============================================================================
| Copyright (C) 2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code demonstrates how to save or load the camera setup from/to a
| simple text file.
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
    printf("usage: CamSetup -u <camera unique ID>| -i <camera IP> -l|-s <file>\n");
    printf("-u\tcamera unique ID\n");
    printf("-i\tcamera IP address\n");
    printf("-l\tload setup\n");
    printf("-s\tsave setup\n");
}

// trim the supplied string left and right
char* strtrim(char *aString)
{
    int i;
    int lLength = strlen(aString);
    char* lOut = aString;
    
    // trim right
    for(i=lLength-1;i>=0;i--)   
        if(isspace(aString[i]))
            aString[i]='\0';
        else
            break;
                
    lLength = strlen(aString);    
        
    // trim left
    for(i=0;i<lLength;i++)
        if(isspace(aString[i]))
            lOut = &aString[i+1];    
        else
            break;    
    
    return lOut;
}

// set the value of a given attribute from a value encoded in a string
bool String2Value(tPvHandle aCamera,const char* aLabel,tPvDatatype aType,char* aValue)
{
    switch(aType)
    {           
        case ePvDatatypeString:
        {   
            if(!PvAttrStringSet(aCamera,aLabel,aValue))
                return true;
            else
                return false;     
        }
        case ePvDatatypeEnum:
        {            
            if(!PvAttrEnumSet(aCamera,aLabel,aValue))
                return true;
            else
                return false;
        }
        case ePvDatatypeUint32:
        {
            tPvUint32 lValue = atol(aValue);
            tPvUint32 lMin,lMax;
            
           if(!PvAttrRangeUint32(aCamera,aLabel,&lMin,&lMax))
           {
               if(lMin > lValue)
                   lValue = lMin;
               else
               if(lMax < lValue)
                   lValue = lMax;
                                        
               if(!PvAttrUint32Set(aCamera,aLabel,lValue))
                   return true;
               else
                   return false;
           }
           else
               return false;
        }
        case ePvDatatypeFloat32:
        {
            tPvFloat32 lValue = (tPvFloat32)atof(aValue);
            tPvFloat32 lMin,lMax;
            
           if(!PvAttrRangeFloat32(aCamera,aLabel,&lMin,&lMax))
           {
                if(lMin > lValue)
                   lValue = lMin;
                else
                if(lMax < lValue)
                   lValue = lMax;            
            
                if(!PvAttrFloat32Set(aCamera,aLabel,lValue))
                    return true;
                else
                    return false;
           }
           else
               return false;
        }
        default:
            return false;
    }       
}

// encode the value of a given attribute in a string
bool Value2String(tPvHandle aCamera,const char* aLabel,tPvDatatype aType,char* aString,unsigned long aLength)
{   
    switch(aType)
    {           
        case ePvDatatypeString:
        {   
            if(!PvAttrStringGet(aCamera,aLabel,aString,aLength,NULL))
                return true;
            else
                return false;     
        }
        case ePvDatatypeEnum:
        {            
            if(!PvAttrEnumGet(aCamera,aLabel,aString,aLength,NULL))
                return true;
            else
                return false;
        }
        case ePvDatatypeUint32:
        {
            tPvUint32 lValue;
            
            if(!PvAttrUint32Get(aCamera,aLabel,&lValue))
            {
                sprintf(aString,"%lu",lValue);
                return true;
            }
            else
                return false;
            
        }
        case ePvDatatypeFloat32:
        {
            tPvFloat32 lValue;
            
            if(!PvAttrFloat32Get(aCamera,aLabel,&lValue))
            {
                sprintf(aString,"%g",lValue);
                return true;
            }
            else
                return false;
        }
        default:
            return false;
    }        
}

// write a given attribute in a text file
void WriteAttribute(tPvHandle aCamera,const char* aLabel,FILE* aFile)
{
    tPvAttributeInfo lInfo;

    if(!PvAttrInfo(aCamera,aLabel,&lInfo))
    {
        if(lInfo.Datatype != ePvDatatypeCommand &&
           (lInfo.Flags & ePvFlagWrite))
        {
            char lValue[128];
            
            if(Value2String(aCamera,aLabel,lInfo.Datatype,lValue,128))
                fprintf(aFile,"%s = %s\n",aLabel,lValue);
            else
                fprintf(stderr,"attribute %s couldn't be saved\n",aLabel);            
        }   
    }
}

// read the attribute from one of the file's text line
void ReadAttribute(tPvHandle aCamera,char* aLine)
{
    char* lValue = strchr(aLine,'=');
    char* lLabel;
    
    if(lValue)
    {
        lValue[0] = '\0';
        lValue++;    
    
        lLabel = strtrim(aLine);
        lValue = strtrim(lValue);
        
        if(strlen(lLabel) && strlen(lValue))
        {
            tPvAttributeInfo lInfo;
                           
            if(!PvAttrInfo(aCamera,lLabel,&lInfo))
            {
                if(lInfo.Datatype != ePvDatatypeCommand &&
                (lInfo.Flags & ePvFlagWrite))
                {      
                    if(!String2Value(aCamera,lLabel,lInfo.Datatype,lValue))
                        fprintf(stderr,"attribute %s couldn't be loaded\n",lLabel);                          
                } 
            }     
        }
    }
}

// load the setup of a camera from the given file
bool SetupLoad(tPvHandle aCamera,const char* aFile)
{
    FILE* lFile = fopen(aFile,"r");
    
    if(lFile)
    {
        char lLine[256];
        
        while(!feof(lFile))
        {
            if(fgets(lLine,256,lFile))
                ReadAttribute(aCamera,lLine);
        }
        
        fclose(lFile);
        
        return true;
    }
    else
        return false;    
}

// save the setup of a camera from the given file
bool SetupSave(tPvHandle aCamera,const char* aFile)
{
    FILE* lFile = fopen(aFile,"w+");
    
    if(lFile)
    {
        bool            lRet = true;
        tPvAttrListPtr  lAttrs; 
        tPvUint32       lCount;    
        
        if(!PvAttrList(aCamera,&lAttrs,&lCount))
        {
            for(tPvUint32 i=0;i<lCount;i++)
                WriteAttribute(aCamera,lAttrs[i],lFile);
        }     
        else
            lRet = false;   
        
        fclose(lFile);
        
        return lRet;
    }
    else
        return false;    
}

//
int main(int argc, char* argv[])
{
    int err = 0;

    // initialise the Prosilica API
    if(!PvInitialize())
    {
        int c;
        unsigned long uid = 0;
        unsigned long addr = 0;
        bool bLoad = false;
        bool bSave = false;
    
        while ((c = getopt (argc, argv, "u:i:ls:h?")) != -1)
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
                case 'l':
                {
                    bLoad = true;
                    break;
                }
                case 's':
                {
                    bSave = true;
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

        if((uid || addr) && (bSave || bLoad))
        {
            tPvHandle       Camera;
            tPvAccessFlags  Flags = (bLoad ? ePvAccessMaster : ePvAccessMonitor);
            tPvErr          Err;
            bool            Done = false;

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
                if(bLoad) // load the camera setup
                    Done = SetupLoad(Camera,argv[argc-1]);
                else
                if(bSave) // save the camera setup
                    Done = SetupSave(Camera,argv[argc-1]);          

                if(!Done)
                    fprintf(stderr,"sorry, an error occured\n");

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

