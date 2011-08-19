/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         Tools.cpp
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Implement some useful functions
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

//===== INCLUDE FILES =========================================================

#include <PvApi.h>

//===== FUNCTION PROTOTYPES ===================================================

/*
 * Function:  GetStringForError()
 * Purpose:   convert a PvAPI error code into a "user friendly" string
 * Comments:  none
 */       
const char* GetStringForError(tPvErr aErr)
{   
    switch(aErr)
    {
        case ePvErrSuccess:
            return "No error";
        case ePvErrCameraFault:
            return "Unexpected camera fault";
        case ePvErrInternalFault:
            return "Unexpected fault in PvApi or driver";
        case ePvErrBadHandle:
            return "Camera handle is invalid";
        case ePvErrBadParameter:
            return "Bad parameter to API call";
        case ePvErrBadSequence:
            return "Sequence of API calls is incorrect";
        case ePvErrNotFound:
            return "Camera or attribute not found";
        case ePvErrAccessDenied:
            return "Camera cannot be opened in the specified mode";
        case ePvErrUnplugged:
            return "Camera was unplugged";
        case ePvErrInvalidSetup:
            return "Setup/Attribute is invalid";
        case ePvErrResources:
            return "System/network resources or memory not available";
        case ePvErrBandwidth:
            return "1394 bandwidth not available";
        case ePvErrQueueFull:
            return "Too many frames on queue";
        case ePvErrBufferTooSmall:
            return "Frame buffer is too small";
        case ePvErrCancelled:
            return "Frame cancelled by user";
        case ePvErrDataLost:
            return "The data for the frame was lost";
        case ePvErrDataMissing:
            return "Some data in the frame is missing";
        case ePvErrTimeout:
            return "Timeout during wait";
        case ePvErrOutOfRange:
            return "Attribute value is out of the expected range";
        case ePvErrWrongType:
            return "Attribute is not of this type";
        case ePvErrForbidden:
            return "Attribute write forbidden at this time";
        case ePvErrUnavailable:
            return "Attribute is not available at this time";
        default:
            return "";    
    }
}
