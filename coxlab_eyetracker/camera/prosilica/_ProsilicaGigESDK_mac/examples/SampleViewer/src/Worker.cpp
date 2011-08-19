/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         MainWindow.cpp
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Implement the main window class
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

#include <Worker.h>

//===== DEFINES ===============================================================

//===== CONSTANTS =============================================================

//===== LOCAL DATA ============================================================

// define the event
DEFINE_EVENT_TYPE(wxEVT_WORKER)

//===== CLASS DEFINITION ======================================================

//===== CLASS IMPLEMENTATION ==================================================

/*
 * Method:    CWorkerEvent()
 * Purpose:   constructor
 * Comments:  none
 */ 
CWorkerEvent::CWorkerEvent()
    : wxNotifyEvent(wxEVT_WORKER,0)
{
    iEvent  = 0;
    iData   = 0;
}

/*
 * Method:    CWorkerEvent()
 * Purpose:   constructor
 * Comments:  none
 */ 
CWorkerEvent::CWorkerEvent(tInt32 aId,tUint32 aEvent,tUint32 aData)
    : wxNotifyEvent(wxEVT_WORKER,aId)
{
    iEvent  = aEvent;
    iData   = aData;
}

/*
 * Method:    CWorkerEvent()
 * Purpose:   copy constructor
 * 
 * Comments:  none
 */ 
CWorkerEvent::CWorkerEvent(const CWorkerEvent& aEvent)
    : wxNotifyEvent(wxEVT_WORKER,aEvent.GetId())
{
    iEvent  = aEvent.iEvent;
    iData   = aEvent.iData;
}

/*
 * Method:    PWorker()
 * Purpose:   constructor
 * Comments:  none
 */ 
PWorker::PWorker(tInt32 aId,wxEvtHandler* aHandler)
    : wxThread(wxTHREAD_JOINABLE) , iId(aId), iHandler(aHandler)
{
}

/*
 * Method:    ~PWorker()
 * Purpose:   destructor
 * Comments:  none
 */        
PWorker::~PWorker()
{
}

/*
 * Method:    Start()
 * Purpose:   instruct the worker to start
 * Comments:  none
 */         
bool PWorker::Start()
{
    if(Create() == wxTHREAD_NO_ERROR)
    {
        Run();
        return true;
    }
    else
        return false;    
}

/*
 * Method:    NotifyHandler()
 * Purpose:   notify the handler of a given event
 * Comments:  none
 */ 
void PWorker::NotifyHandler(tUint32 aEvent,tUint32 aData /* = 0 */)
{
    if(iHandler)
    {
        CWorkerEvent lEvent(iId,aEvent,aData);
        lEvent.SetEventObject(NULL);
        //::wxPostEvent(iHandler,lEvent);    
        iHandler->AddPendingEvent(lEvent); 
    }
}

/* 
 * Method:    Entry()
 * Purpose:   thread entry method
 * Arguments: none
 * Return:    none
 * Comments:  do not derive, use OnRunning() instead
 */ 
PWorker::ExitCode PWorker::Entry()
{
    OnEntry();
    return (PWorker::ExitCode)OnRunning();
}


