/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code allow to set/get the value of an attribute or query its type
| and range
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
#include <strings.h>
#include <ctype.h>

#include <unistd.h>
#include <time.h>
#include <signal.h>
#include <arpa/inet.h>

#include <PvApi.h>

// put the calling thread to sleep for a given amount of millisecond
void Sleep(unsigned int time)
{
    struct timespec t,r;
    
    t.tv_sec    = time / 1000;
    t.tv_nsec   = (time % 1000) * 1000000;    
    
    while(nanosleep(&t,&r)==-1)
        t = r;
}

// display the usage details
void ShowUsage()
{
    printf("usage: CamAttr -u <camera unique ID>| -i <camera IP> -g|-s|-r|-t|-l [<label>] [<value>]\n");
    printf("-u\tcamera unique ID\n");
    printf("-i\tcamera IP address\n");
    printf("-l\tlist all attributes label\n");
    printf("-g\tget value\n");
    printf("-s\tset value\n");
    printf("-r\tget range\n");
    printf("-t\tget type\n");
    printf("-m\tget impact\n");
}

// convert a type into a string
const char* TypeToString(tPvDatatype aType)
{
    switch(aType)
    {
        case ePvDatatypeUnknown:
            return "unknown";
        case ePvDatatypeCommand:
            return "command";
        case ePvDatatypeRaw:
            return "raw";
        case ePvDatatypeString:
            return "string";
        case ePvDatatypeEnum:
            return "enum";
        case ePvDatatypeUint32:
            return "uint32";
        case ePvDatatypeFloat32:
            return "float32";
        case ePvDatatypeInt64:
            return "int64"; 
        case ePvDatatypeBoolean:
            return "boolean";                
        default:
            return "";
    }
}

tPvErr AttrList(tPvHandle Camera)
{
    tPvErr          Err;
    tPvUint32       Count;
    tPvAttrListPtr  Attrs;

    if(!(Err = PvAttrList(Camera,&Attrs,&Count)))
        for(tPvUint32 i=0;i<Count;i++)
            printf("%s\n",Attrs[i]);

    return Err;            
}

// print the attribute type
tPvErr AttrType(tPvHandle Camera,const char* Label)
{
    tPvErr              Err;
    tPvAttributeInfo    Info;

    if(!(Err = PvAttrInfo(Camera,Label,&Info)))
        printf("%s\n",TypeToString(Info.Datatype));    

    return Err;            
}

// print the attribute range of value
tPvErr AttrRange(tPvHandle Camera,const char* Label)
{
    tPvErr              Err;
    tPvAttributeInfo    Info;
    
    if(!(Err = PvAttrInfo(Camera,Label,&Info)))
        switch(Info.Datatype)
        {
            case ePvDatatypeEnum:
            {
                char Range[512];
            
                if(!(Err = PvAttrRangeEnum(Camera,Label,Range,512,NULL)))
                    printf("%s\n",Range);
                              
                break;
            }
            case ePvDatatypeUint32:
            {
                tPvUint32 Min,Max;
            
                if(!(Err = PvAttrRangeUint32(Camera,Label,&Min,&Max)))
                    printf("%lu : %lu\n",Min,Max);

                break;
            }
            case ePvDatatypeInt64:
            {
                tPvInt64 Min,Max;
            
                if(!(Err = PvAttrRangeInt64(Camera,Label,&Min,&Max)))
                    printf("%Ld : %Ld\n",Min,Max);

                break;
            }            
            case ePvDatatypeFloat32:
            {
                tPvFloat32 Min,Max;
            
                if(!(Err = PvAttrRangeFloat32(Camera,Label,&Min,&Max)))
                    printf("%f : %f\n",Min,Max);

                break;
            }
            default:
                break;
        }
    
    return Err;            
}

// print the value of an attribute
tPvErr AttrRead(tPvHandle Camera,const char* Label)
{
    tPvErr              Err;
    tPvAttributeInfo    Info;
    
    if(!(Err = PvAttrInfo(Camera,Label,&Info)))
        switch(Info.Datatype)
        {
            case ePvDatatypeString:
            {
                char String[256];
            
                if(!(Err = PvAttrStringGet(Camera,Label,String,256,NULL)))
                    printf("%s\n",String);
                          
                break;
            }
            case ePvDatatypeEnum:
            {
                char String[256];
            
                if(!(Err = PvAttrEnumGet(Camera,Label,String,256,NULL)))
                    printf("%s\n",String);
                          
                break;
            }
            case ePvDatatypeUint32:
            {
                tPvUint32 Value;
            
                if(!(Err = PvAttrUint32Get(Camera,Label,&Value)))
                    printf("%lu\n",Value);
                          
                break;
            } 
            case ePvDatatypeInt64:
            {
                tPvInt64 Value;
            
                if(!(Err = PvAttrInt64Get(Camera,Label,&Value)))
                    printf("%Ld\n",Value);
                          
                break;
            }                         
            case ePvDatatypeFloat32:
            {
                tPvFloat32 Value;
            
                if(!(Err = PvAttrFloat32Get(Camera,Label,&Value)))
                    printf("%f\n",Value);
                          
                break;
            } 
            case ePvDatatypeBoolean:
            {
                tPvBoolean Value;
            
                if(!(Err = PvAttrBooleanGet(Camera,Label,&Value)))
                    printf("%s\n",Value ? "true" : "false");
                          
                break;
            }                       
            default:
                break;
        }
    
    return Err;            
}

// write the value of an attribute
tPvErr AttrWrite(tPvHandle Camera,const char* Label,const char* Value)
{
    tPvErr              Err;
    tPvAttributeInfo    Info;
    
    if(!(Err = PvAttrInfo(Camera,Label,&Info)))
        switch(Info.Datatype)
        {
            case ePvDatatypeEnum:
            {            
                Err = PvAttrEnumSet(Camera,Label,Value);
                          
                break;
            }
            case ePvDatatypeUint32:
            {
                tPvUint32 Uint;

                if(sscanf(Value,"%lu",&Uint) == 1)
                    Err = PvAttrUint32Set(Camera,Label,Uint);
                else
                    Err = ePvErrWrongType;    
                          
                break;
            }  
            case ePvDatatypeInt64:
            {
                tPvInt64 Sint;

                if(sscanf(Value,"%Ld",&Sint) == 1)
                    Err = PvAttrInt64Set(Camera,Label,Sint);
                else
                    Err = ePvErrWrongType;    
                          
                break;
            }                      
            case ePvDatatypeFloat32:
            {
                tPvFloat32 Float;

                if(sscanf(Value,"%f",&Float) == 1)
                    Err = PvAttrFloat32Set(Camera,Label,Float);
                else
                    Err = ePvErrWrongType;
                          
                break;
            }  
            case ePvDatatypeBoolean:
            {
                Err = PvAttrBooleanSet(Camera,Label,!strcmp("true",Value));
                          
                break;
            }                                   
            default:
                break;
        }
    
    return Err;            
}

// print the value of an attribute
tPvErr AttrImpact(tPvHandle Camera,const char* Label)
{
    tPvErr              Err;
    tPvAttributeInfo    Info;
    
    if(!(Err = PvAttrInfo(Camera,Label,&Info)))
        printf("'%s'\n",Info.Impact);
    
    return Err;
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
        bool bTyp = false;
        bool bRng = false;
        bool bLst = false;
        bool bImpact = false;
        const char* sLabel = NULL;
    
        while ((c = getopt (argc, argv, "u:i:lg:t:r:s:m:h?")) != -1)
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
                    bLst = true;
                    break;
                }
                case 'g':
                {
                    bGet   = true;
                    sLabel = optarg;
                    break;
                }
                case 's':
                {
                    bSet = true;
                    sLabel = optarg;
                    break;
                }
                case 'm':
                {
                    bImpact = true;
                    sLabel  = optarg;
                    break;
                }                
                case 'r':
                {
                    bRng = true;
                    sLabel = optarg;
                    break;
                }
                case 't':
                {
                    bTyp = true;
                    sLabel = optarg;
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
                    Err = AttrRead(Camera,sLabel);
                else
                if(bSet) // set value
                    Err = AttrWrite(Camera,sLabel,argv[argc-1]);
                else
                if(bRng) // get range
                    Err = AttrRange(Camera,sLabel);
                else
                if(bTyp) // get type
                    Err = AttrType(Camera,sLabel);
                else
                if(bLst)
                    Err = AttrList(Camera); 
                else
                if(bImpact) // get impact
                    Err = AttrImpact(Camera,sLabel);                                 

                if(Err)
                {
                    switch(Err)
                    {
                        case ePvErrNotFound:
                        {
                            fprintf(stderr,"this attribute was not found\n");
                            break;
                        }
                        case ePvErrOutOfRange:
                        {
                            fprintf(stderr,"the value is out of range\n");
                            break;
                        }
                        case ePvErrWrongType:
                        {
                            fprintf(stderr,"this attribute is not of this type\n");
                            break;                              
                        }
                        default:
                            fprintf(stderr,"sorry, an error occured (%u)\n",Err);
                    }

                    err = 1;
                }

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
