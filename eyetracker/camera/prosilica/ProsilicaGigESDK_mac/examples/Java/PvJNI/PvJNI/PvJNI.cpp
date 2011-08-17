// PvJNI.cpp : Defines the entry point for the DLL application.
//

#ifdef _WINDOWS
#include "stdafx.h"
#endif

#include "PvJNI.h"
#include <PvApi.h>
#include <PvRegIo.h>
#include <stdio.h>
#include <jni.h>
#include <string.h>
#include <stdlib.h>

#include <deque>
#include <queue>

#ifdef _WINDOWS

BOOL APIENTRY DllMain( HMODULE hModule,
                       DWORD  ul_reason_for_call,
                       LPVOID lpReserved
					 )
{
	switch (ul_reason_for_call)
	{
        case DLL_PROCESS_ATTACH:
        case DLL_THREAD_ATTACH:
        case DLL_THREAD_DETACH:
        case DLL_PROCESS_DETACH:
	        break;
	}
    return TRUE;
}

#define _STDCALL __stdcall

CRITICAL_SECTION gLock;

void initLock()
{
    InitializeCriticalSection(&gLock);
}

void deleteLock()
{
    DeleteCriticalSection(&gLock);
}

void acquireLock()
{
    EnterCriticalSection(&gLock);
}

void releaseLock()
{
    LeaveCriticalSection(&gLock);
}

#else

#define _STDCALL

#define min(a,b) (a < b ? a : b)
#define max(a,b) (a > b ? a : b)

#include <pthread.h>

pthread_mutex_t gLock;

void initLock()
{
    pthread_mutexattr_t lAttr;

    pthread_mutexattr_init(&lAttr);
#ifdef _OSX
    pthread_mutexattr_settype(&lAttr,PTHREAD_MUTEX_RECURSIVE);
#else
	pthread_mutexattr_settype(&lAttr,PTHREAD_MUTEX_RECURSIVE_NP);
#endif
    pthread_mutex_init(&gLock,&lAttr);
}

void deleteLock()
{
    pthread_mutex_destroy(&gLock);
}

void acquireLock()
{
    pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS,NULL);
    pthread_mutex_lock(&gLock); 
    pthread_setcanceltype(PTHREAD_CANCEL_DEFERRED,NULL);
}

void releaseLock()
{
    pthread_mutex_unlock(&gLock);
}

#endif

#ifdef __cplusplus
extern "C" {
#endif

// type

// list of callback Java objects
typedef std::deque<jobject> tCallbacks;
// queue of allocated tPvFrame
typedef std::queue<tPvFrame*> tFramesPool;

typedef struct {

    unsigned char LByte;
    unsigned char MByte;
    unsigned char UByte;

} Packed12BitsPixel_t;

// global data

// flags
bool        gCBRegistered = false;
// list of registered callbacks (for link events)
tCallbacks  gCallbacksList;
// pool of frames structures 
tFramesPool gFramesPool;
// pointer to Java's VM
JavaVM*     gJavaVM;
// default class loader
jobject     gDefaultContextClassLoader = NULL;

// Usefull functions

/*
void _OutputString(const char* format, ...)
{
	static char output[2048];

	va_list     arg;

	va_start(arg, format);

    #ifdef _WINDOWS
	_vsnprintf(output, sizeof(output), format, arg);
	#else
	vsnprintf(output, sizeof(output), format, arg);
	#endif

	va_end(arg);     

    #ifdef _WINDOWS
	OutputDebugStringA(output);
	#else
	printf(output);
	#endif
}
*/

#define _OutputString(...)

void acquireDefaultContextClassLoader(JNIEnv* env)
{
    jclass      Class   = env->FindClass("java/lang/Thread");
    jmethodID   Method1 = env->GetStaticMethodID(Class, "currentThread","()Ljava/lang/Thread;");
    jobject     Thread  = env->CallStaticObjectMethod(Class,Method1);
    jmethodID   Method2 = env->GetMethodID(Class, "getContextClassLoader","()Ljava/lang/ClassLoader;");    
    jobject     Loader  = env->CallObjectMethod(Thread,Method2);
    
    if(env->ExceptionCheck())
    {
        _OutputString("Exception occured in PvJNI::acquireDefaultContextClassLoader\n");
        env->ExceptionClear();
    }
    else
    {
        if (Loader != NULL)
            gDefaultContextClassLoader = env->NewGlobalRef(Loader);
            
        if(!gDefaultContextClassLoader)
            _OutputString("Error in PvJNI::acquireDefaultContextClassLoader\n");
    }
    
}

void releaseDefaultContextClassLoader(JNIEnv* env)
{
    if(gDefaultContextClassLoader)
    {
        env->DeleteGlobalRef(gDefaultContextClassLoader);
        gDefaultContextClassLoader = NULL;
    }
}

/*
jobject getThreadContextClassLoader(JNIEnv* env)
{
    jclass      Class   = env->FindClass("java/lang/Thread");
    jmethodID   Method1 = env->GetStaticMethodID(Class, "currentThread","()Ljava/lang/Thread;");
    jobject     Thread  = env->CallStaticObjectMethod(Class,Method1);
    jmethodID   Method2 = env->GetMethodID(Class, "getContextClassLoader","()Ljava/lang/ClassLoader;"); 
       
    return env->CallObjectMethod(Thread,Method2);    
}

void setThreadContextClassLoader(JNIEnv* env,jobject loader)
{
    jclass      Class   = env->FindClass("java/lang/Thread");
    jmethodID   Method1 = env->GetStaticMethodID(Class, "currentThread","()Ljava/lang/Thread;");
    jobject     Thread  = env->CallStaticObjectMethod(Class,Method1);
    jmethodID   Method2 = env->GetMethodID(Class, "setContextClassLoader","(Ljava/lang/ClassLoader;)V");     

    env->CallVoidMethod(Thread,Method2,loader);        
}
*/

// get a class defined the prosilica.pv class (workaround class loading issue in multi-threaded env.)
jclass getPvClass(JNIEnv* env,const char* className)
{
    char   path[256];
    jclass someClass = NULL;
    
    sprintf(path,"prosilica.Pv$%s",className);
    
    if(gDefaultContextClassLoader)
    {
        jclass    loaderClass = env->FindClass("java/lang/ClassLoader");
        jmethodID getClass    = env->GetMethodID(loaderClass,"loadClass","(Ljava/lang/String;)Ljava/lang/Class;"); 
        
        if(getClass)
            someClass = (jclass)env->CallObjectMethod(gDefaultContextClassLoader,getClass,env->NewStringUTF(path));  	           
    }
    
    if(!someClass)
    {
        path[9]     = '/';
        someClass   = env->FindClass(path);
    }

    if(!someClass)
        _OutputString("Class %s was not found!!\n",className);
    
    return someClass;

}

// convert YUV to RGB
inline void YUV2RGB(int y,int u,int v,int& r,int& g,int& b)
{
   // u and v are +-0.5
   u -= 128;
   v -= 128;

   // Conversion (clamped to 0..255)
   r = min(max(0,(int)(y + 1.370705 * (float)v)),255);
   g = min(max(0,(int)(y - 0.698001 * (float)v - 0.337633 * (float)u)),255);
   b = min(max(0,(int)(y + 1.732446 * (float)u)),255);
}

tPvFrame* PopAFrame(JNIEnv* env,jclass Object)
{
    tPvFrame* pFrame;

    acquireLock();

    if(gFramesPool.size())
    {
        pFrame = gFramesPool.front();
        gFramesPool.pop();
    }
    else
        pFrame = new tPvFrame;

    releaseLock();

    return pFrame;
}

void PushAFrame(JNIEnv* env,jobject Object,tPvFrame* pFrame)
{
    acquireLock();

    if(gFramesPool.size() < 100)
    {
        try
        {
            gFramesPool.push(pFrame);
        } catch (...) {
            delete pFrame;
        }
    }
    else
        delete pFrame; 

    releaseLock();      
}

/*
jbyteArray GetBufferFromFrame(JNIEnv* env,jobject Frame)
{
    jclass   Class;
    jfieldID Field; 

    // get the object's class
    Class = env->GetObjectClass(Frame);
    // get the ID of the fields
    Field = env->GetFieldID(Class,"ImageBuffer","[B");
    if(Field)
        return (jbyteArray)env->GetObjectField(Frame,Field);
    else
        return NULL;
}
*/

jobject GetBufferFromFrame(JNIEnv* env,jobject Frame)
{
    jclass   Class;
    jfieldID Field; 

    // get the object's class
    Class = env->GetObjectClass(Frame);
    // get the ID of the fields
    Field = env->GetFieldID(Class,"ImageBuffer","Ljava/nio/ByteBuffer;");
    if(Field)
        return (jbyteArray)env->GetObjectField(Frame,Field);
    else
        return NULL;
}

void SetFrameInFrame(JNIEnv* env,jobject Frame,tPvFrame* pFrame)
{
    jclass   Class;
    jfieldID Field; 

    // get the object's class
    Class = env->GetObjectClass(Frame);
    // get the ID of the fields
    Field = env->GetFieldID(Class,"CachedFrame","J");
    if(Field)
        env->SetLongField(Frame,Field,(jlong)pFrame);
}

tPvFrame* GetFrameInFrame(JNIEnv* env,jobject Frame)
{
    jclass   Class;
    jfieldID Field; 

    // get the object's class
    Class = env->GetObjectClass(Frame);
    // get the ID of the fields
    Field = env->GetFieldID(Class,"CachedFrame","J");
    if(Field)
        return (tPvFrame*)env->GetLongField(Frame,Field);
    else
        return NULL;
}

// Convert an API error into the corresponding Pv.tError enumerate
jobject ConvertError(JNIEnv* env,tPvErr Err)
{
    jclass       ErrC; 
    jmethodID    ErrM;
    jobjectArray Values = NULL;

    // get the tError class
    ErrC = getPvClass(env,"tError");
    // get its "values" method
    ErrM = env->GetStaticMethodID(ErrC,"values","()[Lprosilica/Pv$tError;");
    // call the method to get the array of possible value for the enumerate
    Values = (jobjectArray)env->CallStaticObjectMethod(ErrC,ErrM);
    // use the array of tError enumerate to return the proper code
    return env->GetObjectArrayElement(Values,(jint)Err);  
}

tPvErr InvertError(JNIEnv* env,jobject Format)
{
    jclass       EvnC; 
    jmethodID    EvnM;
    jobjectArray Values = NULL;
    jsize        Count;
    jint         i;

    // get the tError class
    EvnC = getPvClass(env,"tError");
    // get its "values" method
    EvnM = env->GetStaticMethodID(EvnC,"values","()[Lprosilica/Pv$tError;");
    // call the method to get the array of possible value for the enumerate
    Values = (jobjectArray)env->CallStaticObjectMethod(EvnC,EvnM);
    //
    Count = env->GetArrayLength(Values);
    //
    for(i=0;i<Count;i++)
        if(env->IsSameObject(env->GetObjectArrayElement(Values,i),Format))
            break;
    
    if(i<Count)
        return (tPvErr)(ePvErrSuccess + i);
    else
        return ePvErrSuccess;
}

// Convert an API Event into the corresponding Pv.tLinkEvent enumerate
jobject ConvertLinkEvent(JNIEnv* env,tPvLinkEvent Event)
{
    jclass       EvnC; 
    jmethodID    EvnM;
    jobjectArray Values = NULL;

    // get the tError class
    EvnC = getPvClass(env,"tLinkEvent");
    // get its "values" method
    EvnM = env->GetStaticMethodID(EvnC,"values","()[Lprosilica/Pv$tLinkEvent;");
    // call the method to get the array of possible value for the enumerate
    Values = (jobjectArray)env->CallStaticObjectMethod(EvnC,EvnM);
    // use the array of tError enumerate to return the proper code
    return env->GetObjectArrayElement(Values,((jint)Event) - 1);    
}

jobject ConvertDataType(JNIEnv* env,tPvDatatype Type)
{
    jclass       EvnC; 
    jmethodID    EvnM;
    jobjectArray Values = NULL;

    // get the tError class
    EvnC = getPvClass(env,"tDatatype");
    // get its "values" method
    EvnM = env->GetStaticMethodID(EvnC,"values","()[Lprosilica/Pv$tDatatype;");
    // call the method to get the array of possible value for the enumerate
    Values = (jobjectArray)env->CallStaticObjectMethod(EvnC,EvnM);
    // use the array of tError enumerate to return the proper code
    return env->GetObjectArrayElement(Values,(jint)Type); 
}

jobject ConvertImageFormat(JNIEnv* env,tPvImageFormat Format)
{
    jclass       EvnC; 
    jmethodID    EvnM;
    jobjectArray Values = NULL;

    // get the tError class
    EvnC = getPvClass(env,"tImageFormat");
    // get its "values" method
    EvnM = env->GetStaticMethodID(EvnC,"values","()[Lprosilica/Pv$tImageFormat;");
    // call the method to get the array of possible value for the enumerate
    Values = (jobjectArray)env->CallStaticObjectMethod(EvnC,EvnM);
    // use the array of tError enumerate to return the proper code
    return env->GetObjectArrayElement(Values,((jint)Format)); 
}

tPvImageFormat InvertImageFormat(JNIEnv* env,jobject Format)
{
    jclass       EvnC; 
    jmethodID    EvnM;
    jobjectArray Values = NULL;
    jsize        Count;
    jint         i;

    // get the tError class
    EvnC = getPvClass(env,"tImageFormat");
    // get its "values" method
    EvnM = env->GetStaticMethodID(EvnC,"values","()[Lprosilica/Pv$tImageFormat;");
    // call the method to get the array of possible value for the enumerate
    Values = (jobjectArray)env->CallStaticObjectMethod(EvnC,EvnM);
    //
    Count = env->GetArrayLength(Values);
    //
    for(i=0;i<Count;i++)
        if(env->IsSameObject(env->GetObjectArrayElement(Values,i),Format))
            break;
    
    if(i<Count)
        return (tPvImageFormat)(ePvFmtMono8 + i);
    else
        return ePvFmtMono8;
}

jobject ConvertBayerPattern(JNIEnv* env,tPvBayerPattern Pattern)
{
    jclass       EvnC; 
    jmethodID    EvnM;
    jobjectArray Values = NULL;

    // get the tError class
    EvnC = getPvClass(env,"tBayerPattern");
    // get its "values" method
    EvnM = env->GetStaticMethodID(EvnC,"values","()[Lprosilica/Pv$tBayerPattern;");
    // call the method to get the array of possible value for the enumerate
    Values = (jobjectArray)env->CallStaticObjectMethod(EvnC,EvnM);
    // use the array of tError enumerate to return the proper code
    return env->GetObjectArrayElement(Values,(jint)Pattern); 
}

tPvBayerPattern InvertBayerPattern(JNIEnv* env,jobject Pattern)
{
    jclass       EvnC; 
    jmethodID    EvnM;
    jobjectArray Values = NULL;
    jsize        Count;
    jint         i;

    // get the tError class
    EvnC = getPvClass(env,"tBayerPattern");
    // get its "values" method
    EvnM = env->GetStaticMethodID(EvnC,"values","()[Lprosilica/Pv$tBayerPattern;");
    // call the method to get the array of possible value for the enumerate
    Values = (jobjectArray)env->CallStaticObjectMethod(EvnC,EvnM);
    //
    Count = env->GetArrayLength(Values);
    //
    for(i=0;i<Count;i++)
        if(env->IsSameObject(env->GetObjectArrayElement(Values,i),Pattern))
            break;
    
    if(i<Count)
        return (tPvBayerPattern)(ePvBayerRGGB + i);
    else
        return ePvBayerRGGB;
}

// build an object of type tCameraInfo
jobject BuildtCameraInfo(JNIEnv* env)
{
    jclass       Class; 
    jmethodID    Method;

    // get the tError class
    Class = getPvClass(env,"tCameraInfo");
    // get its constructor method
    Method = env->GetMethodID(Class,"<init>","()V");
    // create the new object
    return env->NewObject(Class,Method);
}

// build an object of type tCameraInfoEx
jobject BuildtCameraInfoEx(JNIEnv* env)
{
    jclass       Class; 
    jmethodID    Method;

    // get the tError class
    Class = getPvClass(env,"tCameraInfoEx");
    // get its constructor method
    Method = env->GetMethodID(Class,"<init>","()V");
    // create the new object
    return env->NewObject(Class,Method);
}

void Copy2tCameraInfo(JNIEnv* env,jobject Item,const tPvCameraInfo& Info)
{
    jclass   Class;
    jfieldID FUniqueId,FSerStr,FPNum,FPVer,FPAccess,FInfId,FNameStr; 

    // get the object's class
    Class = env->GetObjectClass(Item);
    // get the ID of the fields
    FUniqueId = env->GetFieldID(Class,"UniqueId","J");
    FSerStr   = env->GetFieldID(Class,"SerialString","Ljava/lang/String;");
    FPNum     = env->GetFieldID(Class,"PartNumber","J");
    FPVer     = env->GetFieldID(Class,"PartVersion","C");
    FPAccess  = env->GetFieldID(Class,"PermittedAccess","J");
    FInfId    = env->GetFieldID(Class,"InterfaceId","J");
    FNameStr  = env->GetFieldID(Class,"DisplayName","Ljava/lang/String;");

    // set the field values
    env->SetLongField(Item,FUniqueId,(jlong)Info.UniqueId);
    env->SetObjectField(Item,FSerStr,env->NewStringUTF(Info.SerialString));
    env->SetLongField(Item,FPNum,(jlong)Info.PartNumber);
    env->SetCharField(Item,FPVer,L'A' + (Info.PartVersion - 'A'));
    env->SetLongField(Item,FPAccess,(jlong)Info.PermittedAccess);
    env->SetLongField(Item,FInfId,(jlong)Info.InterfaceId);
    env->SetObjectField(Item,FNameStr,env->NewStringUTF(Info.DisplayName));
}

void Copy2tCameraInfoEx(JNIEnv* env,jobject Item,const tPvCameraInfoEx& Info)
{
    jclass   Class;
    jfieldID Field;

    // get the object's class
    Class = env->GetObjectClass(Item);
    // get the ID of the fields
    Field = env->GetFieldID(Class,"UniqueId","J");
    env->SetLongField(Item,Field,(jlong)Info.UniqueId);
    Field  = env->GetFieldID(Class,"CameraName","Ljava/lang/String;");
    env->SetObjectField(Item,Field,env->NewStringUTF(Info.CameraName));
    Field  = env->GetFieldID(Class,"ModelName","Ljava/lang/String;");
    env->SetObjectField(Item,Field,env->NewStringUTF(Info.ModelName));
    Field  = env->GetFieldID(Class,"PartNumber","Ljava/lang/String;");
    env->SetObjectField(Item,Field,env->NewStringUTF(Info.PartNumber));
    Field  = env->GetFieldID(Class,"SerialNumber","Ljava/lang/String;");
    env->SetObjectField(Item,Field,env->NewStringUTF(Info.SerialNumber));
    Field  = env->GetFieldID(Class,"FirmwareVersion","Ljava/lang/String;");
    env->SetObjectField(Item,Field,env->NewStringUTF(Info.FirmwareVersion));
    Field    = env->GetFieldID(Class,"PermittedAccess","J");
    env->SetLongField(Item,Field,(jlong)Info.PermittedAccess);
    Field    = env->GetFieldID(Class,"InterfaceId","J");
    env->SetLongField(Item,Field,(jlong)Info.InterfaceId);
 
}

void Copy2tAttributeInfo(JNIEnv* env,jobject Item,const tPvAttributeInfo& Info)
{
    jclass   Class;
    jfieldID FType,FFlags,FCategory,FImpact;

    // get the object's class
    Class = env->GetObjectClass(Item);
    // get the ID of the fields
    FType       = env->GetFieldID(Class,"Datatype","Lprosilica/Pv$tDatatype;");
    FFlags      = env->GetFieldID(Class,"Flags","I");
    FCategory   = env->GetFieldID(Class,"Category","Ljava/lang/String;");
    FImpact     = env->GetFieldID(Class,"Impact","Ljava/lang/String;");

    if(FType && FFlags && FCategory && FImpact)
    {
        env->SetObjectField(Item,FType,ConvertDataType(env,Info.Datatype));
        env->SetIntField(Item,FFlags,Info.Flags);
        env->SetObjectField(Item,FCategory,env->NewStringUTF(Info.Category));
        env->SetObjectField(Item,FImpact,env->NewStringUTF(Info.Impact));
    }
}

void Copy2tFrame(JNIEnv* env,jobject Frame,const tPvFrame* pFrame)
{
    jclass   Class;
    jfieldID Field;

    // get the object's class
    Class = env->GetObjectClass(Frame);
    // set the frame status
    Field = env->GetFieldID(Class,"Status","Lprosilica/Pv$tError;");
    env->SetObjectField(Frame,Field,ConvertError(env,pFrame->Status));
    // set the image size
    Field = env->GetFieldID(Class,"ImageSize","J");
    env->SetLongField(Frame,Field,(jlong)pFrame->ImageSize);
    // set the image width
    Field = env->GetFieldID(Class,"Width","J");
    env->SetLongField(Frame,Field,(jlong)pFrame->Width);
    // set the image height
    Field = env->GetFieldID(Class,"Height","J");
    env->SetLongField(Frame,Field,(jlong)pFrame->Height);
    // set the image region X&Y
    Field = env->GetFieldID(Class,"RegionX","J");
    env->SetLongField(Frame,Field,(jlong)pFrame->RegionX);
    Field = env->GetFieldID(Class,"RegionY","J");
    env->SetLongField(Frame,Field,(jlong)pFrame->RegionY);
    // set the image format
    Field = env->GetFieldID(Class,"Format","Lprosilica/Pv$tImageFormat;");
    env->SetObjectField(Frame,Field,ConvertImageFormat(env,pFrame->Format));
    // set the bithdepth
    Field = env->GetFieldID(Class,"BitDepth","I");
    env->SetIntField(Frame,Field,(jint)pFrame->BitDepth);
    // set the bayer pattern
    Field = env->GetFieldID(Class,"BayerPattern","Lprosilica/Pv$tBayerPattern;");
    env->SetObjectField(Frame,Field,ConvertBayerPattern(env,pFrame->BayerPattern));
    // set the frame count
    Field = env->GetFieldID(Class,"FrameCount","J");
    env->SetLongField(Frame,Field,(jlong)pFrame->FrameCount);
    // set the timestamp
    Field = env->GetFieldID(Class,"TimestampLo","J");
    env->SetLongField(Frame,Field,(jlong)pFrame->TimestampLo);
    Field = env->GetFieldID(Class,"TimestampHi","J");
    env->SetLongField(Frame,Field,(jlong)pFrame->TimestampHi);
}

void Copy2tIpSettings(JNIEnv* env,jobject Object,const tPvIpSettings& Info)
{
    jclass      Class;
    jfieldID    Field; 
    jbyteArray  Bytes;

    // get the object's class
    Class = env->GetObjectClass(Object);
    // fill each fields
    Field = env->GetFieldID(Class,"ConfigMode","I");
    env->SetIntField(Object,Field,(jint)Info.ConfigMode);
    //
    Field = env->GetFieldID(Class,"ConfigModeSupport","I");
    env->SetIntField(Object,Field,(jint)Info.ConfigModeSupport);
    // current IP address
    Field = env->GetFieldID(Class,"CurrentIpAddress","[B");
    Bytes = (jbyteArray)env->GetObjectField(Object,Field);
    if(Bytes)
    {
        jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

        if(env->GetArrayLength(Bytes) == 4)
            memcpy(Array,&Info.CurrentIpAddress,sizeof(jbyte) * 4);

        env->ReleaseByteArrayElements(Bytes,Array,0);
    }
    else
    {
        Bytes = env->NewByteArray(4);
        if(Bytes)
        {
            jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

            if(env->GetArrayLength(Bytes) == 4)
                memcpy(Array,&Info.CurrentIpAddress,sizeof(jbyte) * 4);

            env->ReleaseByteArrayElements(Bytes,Array,0);
            env->SetObjectField(Object,Field,Bytes);
        }
    }
    // current IP subnet
    Field = env->GetFieldID(Class,"CurrentIpSubnet","[B");
    Bytes = (jbyteArray)env->GetObjectField(Object,Field);
    if(Bytes)
    {
        jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

        if(env->GetArrayLength(Bytes) == 4)
            memcpy(Array,&Info.CurrentIpSubnet,sizeof(jbyte) * 4);

        env->ReleaseByteArrayElements(Bytes,Array,0);
    }
    else
    {
        Bytes = env->NewByteArray(4);
        if(Bytes)
        {
            jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

            if(env->GetArrayLength(Bytes) == 4)
                memcpy(Array,&Info.CurrentIpSubnet,sizeof(jbyte) * 4);

            env->ReleaseByteArrayElements(Bytes,Array,0);
            env->SetObjectField(Object,Field,Bytes);
        }
    }
    // current IP gateway
    Field = env->GetFieldID(Class,"CurrentIpGateway","[B");
    Bytes = (jbyteArray)env->GetObjectField(Object,Field);
    if(Bytes)
    {
        jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

        if(env->GetArrayLength(Bytes) == 4)
            memcpy(Array,&Info.CurrentIpGateway,sizeof(jbyte) * 4);

        env->ReleaseByteArrayElements(Bytes,Array,0);
    }
    else
    {
        Bytes = env->NewByteArray(4);
        if(Bytes)
        {
            jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

            if(env->GetArrayLength(Bytes) == 4)
                memcpy(Array,&Info.CurrentIpGateway,sizeof(jbyte) * 4);

            env->ReleaseByteArrayElements(Bytes,Array,0);
            env->SetObjectField(Object,Field,Bytes);
        }
    }
    // persistent IP address
    Field = env->GetFieldID(Class,"PersistentIpAddr","[B");
    Bytes = (jbyteArray)env->GetObjectField(Object,Field);
    if(Bytes)
    {
        jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

        if(env->GetArrayLength(Bytes) == 4)
            memcpy(Array,&Info.PersistentIpAddr,sizeof(jbyte) * 4);

        env->ReleaseByteArrayElements(Bytes,Array,0);
    }
    else
    {
        Bytes = env->NewByteArray(4);
        if(Bytes)
        {
            jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

            if(env->GetArrayLength(Bytes) == 4)
                memcpy(Array,&Info.PersistentIpAddr,sizeof(jbyte) * 4);

            env->ReleaseByteArrayElements(Bytes,Array,0);
            env->SetObjectField(Object,Field,Bytes);
        }
    }
    // persistent IP subnet
    Field = env->GetFieldID(Class,"PersistentIpSubnet","[B");
    Bytes = (jbyteArray)env->GetObjectField(Object,Field);
    if(Bytes)
    {
        jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

        if(env->GetArrayLength(Bytes) == 4)
            memcpy(Array,&Info.PersistentIpSubnet,sizeof(jbyte) * 4);

        env->ReleaseByteArrayElements(Bytes,Array,0);
    }
    else
    {
        Bytes = env->NewByteArray(4);
        if(Bytes)
        {
            jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

            if(env->GetArrayLength(Bytes) == 4)
                memcpy(Array,&Info.PersistentIpSubnet,sizeof(jbyte) * 4);

            env->ReleaseByteArrayElements(Bytes,Array,0);
            env->SetObjectField(Object,Field,Bytes);
        }
    }
    // persistent IP gateway
    Field = env->GetFieldID(Class,"PersistentIpGateway","[B");
    Bytes = (jbyteArray)env->GetObjectField(Object,Field);
    if(Bytes)
    {
        jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

        if(env->GetArrayLength(Bytes) == 4)
            memcpy(Array,&Info.PersistentIpGateway,sizeof(jbyte) * 4);

        env->ReleaseByteArrayElements(Bytes,Array,0);
    }
    else
    {
        Bytes = env->NewByteArray(4);
        if(Bytes)
        {
            jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

            if(env->GetArrayLength(Bytes) == 4)
                memcpy(Array,&Info.PersistentIpGateway,sizeof(jbyte) * 4);

            env->ReleaseByteArrayElements(Bytes,Array,0);
            env->SetObjectField(Object,Field,Bytes);
        }
    }
}

void Copy2tPvIpSettings(JNIEnv* env,jobject Object,tPvIpSettings& Info)
{
    jclass      Class;
    jfieldID    Field; 
    jbyteArray  Bytes;

    // get the object's class
    Class = env->GetObjectClass(Object);
    // fill each fields
    Field = env->GetFieldID(Class,"ConfigMode","I");
    Info.ConfigMode = (tPvIpConfig)env->GetIntField(Object,Field);
    // current IP address
    Field = env->GetFieldID(Class,"CurrentIpAddress","[B");
    Bytes = (jbyteArray)env->GetObjectField(Object,Field);
    if(Bytes)
    {
        jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

        if(env->GetArrayLength(Bytes) == 4)
            memcpy(&Info.CurrentIpAddress,Array,sizeof(jbyte) * 4);

        env->ReleaseByteArrayElements(Bytes,Array,0);
    }
    else
        Info.CurrentIpAddress = 0;
    // current IP subnet
    Field = env->GetFieldID(Class,"CurrentIpSubnet","[B");
    Bytes = (jbyteArray)env->GetObjectField(Object,Field);
    if(Bytes)
    {
        jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

        if(env->GetArrayLength(Bytes) == 4)
            memcpy(&Info.CurrentIpSubnet,Array,sizeof(jbyte) * 4);

        env->ReleaseByteArrayElements(Bytes,Array,0);
    }
    else
        Info.CurrentIpSubnet = 0;
    // current IP gateway
    Field = env->GetFieldID(Class,"CurrentIpGateway","[B");
    Bytes = (jbyteArray)env->GetObjectField(Object,Field);
    if(Bytes)
    {
        jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

        if(env->GetArrayLength(Bytes) == 4)
            memcpy(&Info.CurrentIpGateway,Array,sizeof(jbyte) * 4);

        env->ReleaseByteArrayElements(Bytes,Array,0);
    }
    else
        Info.CurrentIpGateway = 0;
    // persistent IP address
    Field = env->GetFieldID(Class,"PersistentIpAddr","[B");
    Bytes = (jbyteArray)env->GetObjectField(Object,Field);
    if(Bytes)
    {
        jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

        if(env->GetArrayLength(Bytes) == 4)
            memcpy(&Info.PersistentIpAddr,Array,sizeof(jbyte) * 4);

        env->ReleaseByteArrayElements(Bytes,Array,0);
    }
    else
        Info.PersistentIpAddr = 0;
    // persistent IP subnet
    Field = env->GetFieldID(Class,"PersistentIpSubnet","[B");
    Bytes = (jbyteArray)env->GetObjectField(Object,Field);
    if(Bytes)
    {
        jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

        if(env->GetArrayLength(Bytes) == 4)
            memcpy(&Info.PersistentIpSubnet,Array,sizeof(jbyte) * 4);

        env->ReleaseByteArrayElements(Bytes,Array,0);
    }
    else
        Info.PersistentIpSubnet = 0;
    // persistent IP gateway
    Field = env->GetFieldID(Class,"PersistentIpGateway","[B");
    Bytes = (jbyteArray)env->GetObjectField(Object,Field);
    if(Bytes)
    {
        jbyte* Array = env->GetByteArrayElements(Bytes,JNI_FALSE);

        if(env->GetArrayLength(Bytes) == 4)
            memcpy(&Info.PersistentIpGateway,Array,sizeof(jbyte) * 4);

        env->ReleaseByteArrayElements(Bytes,Array,0);
    }
    else
        Info.PersistentIpGateway = 0;
}

void WaitForObject(JNIEnv* env,jobject Object)
{
    jclass    Class; 
    jmethodID Method;

    Class  = env->GetObjectClass(Object);
    Method = env->GetMethodID(Class,"wait","()V");
    if(Method)
        env->CallObjectMethod(Object,Method);  
}

void NotifyObject(JNIEnv* env,jobject Object)
{
    jclass    Class; 
    jmethodID Method;

    Class  = env->GetObjectClass(Object);
    Method = env->GetMethodID(Class,"notifyAll","()V");
    if(Method)
        env->CallObjectMethod(Object,Method);  
}

void Copy2tPvFrame(JNIEnv* env,jobject Frame,tPvFrame* pFrame)
{
    jclass   Class;
    jfieldID Field;

    // get the object's class
    Class = env->GetObjectClass(Frame);
    // get the frame status
    Field = env->GetFieldID(Class,"Status","Lprosilica/Pv$tError;");
    pFrame->Status = InvertError(env,env->GetObjectField(Frame,Field));
    // get the image size
    Field = env->GetFieldID(Class,"ImageSize","J");
    pFrame->ImageSize = env->GetLongField(Frame,Field);
    // get the image width
    Field = env->GetFieldID(Class,"Width","J");
    pFrame->Width = env->GetLongField(Frame,Field);
    // get the image height
    Field = env->GetFieldID(Class,"Height","J");
    pFrame->Height = env->GetLongField(Frame,Field);
    // get the image format
    Field = env->GetFieldID(Class,"Format","Lprosilica/Pv$tImageFormat;");
    pFrame->Format = InvertImageFormat(env,env->GetObjectField(Frame,Field));
    // get the bithdepth
    Field = env->GetFieldID(Class,"BitDepth","I");
    pFrame->BitDepth = env->GetIntField(Frame,Field);
    // get the bayer pattern
    Field = env->GetFieldID(Class,"BayerPattern","Lprosilica/Pv$tBayerPattern;");
    pFrame->BayerPattern = InvertBayerPattern(env,env->GetObjectField(Frame,Field));
}

// Get the tPvHandle cached in a Pv.tHandle object
tPvHandle GetPvHandle(JNIEnv* env,jobject Handle)
{
    jclass      Klass;
    jfieldID    Field;
    jlong       Value;
   
    // get the object's class
    Klass = env->GetObjectClass(Handle);
    // get the ID of the two fields were are interested in
    Field = env->GetFieldID(Klass,"Handle","J");
   
    if(Field)
    {
        Value = env->GetLongField(Handle,Field);
        return *(tPvHandle*)&Value;
    }
    else
        return 0;  
}

 char *GetStringNativeChars(JNIEnv* env,jstring jstr)
 {
    jclass      Klass;
    jmethodID   Method;    

    // get the object's class
    Klass   = env->GetObjectClass(jstr);
    // get the ID of the getBytes method
    Method  = env->GetMethodID(Klass,"getBytes","()[B");
    
    if(Method)
    {
        jbyteArray bytes = 0;
        jthrowable exc;
        char *result = 0;

        if (env->EnsureLocalCapacity(2) < 0)
            return 0; /* out of memory error */

        bytes = (jbyteArray)env->CallObjectMethod(jstr,Method);
        exc = env->ExceptionOccurred();
        if (!exc)
        {
             jint len = env->GetArrayLength(bytes);
             result = (char *)malloc(len + 1);
             if(result)
             {
                 env->GetByteArrayRegion(bytes, 0, len,(jbyte *)result);
                 result[len] = 0; /* NULL-terminate */
             }
        }
        else
            env->DeleteLocalRef(exc);

        env->DeleteLocalRef(bytes);

        return result;        
    }
    else
        return NULL;
 }

 // count the number of occurence of a character in the string
int strcnt(const char* String,char Char)
{
    int Count = 0;
    int i = 0;

    while(String[i] != '\0')
    {
        if(String[i] == Char)
            Count++;

        i++;
    }

    return Count;
}

// Internal callbacks

void _STDCALL InternalLinkCB(void* Context,tPvInterface Interface,tPvLinkEvent Event,unsigned long UniqueId)
{
    tCallbacks::iterator Cursor;
    jclass               Class; 
    jmethodID            Method;
    JNIEnv*              Env;
    jobject              Jvent;

    if(!gJavaVM->AttachCurrentThread((void **)&Env,NULL))
    {
        /*
        jobject Loader;
        
        // change the class loader for the thread
        Loader = getThreadContextClassLoader(Env);
        if(Loader)
            Env->NewGlobalRef(Loader);
        setThreadContextClassLoader(Env,gDefaultContextClassLoader);
        */
    
        // convert the event to a corresponding Java object
        Jvent = ConvertLinkEvent(Env,Event);

        // get the class of the callback object
        Class = getPvClass(Env,"LinkListener");
        // get the method to be called
        Method = Env->GetMethodID(Class,"onLinkEvent","(Lprosilica/Pv$tLinkEvent;J)V");

        // restrict access while we're registering
        Env->ExceptionClear();
        Env->MonitorEnter(Class);

        acquireLock();

        for(Cursor = gCallbacksList.begin();Cursor != gCallbacksList.end(); Cursor++)
        {
            Env->CallObjectMethod(*Cursor,Method,Jvent,(jlong)UniqueId);            
        }

        releaseLock();

        // un-restrict access while we're registering
        Env->MonitorExit(Class);
        
        /*
        // revert class loader
        if(Loader)
        {
            setThreadContextClassLoader(Env,Loader);
            Env->DeleteGlobalRef(Loader);
        }     
        */   

        gJavaVM->DetachCurrentThread();
    }
}

void _STDCALL InternalFrameCB(tPvFrame* pFrame)
{
    JNIEnv*    Env      = NULL;
    jobject    Frame    = (jobject)pFrame->Context[1];
    jbyteArray Buffer   = (jbyteArray)pFrame->Context[0];
    jobject    Callback = (jobject)pFrame->Context[2];
    
    if(!gJavaVM->AttachCurrentThread((void **)&Env,NULL))
    {    
        /*
        jobject Loader;
        
        // change the class loader for the thread
        Loader = getThreadContextClassLoader(Env);
        if(Loader)
            Env->NewGlobalRef(Loader);
        setThreadContextClassLoader(Env,gDefaultContextClassLoader);
        */

        acquireLock();
        
        // lock the frame object
        Env->MonitorEnter(Frame);
        // release the array of bytes
        //Env->ReleaseByteArrayElements(Buffer,(jbyte*)pFrame->ImageBuffer,0);
        // copy the frame details in the Java object
        Copy2tFrame(Env,Frame,pFrame);
        // then discard the frame           
        gFramesPool.push(pFrame); // should use the method
        // reset the internal pointer to the tPvFrame
        SetFrameInFrame(Env,Frame,NULL);
        
        // if a callback was specified, we need to call it now
        if(Callback)
        {
            jclass    Class; 
            jmethodID Method;

            Class  = Env->GetObjectClass(Callback);
            Method = Env->GetMethodID(Class,"onFrameEvent","(Lprosilica/Pv$tFrame;)V");
            if(Method)
                Env->CallObjectMethod(Callback,Method,Frame);     
        }
        
        // notify the object so that if there's a a call to CaptureWaitForFrameDone() it will unblock and continue
        NotifyObject(Env,Frame);
        // unlock the object
        Env->MonitorExit(Frame);

        // delete the references we were holding
        Env->DeleteGlobalRef(Buffer);
        Env->DeleteGlobalRef(Frame);
        if(Callback)
            Env->DeleteGlobalRef(Callback);
           
           /* 
        // revert class loader
        if(Loader)
        {
            setThreadContextClassLoader(Env,Loader);
            Env->DeleteGlobalRef(Loader);
        }
        */

        releaseLock();

        gJavaVM->DetachCurrentThread();
    }
}

// API function glue

// prosilica.pv.Version
JNIEXPORT void JNICALL Java_prosilica_Pv_Version(JNIEnv* env,jclass Class,jobject Version)
{
    jclass   Klass;
    jfieldID Field_1,Field_2;
    unsigned long Major,Minor;

    // get the object's class
    Klass = env->GetObjectClass(Version);
    // get the ID of the two fields were are interested in
    Field_1 = env->GetFieldID(Klass,"Major","I");
    Field_2 = env->GetFieldID(Klass,"Minor","I");

    if(Field_1 && Field_2)
    {
        PvVersion(&Major,&Minor);

        env->SetIntField(Version,Field_1,(jint)Major);
        env->SetIntField(Version,Field_1,(jint)Minor);
    }
}

// prosilica.pv.Initialize
JNIEXPORT jobject JNICALL Java_prosilica_Pv_Initialize(JNIEnv* env,jclass Class)
{
    tPvErr Err;

    initLock();

    env->ExceptionClear();
    env->MonitorEnter(Class);

    // keep the Java VM
    env->GetJavaVM(&gJavaVM);
    Err = PvInitialize();

    acquireDefaultContextClassLoader(env);
    
    env->MonitorExit(Class);

    return ConvertError(env,Err);
}

// prosilica.pv.InitializeNoDiscovery
JNIEXPORT jobject JNICALL Java_prosilica_Pv_InitializeNoDiscovery(JNIEnv* env,jclass Class)
{
    tPvErr Err;

    initLock();

    env->ExceptionClear();
    env->MonitorEnter(Class);

    // keep the Java VM
    env->GetJavaVM(&gJavaVM);
    Err = PvInitializeNoDiscovery();

    acquireDefaultContextClassLoader(env);
    
    env->MonitorExit(Class);

    return ConvertError(env,Err);
}

// prosilica.pv.UnInitialize
JNIEXPORT void JNICALL Java_prosilica_Pv_UnInitialize(JNIEnv* env,jclass Class)
{
    env->ExceptionClear();
    env->MonitorEnter(Class);

    if(gCBRegistered)
    {
        PvLinkCallbackUnRegister(InternalLinkCB,ePvLinkAdd);
        PvLinkCallbackUnRegister(InternalLinkCB,ePvLinkRemove);
        gCBRegistered = false;
    }

    releaseDefaultContextClassLoader(env);

    gJavaVM  = NULL;

    // call the API method
    PvUnInitialize();

    acquireLock();

    // delete all the frames that are still in the pool
    while(gFramesPool.size())
    {
        delete gFramesPool.front();
        gFramesPool.pop();
    }

    releaseLock();

    env->MonitorExit(Class);

    deleteLock();
}

// prosilica.pv.LinkCallbackRegister
JNIEXPORT jobject JNICALL Java_prosilica_Pv_LinkListenerRegister(JNIEnv* env,jclass Class,jobject Callback)
{
    tPvErr Err = ePvErrSuccess;

    // restrict access while we're registering
    env->ExceptionClear();
    env->MonitorEnter(Class);

    acquireLock();

    if(!gCBRegistered)
    {
        Err = PvLinkCallbackRegister(InternalLinkCB,ePvLinkAdd,NULL);
        if(!Err)
        {
            Err = PvLinkCallbackRegister(InternalLinkCB,ePvLinkRemove,NULL);
            if(!Err)
                gCBRegistered = true;
            else
                PvLinkCallbackUnRegister(InternalLinkCB,ePvLinkAdd);
        }
    }

    if(!Err)
    {
        jobject Object = env->NewGlobalRef(Callback);

        try 
        {
            // add the object to the list
            gCallbacksList.push_back(Object);

        } catch (...)
        {
            env->DeleteGlobalRef(Object);
            Err = ePvErrResources;
        }
    }

    releaseLock();

    // un-restrict access while we're registering
    env->MonitorExit(Class);

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.LinkCallbackUnRegister
JNIEXPORT jobject JNICALL Java_prosilica_Pv_LinkListenerUnRegister(JNIEnv* env,jclass Class,jobject Callback)
{
    tPvErr Err = ePvErrSuccess;

    // restrict access while we're un-registering
    env->ExceptionClear();
    env->MonitorEnter(Class);

    acquireLock();  

    if(gCBRegistered)
    {
        tPvErr Err = ePvErrSuccess;
        tCallbacks::iterator Cursor;

        for(Cursor = gCallbacksList.begin();Cursor != gCallbacksList.end(); Cursor++)
            if(env->IsSameObject(*Cursor,Callback))
                break;

        if(Cursor != gCallbacksList.end())
            gCallbacksList.erase(Cursor);
        else
            Err = ePvErrBadSequence;
    }

    releaseLock();

    // un-restrict access while we're registering
    env->MonitorExit(Class);

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}


// prosilica.pv.CameraList
JNIEXPORT jint JNICALL Java_prosilica_Pv_CameraList(JNIEnv* env,jclass Class,jobjectArray List,jint Length)
{
    tPvCameraInfo* pList = new tPvCameraInfo[Length];
    if(pList)
    {
        jobject Item;
        jint Found = (jint)PvCameraList(pList,Length,NULL);

        for(jint i=0;i<Found;i++)
        {
            // get the object
            Item = env->GetObjectArrayElement(List,i); 

            if(!Item)
            {
                Item = BuildtCameraInfo(env);
                if(Item)
                    env->SetObjectArrayElement(List,i,Item);
            }

            // copy the C structure in the corresponding Java object
            if(Item)
                Copy2tCameraInfo(env,Item,pList[i]);
        }

        delete [] pList;

        return Found;
    }
    else
        return 0;
}

// prosilica.pv.CameraListEx
JNIEXPORT jint JNICALL Java_prosilica_Pv_CameraListEx(JNIEnv* env,jclass Class,jobjectArray List,jint Length)
{
    tPvCameraInfoEx* pList = new tPvCameraInfoEx[Length];
    if(pList)
    {
        jobject Item;
        jint Found = (jint)PvCameraListEx(pList,Length,NULL,sizeof(tPvCameraInfoEx));

        for(jint i=0;i<Found;i++)
        {
            // get the object
            Item = env->GetObjectArrayElement(List,i); 

            if(!Item)
            {
                Item = BuildtCameraInfoEx(env);
                if(Item)
                    env->SetObjectArrayElement(List,i,Item);
            }

            // copy the C structure in the corresponding Java object
            if(Item)
                Copy2tCameraInfoEx(env,Item,pList[i]);
        }

        delete [] pList;

        return Found;
    }
    else
        return 0;
}


// prosilica.pv.CameraListUnreachable
JNIEXPORT jint JNICALL Java_prosilica_Pv_CameraListUnreachable(JNIEnv* env,jclass Class,jobjectArray List,jint Length)
{
    tPvCameraInfo* pList = new tPvCameraInfo[Length];
    if(pList)
    {
        jobject Item;
        jint Found = (jint)PvCameraListUnreachable(pList,Length,NULL);

        for(jint i=0;i<Found;i++)
        {
            // get the object
            Item = env->GetObjectArrayElement(List,i); 

            if(!Item)
            {
                Item = BuildtCameraInfo(env);
                if(Item)
                    env->SetObjectArrayElement(List,i,Item);
            }

            // copy the C structure in the corresponding Java object
            if(Item)
                Copy2tCameraInfo(env,Item,pList[i]);
        }

        delete [] pList;

        return Found;
    }
    else
        return 0;
}

// prosilica.pv.CameraListUnreachableEx
JNIEXPORT jint JNICALL Java_prosilica_Pv_CameraListUnreachableEx(JNIEnv* env,jclass Class,jobjectArray List,jint Length)
{
    tPvCameraInfoEx* pList = new tPvCameraInfoEx[Length];
    if(pList)
    {
        jobject Item;
        jint Found = (jint)PvCameraListUnreachableEx(pList,Length,NULL,sizeof(tPvCameraInfoEx));

        for(jint i=0;i<Found;i++)
        {
            // get the object
            Item = env->GetObjectArrayElement(List,i); 

            if(!Item)
            {
                Item = BuildtCameraInfoEx(env);
                if(Item)
                    env->SetObjectArrayElement(List,i,Item);
            }

            // copy the C structure in the corresponding Java object
            if(Item)
                Copy2tCameraInfoEx(env,Item,pList[i]);
        }

        delete [] pList;

        return Found;
    }
    else
        return 0;
}

// prosilica.pv.CameraCount
JNIEXPORT jint JNICALL Java_prosilica_Pv_CameraCount(JNIEnv* env,jclass Class)
{
    return PvCameraCount();
}

// prosilica.pv.CameraInfo
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CameraInfo(JNIEnv* env,jclass Class,jlong UniqueId,jobject CamInfo)
{
    tPvCameraInfo Info;
    tPvErr        Err;

    // call the corresponding API function
    Err = PvCameraInfo((unsigned long)UniqueId,&Info);

    // copy the data in the tCameraInfo object
    if(!Err)
        Copy2tCameraInfo(env,CamInfo,Info);

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CameraInfoEx
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CameraInfoEx(JNIEnv* env,jclass Class,jlong UniqueId,jobject CamInfo)
{
    tPvCameraInfoEx Info;
    tPvErr        Err;

    // call the corresponding API function
    Err = PvCameraInfoEx((unsigned long)UniqueId,&Info,sizeof(tPvCameraInfoEx));

    // copy the data in the tCameraInfo object
    if(!Err)
        Copy2tCameraInfoEx(env,CamInfo,Info);

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CameraInfo
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CameraInfoByAddr(JNIEnv* env,jclass Class,jbyteArray Address,jobject CamInfo)
{
    jbyte*          Bytes;
    tPvCameraInfo   Info;
    tPvErr          Err;

    // grab the array of jbytes
    Bytes = env->GetByteArrayElements(Address,NULL);

    // call the corresponding API function
    Err = PvCameraInfoByAddr(*(unsigned long*)Bytes,&Info,NULL);
    // copy the data in the tCameraInfo object
    if(!Err)
        Copy2tCameraInfo(env,CamInfo,Info);

    // release the array of jbytes
    env->ReleaseByteArrayElements(Address,Bytes,0);

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CameraInfoByAddrEx
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CameraInfoByAddrEx(JNIEnv* env,jclass Class,jbyteArray Address,jobject CamInfo)
{
    jbyte*          Bytes;
    tPvCameraInfoEx Info;
    tPvErr          Err;

    // grab the array of jbytes
    Bytes = env->GetByteArrayElements(Address,NULL);

    // call the corresponding API function
    Err = PvCameraInfoByAddrEx(*(unsigned long*)Bytes,&Info,NULL,sizeof(tPvCameraInfoEx));
    // copy the data in the tCameraInfo object
    if(!Err)
        Copy2tCameraInfoEx(env,CamInfo,Info);

    // release the array of jbytes
    env->ReleaseByteArrayElements(Address,Bytes,0);

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CameraIpSettingsGet
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CameraIpSettingsGet(JNIEnv* env,jclass Class,jlong UniqueId,jobject IPInfo)
{
    tPvIpSettings   Info;
    tPvErr          Err;

    Err = PvCameraIpSettingsGet((unsigned long)UniqueId,&Info);
    if(!Err)
        Copy2tIpSettings(env,IPInfo,Info);
    
    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CameraIpSettingsChange
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CameraIpSettingsChange(JNIEnv* env,jclass Class,jlong UniqueId,jobject IPInfo)
{
    tPvIpSettings   Info;
    tPvErr          Err;

    Copy2tPvIpSettings(env,IPInfo,Info);

    Err = PvCameraIpSettingsChange((unsigned long)UniqueId,&Info);
    
    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}


// prosilica.pv.CameraOpen
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CameraOpen(JNIEnv* env,jclass Class,jlong UniqueId,jint AccessFlag,jobject Handle)
{
    tPvErr      Err;
    tPvHandle   Camera;
    jclass      Klass;
    jfieldID    Field;
   
    // get the object's class
    Klass = env->GetObjectClass(Handle);
    // get the ID of the two fields were are interested in
    Field = env->GetFieldID(Klass,"Handle","J");
   
    if(Field)
    {
        Err = PvCameraOpen((unsigned long)UniqueId,(tPvAccessFlags)AccessFlag,&Camera);
        if(!Err)
            env->SetLongField(Handle,Field,*(jlong*)&Camera);
        else
            env->SetLongField(Handle,Field,0);
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CameraOpenByAddr
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CameraOpenByAddr(JNIEnv* env,jclass Class,jbyteArray Address,jint AccessFlag,jobject Handle)
{
    tPvErr      Err;
    tPvHandle   Camera;
    jclass      Klass;
    jfieldID    Field;
   
    // get the object's class
    Klass = env->GetObjectClass(Handle);
    // get the ID of the two fields were are interested in
    Field = env->GetFieldID(Klass,"Handle","J");
   
    if(Field)
    {
        // grab the array of jbytes
        jbyte* Bytes = env->GetByteArrayElements(Address,NULL);

        Err = PvCameraOpenByAddr(*(unsigned long*)Bytes,(tPvAccessFlags)AccessFlag,&Camera);
        if(!Err)
            env->SetLongField(Handle,Field,*(jlong*)&Camera);
        else
            env->SetLongField(Handle,Field,0);

        // release the array of jbytes
        env->ReleaseByteArrayElements(Address,Bytes,0);
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CameraClose
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CameraClose(JNIEnv* env,jclass Class,jobject Handle)
{
    tPvErr      Err;
    jclass      Klass;
    jfieldID    Field;
    jlong       Value;
   
    // get the object's class
    Klass = env->GetObjectClass(Handle);
    // get the ID of the two fields were are interested in
    Field = env->GetFieldID(Klass,"Handle","J");
   
    if(Field)
    {
        Value = env->GetLongField(Handle,Field);

        Err = PvCameraClose(*(tPvHandle*)&Value);
      
        if(!Err)
            env->SetLongField(Handle,Field,0);
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrList
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrList(JNIEnv* env,jclass Class,jobject Handle,jobject List)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        tPvAttrListPtr Array;
        unsigned long Length;

        Err = PvAttrList(Camera,&Array,&Length);
        if(!Err)
        {
            jobjectArray list;

            // allocate an array of string object
            list = (jobjectArray)env->NewObjectArray(Length,env->FindClass("java/lang/String"),env->NewStringUTF(""));
            if(list)
            {
                jobject string;

                // loop over all the label from the PvAPI array, and create a corresponding string object
                for(unsigned long i=0;i<Length;i++)
                {
                    string = env->NewStringUTF(Array[i]);
                    if(!string)
                    {
                        Err = ePvErrResources;
                        break;
                    }
                    else
                        env->SetObjectArrayElement(list,i,string);
                }

                if(!Err)
                {
                    jclass      Klass;
                    jfieldID    Field1,Field2;
                   
                    // get the object's class
                    Klass = env->GetObjectClass(List);
                    // get the ID of the two fields were are interested in
                    Field1 = env->GetFieldID(Klass,"Array","[Ljava/lang/String;");
                    Field2 = env->GetFieldID(Klass,"Count","I");
                   
                    if(Field1 && Field2)
                    {
                        env->SetObjectField(List,Field1,list);
                        env->SetIntField(List,Field2,(jint)Length);
                    }
                    else
                        Err = ePvErrBadParameter;
                }
            }
            else
                Err = ePvErrResources;
        }
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}


// prosilica.pv.AttrInfo
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrInfo(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jobject Info)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        tPvAttributeInfo PvInfo;
        char* Name;

        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            // call the API function
            Err = PvAttrInfo(Camera,Name,&PvInfo);

            if(!Err)
                Copy2tAttributeInfo(env,Info,PvInfo);

            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrExists
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrExists(JNIEnv* env,jclass Class,jobject Handle,jstring Label)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;

        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            // call the API function
            Err = PvAttrExists(Camera,Name);

            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrIsAvailable
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrIsAvailable(JNIEnv* env,jclass Class,jobject Handle,jstring Label)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;

        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            // call the API function
            Err = PvAttrIsAvailable(Camera,Name);

            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrIsValid
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrIsValid(JNIEnv* env,jclass Class,jobject Handle,jstring Label)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;

        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            // call the API function
            Err = PvAttrIsValid(Camera,Name);

            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrRangeEnum
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrRangeEnum(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jobject List)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;

        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            unsigned long Size = 256;
            char*         String = new char[Size];

            if(String)
            {
                Err = PvAttrRangeEnum(Camera,Name,String,Size,&Size);
                if(Err == ePvErrBadParameter)
                {
                    delete [] String;

                    String = new char[Size];
                    if(String)
                        Err = PvAttrRangeEnum(Camera,Name,String,Size,NULL);
                    else
                        Err = ePvErrResources;
                }   

                if(!Err)
                {
                    char* token;
                    jobjectArray list;
                    jsize Length = 0;

                    // count how many enumerate value there is
                    Length = strcnt(String,',') + 1;

                    // allocate an array of string object
                    list = (jobjectArray)env->NewObjectArray(Length,env->FindClass("java/lang/String"),env->NewStringUTF(""));
                    if(list)
                    {
                        int i = 0;
                        jobject string;

                        // restrict access while we're using strtok (which isn't thread safe)
                        env->ExceptionClear();
                        env->MonitorEnter(Class);

                        acquireLock();

                        // start the tokenization
                        token = strtok(String,","); 
                        // loop while there's token and add each to the supplied list
                        while(token)
                        {
                            string = env->NewStringUTF(token);
                            if(!string)
                            {
                                Err = ePvErrResources;
                                break;
                            }
                            else
                                env->SetObjectArrayElement(list,i++,string);                           
                            

                            token = strtok(NULL,",");
                        }

                        releaseLock();

                        env->MonitorExit(Class);
                    }

                    if(!Err)
                    {
                        jclass      Klass;
                        jfieldID    Field1,Field2;
                       
                        // get the object's class
                        Klass = env->GetObjectClass(List);
                        // get the ID of the two fields were are interested in
                        Field1 = env->GetFieldID(Klass,"Array","[Ljava/lang/String;");
                        Field2 = env->GetFieldID(Klass,"Count","I");
                       
                        if(Field1 && Field2)
                        {
                            env->SetObjectField(List,Field1,list);
                            env->SetIntField(List,Field2,(jint)Length);
                        }
                        else
                            Err = ePvErrBadParameter;
                    }
                }

                delete [] String;
            }
            else
                Err = ePvErrResources;

            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrRangeUint32
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrRangeUint32(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jobject Range)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;

        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            tPvUint32 Min,Max;

            // call the API function
            Err = PvAttrRangeUint32(Camera,Name,&Min,&Max);

            if(!Err)
            {
                jclass   Klass;
                jfieldID FMin,FMax;

                // get the object's class
                Klass = env->GetObjectClass(Range);
                // get the ID of the fields
                FMin = env->GetFieldID(Klass,"Min","J");
                FMax = env->GetFieldID(Klass,"Max","J");

                if(FMin && FMax)
                {
                    env->SetLongField(Range,FMin,(jlong)Min);  
                    env->SetLongField(Range,FMax,(jlong)Max); 
                }
            }

            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);   
}

// prosilica.pv.AttrRangeInt64
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrRangeInt64(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jobject Range)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;

        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            tPvInt64 Min,Max;

            // call the API function
            Err = PvAttrRangeInt64(Camera,Name,&Min,&Max);

            if(!Err)
            {
                jclass   Klass;
                jfieldID FMin,FMax;

                // get the object's class
                Klass = env->GetObjectClass(Range);
                // get the ID of the fields
                FMin = env->GetFieldID(Klass,"Min","J");
                FMax = env->GetFieldID(Klass,"Max","J");

                if(FMin && FMax)
                {
                    env->SetLongField(Range,FMin,(jlong)Min);  
                    env->SetLongField(Range,FMax,(jlong)Max); 
                }
            }

            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);   
}

// prosilica.pv.AttrRangeFloat32
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrRangeFloat32(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jobject Range)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;

        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            tPvFloat32 Min,Max;

            // call the API function
            Err = PvAttrRangeFloat32(Camera,Name,&Min,&Max);

            if(!Err)
            {
                jclass   Klass;
                jfieldID FMin,FMax;

                // get the object's class
                Klass = env->GetObjectClass(Range);
                // get the ID of the fields
                FMin = env->GetFieldID(Klass,"Min","F");
                FMax = env->GetFieldID(Klass,"Max","F");

                if(FMin && FMax)
                {
                    env->SetFloatField(Range,FMin,(jfloat)Min);  
                    env->SetFloatField(Range,FMax,(jfloat)Max); 
                }
            }

            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);   
}

// prosilica.pv.CommandRun
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CommandRun(JNIEnv* env,jclass Class,jobject Handle,jstring Label)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;

        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            // call the API function
            Err = PvCommandRun(Camera,Name);

            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrStringGet
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrStringGet(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jobject Value)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;

        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            unsigned long Length = 64;
            unsigned long Size;
            char* String;

            String = new char[Length];
            if(String)
            {
                Err = PvAttrStringGet(Camera,Name,String,Length,&Size);
                if(Err && Size > Length)
                {
                    delete [] String;
                    String = new char[Size];
                    if(String)
                        Err = PvAttrStringGet(Camera,Name,String,Size,NULL);        
                    else
                        Err = ePvErrResources;
                }
            }
            else
                Err = ePvErrResources;

            if(!Err)
            {
                jclass   Klass;
                jfieldID FValue;

                // get the object's class
                Klass = env->GetObjectClass(Value);
                // get the ID of the fields
                FValue = env->GetFieldID(Klass,"Value","Ljava/lang/String;");
                if(FValue)
                    env->SetObjectField(Value,FValue,env->NewStringUTF(String));  
                else
                    Err = ePvErrBadParameter;
            }

            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrStringGet
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrStringSet(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jstring Value)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;
      
        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            char* Data;

            // get the UTF8 value
            Data = GetStringNativeChars(env,Value);            

            if(Data)
            {
                Err = PvAttrStringSet(Camera,Name,Data);    

                free(Data);
            }
            else
                Err = ePvErrResources;

            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrEnumGet
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrEnumGet(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jobject Value)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;

        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            unsigned long Length = 64;
            unsigned long Size;
            char* String;

            String = new char[Length];
            if(String)
            {
                Err = PvAttrEnumGet(Camera,Name,String,Length,&Size);
                if(Err && Size > Length)
                {
                    delete [] String;
                    String = new char[Size];
                    if(String)
                        Err = PvAttrEnumGet(Camera,Name,String,Size,NULL);        
                    else
                        Err = ePvErrResources;
                }
            }
            else
                Err = ePvErrResources;

            if(!Err)
            {
                jclass   Klass;
                jfieldID FValue;

                // get the object's class
                Klass = env->GetObjectClass(Value);
                // get the ID of the fields
                FValue = env->GetFieldID(Klass,"Value","Ljava/lang/String;");
                if(FValue)
                    env->SetObjectField(Value,FValue,env->NewStringUTF(String));  
                else
                    Err = ePvErrBadParameter;
            }

           free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrEnumSet
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrEnumSet(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jstring Value)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;
      
        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {
            char* Data;

            // get the UTF8 value
            Data = GetStringNativeChars(env,Value);            

            if(Data)
            {
                Err = PvAttrEnumSet(Camera,Name,Data);    

                free(Data);
            }
            else
                Err = ePvErrResources;

            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrUint32Get
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrUint32Get(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jobject Value)
{
   tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;
      
        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {   
            tPvUint32 Val;

            Err = PvAttrUint32Get(Camera,Name,&Val);

            if(!Err)
            {
                jclass      Klass;
                jfieldID    Field;
               
                // get the object's class
                Klass = env->GetObjectClass(Value);
                // get the ID of the two fields were are interested in
                Field = env->GetFieldID(Klass,"Value","J");
               
                if(Field)
                    env->SetLongField(Value,Field,(jlong)Val);
            }
           
            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrUint32Set
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrUint32Set(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jlong Value)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;
      
        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {   
            Err = PvAttrUint32Set(Camera,Name,(tPvUint32)Value);
            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrInt64Get
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrInt64Get(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jobject Value)
{
   tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;
      
        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {   
            tPvInt64 Val;

            Err = PvAttrInt64Get(Camera,Name,&Val);

            if(!Err)
            {
                jclass      Klass;
                jfieldID    Field;
               
                // get the object's class
                Klass = env->GetObjectClass(Value);
                // get the ID of the two fields were are interested in
                Field = env->GetFieldID(Klass,"Value","J");
               
                if(Field)
                    env->SetLongField(Value,Field,(jlong)Val);
            }
           
            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrInt64Set
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrInt64Set(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jlong Value)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;
      
        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {   
            Err = PvAttrInt64Set(Camera,Name,(tPvInt64)Value);
            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrFloat32Get
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrFloat32Get(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jobject Value)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;
      
        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {   
            tPvFloat32 Val;

            Err = PvAttrFloat32Get(Camera,Name,&Val);

            if(!Err)
            {
                jclass      Klass;
                jfieldID    Field;
               
                // get the object's class
                Klass = env->GetObjectClass(Value);
                // get the ID of the two fields were are interested in
                Field = env->GetFieldID(Klass,"Value","F");
               
                if(Field)
                    env->SetFloatField(Value,Field,(jfloat)Val);
            }
           
            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrFloat32Set
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrFloat32Set(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jfloat Value)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;
      
        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {   
            Err = PvAttrFloat32Set(Camera,Name,(tPvFloat32)Value);
            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrBooleanGet
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrBooleanGet(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jobject Value)
{
   tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;
      
        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {   
            tPvBoolean Val;

            Err = PvAttrBooleanGet(Camera,Name,&Val);

            if(!Err)
            {
                jclass      Klass;
                jfieldID    Field;
               
                // get the object's class
                Klass = env->GetObjectClass(Value);
                // get the ID of the two fields were are interested in
                Field = env->GetFieldID(Klass,"Value","Z");
               
                if(Field)
                    env->SetBooleanField(Value,Field,(jboolean)Val);
            }
           
            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.AttrBooleanSet
JNIEXPORT jobject JNICALL Java_prosilica_Pv_AttrBooleanSet(JNIEnv* env,jclass Class,jobject Handle,jstring Label,jboolean Value)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        char* Name;
      
        // get the UTF8 name
        Name = GetStringNativeChars(env,Label);

        if(Name)
        {   
            Err = PvAttrBooleanSet(Camera,Name,(tPvBoolean)Value);
            free(Name);
        }
        else
            Err = ePvErrResources;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CaptureStart
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CaptureStart(JNIEnv* env,jclass Class,jobject Handle)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
        Err = PvCaptureStart(Camera);
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CaptureEnd
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CaptureEnd(JNIEnv* env,jclass Class,jobject Handle)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
        Err = PvCaptureEnd(Camera);
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CaptureEnd
JNIEXPORT jboolean JNICALL Java_prosilica_Pv_CaptureQuery(JNIEnv* env,jclass Class,jobject Handle)
{
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        unsigned long Started;

        if(!PvCaptureQuery(Camera,&Started))
            return Started ? true : false;
        else
            return false;
    }
    else
       return false;
}

// prosilica.pv.CaptureQueueFrame
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CaptureQueueFrame(JNIEnv* env,jclass Class,jobject Handle,jobject Frame,jobject Callback)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    env->MonitorEnter(Frame);
    
    if(Camera)
    {
        tPvFrame* pFrame = GetFrameInFrame(env,Frame);

        if(!pFrame)
        {
            pFrame = PopAFrame(env,Class);

            if(pFrame)
            {
                //jbyteArray Buffer; 
                jobject Buffer;
                    
                memset(pFrame,0,sizeof(tPvFrame));

                // get the buffer from the Java's frame
                if((Buffer = GetBufferFromFrame(env,Frame)))
                {
                    // keep reference to the byte buffer
                    pFrame->Context[0] = env->NewGlobalRef(Buffer);
                    /// keep references to the Java frame & callback
                    pFrame->Context[1] = env->NewGlobalRef(Frame);
                    if(Callback)
                        pFrame->Context[2] = env->NewGlobalRef(Callback);

                    // store the address of the frame in a field of the Java frame
                    SetFrameInFrame(env,Frame,pFrame);

                    // set the image buffer in the frame
                    //pFrame->ImageBuffer     = env->GetByteArrayElements((jbyteArray)pFrame->Context[0],JNI_FALSE);
                    //pFrame->ImageBufferSize = env->GetArrayLength((jbyteArray)pFrame->Context[0]);
                    pFrame->ImageBuffer = env->GetDirectBufferAddress((jobject)pFrame->Context[0]);
                    pFrame->ImageBufferSize = env->GetDirectBufferCapacity((jobject)pFrame->Context[0]);

                    Err = PvCaptureQueueFrame(Camera,pFrame,InternalFrameCB);

                    if(Err)
                    {
                        // release the array of bytes
                        //env->ReleaseByteArrayElements(Buffer,(jbyte*)pFrame->ImageBuffer,0);
                        // delete the reference we created
                        env->DeleteGlobalRef((jobject)pFrame->Context[0]);
                        env->DeleteGlobalRef((jobject)pFrame->Context[1]);   
                        if(Callback)
                            env->DeleteGlobalRef((jobject)pFrame->Context[2]);

                        PushAFrame(env,Class,pFrame);
                    }
                }
                else
                    Err = ePvErrBadParameter;
            }
            else
                Err = ePvErrResources;
        }
        else
            Err = ePvErrBadSequence;
    }
    else
        Err = ePvErrBadParameter;

    env->MonitorExit(Frame);

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CaptureWaitForFrameDone
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CaptureWaitForFrameDone(JNIEnv* env,jclass Class,jobject Handle,jobject Frame,jlong Timeout)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        tPvFrame* pFrame;

        // lock the fame object
        env->MonitorEnter(Frame);

        // get the frame object
        if((pFrame = GetFrameInFrame(env,Frame)))
        {
            // unlock the frame object before calling the API function
            env->MonitorExit(Frame);
            Err = PvCaptureWaitForFrameDone(Camera,pFrame,(unsigned long)Timeout);   
            // relock the frame object
            env->MonitorEnter(Frame);
            if(!Err)
            {
                // we need to wait for the internal CB to have executed (if necessary)
                if(GetFrameInFrame(env,Frame))
                    WaitForObject(env,Frame);
            }
        }
        else            
            Err = ePvErrSuccess; // frame might have been already "returned"

        // unlock the frame object
        env->MonitorExit(Frame);
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CaptureQueueClear
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CaptureQueueClear(JNIEnv* env,jclass Class,jobject Handle)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
        Err = PvCaptureQueueClear(Camera);
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.CaptureAdjustPacketSize
JNIEXPORT jobject JNICALL Java_prosilica_Pv_CaptureAdjustPacketSize(JNIEnv* env,jclass Class,jobject Handle,jlong Maximum)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
        Err = PvCaptureAdjustPacketSize(Camera,(unsigned long)Maximum);
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.RegisterRead
JNIEXPORT jobject JNICALL Java_prosilica_Pv_RegisterRead(JNIEnv* env,jclass Class,jobject Handle,jlong NumReads,jobject AddressArray,jobject DataArray,jobject NumComplete)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        if(env->GetArrayLength((jlongArray)AddressArray) >= NumReads && env->GetArrayLength((jlongArray)DataArray) >= NumReads)
        {
            unsigned long Completed;
            jlong*        pAddresses = env->GetLongArrayElements((jlongArray)AddressArray,JNI_FALSE);
            jlong*        pData      = env->GetLongArrayElements((jlongArray)DataArray,JNI_FALSE);

            if(pAddresses && pData)
            {
                Err = PvRegisterRead(Camera,NumReads,(const unsigned long*)pAddresses,(unsigned long*)pData,&Completed);
                if(!Err && NumComplete)
                {
                    jclass      Klass;
                    jfieldID    Field;
                   
                    // get the object's class
                    Klass = env->GetObjectClass(NumComplete);
                    // get the ID of the two fields were are interested in
                    Field = env->GetFieldID(Klass,"Value","J");
                   
                    if(Field)
                        env->SetLongField(NumComplete,Field,Completed); 
                }
            }
            else
                Err = ePvErrBadParameter;

            if(pAddresses)
                env->ReleaseLongArrayElements((jlongArray)AddressArray,pAddresses,JNI_FALSE);
            if(pData)
                env->ReleaseLongArrayElements((jlongArray)DataArray,pData,JNI_TRUE);
        }
        else
            Err = ePvErrBadParameter;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.RegisterWrite
JNIEXPORT jobject JNICALL Java_prosilica_Pv_RegisterWrite(JNIEnv* env,jclass Class,jobject Handle,jlong NumWrites,jobject AddressArray,jobject DataArray,jobject NumComplete)
{
    tPvErr    Err;
    tPvHandle Camera = GetPvHandle(env,Handle);

    if(Camera)
    {
        if(env->GetArrayLength((jlongArray)AddressArray) >= NumWrites && env->GetArrayLength((jlongArray)DataArray) >= NumWrites)
        {
            unsigned long Completed;
            jlong*        pAddresses = env->GetLongArrayElements((jlongArray)AddressArray,JNI_FALSE);
            jlong*        pData      = env->GetLongArrayElements((jlongArray)DataArray,JNI_FALSE);

            if(pAddresses && pData)
            {
                Err = PvRegisterWrite(Camera,NumWrites,(const unsigned long*)pAddresses,(unsigned long*)pData,&Completed);
                if(!Err && NumComplete)
                {
                    jclass      Klass;
                    jfieldID    Field;
                   
                    // get the object's class
                    Klass = env->GetObjectClass(NumComplete);
                    // get the ID of the two fields were are interested in
                    Field = env->GetFieldID(Klass,"Value","J");
                   
                    if(Field)
                        env->SetLongField(NumComplete,Field,Completed); 
                }
            }
            else
                Err = ePvErrBadParameter;

            if(pAddresses)
                env->ReleaseLongArrayElements((jlongArray)AddressArray,pAddresses,JNI_FALSE);
            if(pData)
                env->ReleaseLongArrayElements((jlongArray)DataArray,pData,JNI_FALSE);
        }
        else
            Err = ePvErrBadParameter;
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

// prosilica.pv.FrameToBGRBuffer
JNIEXPORT jobject JNICALL Java_prosilica_Pv_FrameToBGRBuffer(JNIEnv* env,jclass Class,jobject Frame,jobject Buffer)
{
    tPvErr Err = ePvErrSuccess;
    jobject Source;
    jobject Target = Buffer;

    // get the buffer from the Java's frame
    if((Source = GetBufferFromFrame(env,Frame)))
    {
        void* Src    = env->GetDirectBufferAddress(Source);
        void* Tgt    = env->GetDirectBufferAddress(Target);
        jsize SrcLen = env->GetDirectBufferCapacity(Source);
        jsize TgtLen = env->GetDirectBufferCapacity(Target); 

        if(Src && Tgt)
        {
            tPvFrame pFrame;

            // reconsitue a local frame structure
            Copy2tPvFrame(env,Frame,&pFrame);
            pFrame.ImageBuffer = Src;
            pFrame.ImageBufferSize = SrcLen;

            // is the target buffer big enough to fit the data (java BuffereBitmap = TYPE_3BYTE_BGR)
            if(pFrame.Width * pFrame.Height * 3 <= TgtLen)
            {
                // convert the frame into the provided RGB based buffer

                switch(pFrame.Format)
                {
                    case ePvFmtMono8:
                    {
                        unsigned char* pSrc = (unsigned char*)Src;
                        unsigned char* pTgt = (unsigned char*)Tgt;

		                for(unsigned long i=0;i<pFrame.ImageSize;i++)
                        {
		                    *(pTgt++) = pSrc[i];
		                    *(pTgt++) = pSrc[i];
		                    *(pTgt++) = pSrc[i];
		                }

                        break;
                    }
                    case ePvFmtMono16:
                    {
                        unsigned short* pSrc = (unsigned short*)Src;
                        unsigned long Count = pFrame.ImageSize / 2;
                        unsigned char Shift = pFrame.BitDepth - 8;
                        unsigned char Color;
                        unsigned char* pTgt = (unsigned char*)Tgt;

		                for(unsigned long i=0;i<Count;i++)
		                {
		                    Color = pSrc[i] >> Shift;
        				  
		                    *(pTgt++) = Color;
		                    *(pTgt++) = Color;
		                    *(pTgt++) = Color;
		                }

                        break;
                    }
                    case ePvFmtBayer8:
                    {
                        unsigned char* pTgt = (unsigned char*)Tgt;

                        PvUtilityColorInterpolate(&pFrame,&pTgt[2],&pTgt[1],&pTgt[0],2,0);

                        break;
                    }
                    case ePvFmtBayer16:
                    {
                        unsigned short* pSrc = (unsigned short*)Src;
                        unsigned char* pSrcS = (unsigned char*)Src;
                        unsigned long Count = pFrame.ImageSize / 2;
                        unsigned char Shift = pFrame.BitDepth - 8;
                        unsigned char* pTgt = (unsigned char*)Tgt;

                        for(unsigned long i=0;i<Count;i++)
                            pSrcS[i] = pSrc[i] >> Shift;

                        pFrame.Format = ePvFmtBayer8;

                        PvUtilityColorInterpolate(&pFrame,&pTgt[2],&pTgt[1],&pTgt[0],2,0);

                        break;
                    }
                    case ePvFmtRgb24:
                    {
                        unsigned char* pSrc = (unsigned char*)Src;
                        unsigned char* pTgt = (unsigned char*)Tgt;

		                for(unsigned long i=0;i<pFrame.ImageSize;i+=3)
                        {
		                    *(pTgt++) = pSrc[i+2];
		                    *(pTgt++) = pSrc[i+1];
		                    *(pTgt++) = pSrc[i];
		                }

                        break;
                    }
                    case ePvFmtBgr24:
                    {
                        unsigned char* pSrc = (unsigned char*)Src;
                        unsigned char* pTgt = (unsigned char*)Tgt;

                        memcpy(pTgt,pSrc,pFrame.ImageSize);

                        break;
                    }
                    case ePvFmtRgba32:
                    {
                        unsigned char* pSrc = (unsigned char*)Src;
                        unsigned char* pTgt = (unsigned char*)Tgt;

		                for(unsigned long i=0;i<pFrame.ImageSize;i+=4)
                        {
		                    *(pTgt++) = pSrc[i+2];
		                    *(pTgt++) = pSrc[i+1];
		                    *(pTgt++) = pSrc[i];
		                }

                        break;
                    }
                    case ePvFmtBgra32:
                    {
                        unsigned char* pSrc = (unsigned char*)Src;
                        unsigned char* pTgt = (unsigned char*)Tgt;

		                for(unsigned long i=0;i<pFrame.ImageSize;i+=4)
                        {
		                    *(pTgt++) = pSrc[i];
		                    *(pTgt++) = pSrc[i+1];
		                    *(pTgt++) = pSrc[i+2];
		                }

                        break;
                    }
                    case ePvFmtYuv411:
                    {
                        unsigned char* pSrc = (unsigned char*)Src;
                        unsigned char* pTgt = (unsigned char*)Tgt;                        
                        int y1,y2,y3,y4,u,v;
                        int r,g,b;

                        for(unsigned long i=0;i<pFrame.ImageSize;i+=6)
                        {
                            u  = pSrc[i];
                            y1 = pSrc[i+1];
                            y2 = pSrc[i+2];
                            v  = pSrc[i+3];
                            y3 = pSrc[i+4];
                            y4 = pSrc[i+5];

                            YUV2RGB(y1,u,v,r,g,b);
                            *(pTgt++) = (unsigned char)b;
			                *(pTgt++) = (unsigned char)g;
		                    *(pTgt++) = (unsigned char)r;
                            YUV2RGB(y2,u,v,r,g,b);
                            *(pTgt++) = (unsigned char)b;
			                *(pTgt++) = (unsigned char)g;
		                    *(pTgt++) = (unsigned char)r;
                            YUV2RGB(y3,u,v,r,g,b);
                            *(pTgt++) = (unsigned char)b;
			                *(pTgt++) = (unsigned char)g;
		                    *(pTgt++) = (unsigned char)r;
                            YUV2RGB(y4,u,v,r,g,b);
                            *(pTgt++) = (unsigned char)b;
			                *(pTgt++) = (unsigned char)g;
		                    *(pTgt++) = (unsigned char)r;
                        }

                        break;
                    }       
                    case ePvFmtYuv422:
                    {
                        unsigned char* pSrc = (unsigned char*)Src;
                        unsigned char* pTgt = (unsigned char*)Tgt;                        
                        int y1,y2,u,v;
                        int r,g,b;

                        for(unsigned long i=0;i<pFrame.ImageSize;i+=4)
                        {
                            u  = pSrc[i];
                            y1 = pSrc[i+1];
                            v  = pSrc[i+2];
                            y2 = pSrc[i+3];

                            YUV2RGB(y1,u,v,r,g,b);
                            *(pTgt++) = (unsigned char)b;
			                *(pTgt++) = (unsigned char)g;
		                    *(pTgt++) = (unsigned char)r;
                            YUV2RGB(y2,u,v,r,g,b);
                            *(pTgt++) = (unsigned char)b;
			                *(pTgt++) = (unsigned char)g;
		                    *(pTgt++) = (unsigned char)r;
                        }

                        break;
                    }
                    case ePvFmtYuv444:
                    {
                        unsigned char* pSrc = (unsigned char*)Src;
                        unsigned char* pTgt = (unsigned char*)Tgt;                        
                        int y1,y2,u,v;
                        int r,g,b;

                        for(unsigned long i=0;i<pFrame.ImageSize;i+=6)
                        {
                            u  = pSrc[i];
                            y1 = pSrc[i+1];
                            v  = pSrc[i+2];
                            y2 = pSrc[i+4];

                            YUV2RGB(y1,u,v,r,g,b);
                            *(pTgt++) = (unsigned char)b;
			                *(pTgt++) = (unsigned char)g;
		                    *(pTgt++) = (unsigned char)r;
                            YUV2RGB(y2,u,v,r,g,b);
                            *(pTgt++) = (unsigned char)b;
			                *(pTgt++) = (unsigned char)g;
		                    *(pTgt++) = (unsigned char)r;
                        }

                        break;
                    }
                    case ePvFmtMono12Packed:
                    {
		                const Packed12BitsPixel_t*  pSrc = (const Packed12BitsPixel_t*)Src;
                        const Packed12BitsPixel_t*  pSrcEnd = (const Packed12BitsPixel_t*)((unsigned char*)Src + pFrame.ImageSize);
                        unsigned char* pTgt     = (unsigned char*)Tgt;
                        unsigned char* pTgtEnd  = pTgt + TgtLen;
                        unsigned char  Shift    = pFrame.BitDepth - 8;
                        unsigned short pixel;

		                while (pSrc < pSrcEnd)
                        {
                            if(pTgt < pTgtEnd)
                            {
                                pixel = (unsigned short)pSrc->LByte << 4;
                                pixel += ((unsigned short)pSrc->MByte & 0xF0) >> 4;
                                pTgt[0] = pTgt[1] = pTgt[2] = pixel >> Shift;
                                pTgt += 3;
                                
                                if(pTgt < pTgtEnd)
                                {
                                    pixel = (unsigned short)pSrc->UByte << 4;
                                    pixel += ((unsigned short)pSrc->MByte & 0x0F) >> 4;
                                    pTgt[0] = pTgt[1] = pTgt[2] = pixel >> Shift;
                                    pTgt += 3;
                                }
                            }

                            pSrc++;
		                }

                        break;

                    }
                    case ePvFmtBayer12Packed:
                    {
		                const Packed12BitsPixel_t*  pSrc    = (const Packed12BitsPixel_t*)Src;
                        const Packed12BitsPixel_t*  pSrcEnd = (const Packed12BitsPixel_t*)((unsigned char*)Src + pFrame.ImageSize);
                        unsigned short              pixel1,pixel2;
                        unsigned char*              pDest   = (unsigned char*)Src;
                        unsigned char*              pDestEnd= pDest + pFrame.ImageBufferSize;
                        unsigned char               Shift   = pFrame.BitDepth - 8;

	                    while (pSrc < pSrcEnd && pDest < pDestEnd)
	                    {
                            for (unsigned long i = 0; i < pFrame.Width && pSrc < pSrcEnd; i+=2)
                            {
                                pixel1 = (unsigned short)pSrc->LByte << 4;
                                pixel1 += ((unsigned short)pSrc->MByte & 0xF0) >> 4;
                                
                                pixel2 = (unsigned short)pSrc->UByte << 4;
                                pixel2 += ((unsigned short)pSrc->MByte & 0x0F) >> 4;

                                if(pDest < pDestEnd)
                                {
                                    *(pDest++) = pixel1 >> Shift;
                                    if(pDest < pDestEnd)
                                        *(pDest++) = pixel2 >> Shift;
                                }

                                pSrc++;
                            }
	                    }

                        if(pDest < pDestEnd)
                        {
                            unsigned char* pTgt = (unsigned char*)Tgt;

                            pFrame.Format = ePvFmtBayer8;

                            PvUtilityColorInterpolate(&pFrame,&pTgt[2],&pTgt[1],&pTgt[0],2,0);
                        }

                        break;
                    }
                    case ePvFmtRgb48:
                    {
                        // deprecated format
                        break;
                    }
                    default:
                    {
                        Err = ePvErrBadParameter;
                        break;
                    }
                }
            }
            else
                Err = ePvErrBufferTooSmall;
        }
    }
    else
        Err = ePvErrBadParameter;

    // return a Pv.tError enumerate
    return ConvertError(env,Err);
}

#ifdef __cplusplus
}
#endif


