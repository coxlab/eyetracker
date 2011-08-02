/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         Seeker.cpp
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Implements the worker that seek a camera
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

#include <Seeker.h>
#include <PvApi.h>

//===== CLASS IMPLEMENTATION ==================================================

/*
 * Method:    CSeeker()
 * Purpose:   constructor
 * Comments:  none
 */ 
CSeeker::CSeeker(tInt32 aId,wxEvtHandler* aHandler,tUint32 aAddr)
    :PWorker(aId,aHandler) , iAddr(aAddr), iFound(false)
{
}

/*
 * Method:    ~CSeeker()
 * Purpose:   destructor
 * Comments:  none
 */        
CSeeker::~CSeeker()
{
}

/*
 * Method:    OnEntry()
 * Purpose:   called when the thread is starting
 * Comments:  none
 */ 
void CSeeker::OnEntry()
{
    NotifyHandler(kEvnSeekerStarted);
}

/*
 * Method:    OnExit()
 * Purpose:   called when the thread is terminating
 * Comments:  none
 */         
void CSeeker::OnExit()
{
    NotifyHandler(kEvnSeekerFinished,iFound);
}

/*
 * Method:    OnRunning()
 * Purpose:   called when the thread is running (body)
 * Comments:  none
 */ 
tUint32 CSeeker::OnRunning()
{
    tPvCameraInfo Info;
    tPvErr lErr;
                                                                     
    if((lErr = PvCameraInfoByAddr(iAddr,&Info,NULL)))
        iFound = false;
    else
        iFound = true;     
   
    return lErr;
}
