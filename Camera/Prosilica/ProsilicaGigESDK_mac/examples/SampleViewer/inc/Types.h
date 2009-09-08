/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         Types.h
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Define various basic types
|
| Notes:
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

#ifndef _TYPES
#define _TYPES

#include <stdlib.h>

//===== TYPE DEFINITIONS ======================================================

typedef void                tAny;
typedef void*               tHandle;
typedef char                tChar;
#ifdef _WINDOWS
typedef wchar_t             tWChar;
#endif
typedef bool                tBool;
typedef unsigned char       tByte;
typedef unsigned int        tErr;
typedef unsigned int        tEnum;
typedef unsigned int        tSize;
typedef unsigned int        tUID;

typedef char                tInt8;
typedef unsigned char       tUint8;
typedef short               tInt16;
typedef unsigned short      tUint16;
typedef int                 tInt32;
typedef unsigned int        tUint32;
#ifdef _WINDOWS
typedef __int64             tInt64;
typedef unsigned __int64    tUint64;
#elif defined(_LINUX) || defined(_QNX) || defined(_OSX)
typedef long long           tInt64;
typedef unsigned long long  tUint64;
#else
#error Define Int64 data types for this platform!
#endif 
typedef float               tFloat32;
typedef double              tFloat64;

#endif
