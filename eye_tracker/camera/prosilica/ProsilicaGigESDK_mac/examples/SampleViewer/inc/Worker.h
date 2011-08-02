/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         Worker.h
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Define the basic worker thread class
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

#include <wx/event.h>
#include <wx/thread.h>

#include <Types.h>

#ifndef EVT_WORKER

class CWorkerEvent;

extern const wxEventType wxEVT_WORKER;

typedef void (wxEvtHandler::*wxWorkerEventFunction)(CWorkerEvent&);

#define EVT_WORKER(id,fn) \
    DECLARE_EVENT_TABLE_ENTRY( wxEVT_WORKER, id, -1, \
    (wxObjectEventFunction) (wxEventFunction) (wxCommandEventFunction) (wxNotifyEventFunction) \
    wxStaticCastEvent( wxWorkerEventFunction, & fn ), (wxObject *) NULL ),
#endif

//===== CLASS DEFINITION ======================================================

/*
 * Class:    CWorkerEvent
 * Purpose:  Derive the basic wxEvent class to create the type of events sent
 *           by the worker thread
 * Comments: none
 */
class CWorkerEvent : public wxNotifyEvent
{
    public:
    
        /*
         * Method:    CWorkerEvent()
         * Purpose:   constructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */ 
        CWorkerEvent();
    
        /*
         * Method:    CWorkerEvent()
         * Purpose:   constructor
         * Arguments:
         *
         * [i] tInt32 aId,      Id
         * [i] tUint32 aEvent,  event's ID
         * [i] tUint32 aData,   event's data
         *
         * Return:    none
         * Comments:  none
         */ 
        CWorkerEvent(tInt32 aId,tUint32 aEvent,tUint32 aData);

        /*
         * Method:    CWorkerEvent()
         * Purpose:   copy constructor
         * Arguments:
         *
         * [i] const CWorkerEvent& aEvent, event to copy
         *
         * Return:    none
         * Comments:  none
         */ 
        CWorkerEvent(const CWorkerEvent& aEvent);

        /*
         * Method:    ~CWorkerEvent()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~CWorkerEvent() {};

        /*
         * Method:    Clone()
         * Purpose:   clone the event
         * Arguments: none
         * Return:    a new cloned event
         * Comments:  none
         */   
        wxEvent *Clone(void) const { return new CWorkerEvent(*this); }
    
    public: // data

        tUint32 iEvent;
        tUint32 iData;
};

/*
 * Class:    PWorker
 * Purpose:  Derive the standard thread class to create the worker type thread
 * Comments: none
 */
class PWorker : public wxThread
{
    public: // cons./des.

        /*
         * Method:    PWorker()
         * Purpose:   constructor
         * Arguments: 
         *   
         * [i] tInt32 aId,              worker's ID  
         * [i] wxEvtHandler* aHandler,  handle to be notified by the worker
         *
         * Return:    none
         * Comments:  none
         */ 
        PWorker(tInt32 aId,wxEvtHandler* aHandler);

         /*
         * Method:    ~PWorker()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~PWorker();
        
        /*
         * Method:    Start()
         * Purpose:   instruct the worker to start
         * Arguments: none
         * Return:    false if failed
         * Comments:  none
         */         
        virtual bool Start();
        
    protected: // callbacks

        /*
         * Method:    OnEntry()
         * Purpose:   called when the thread is starting
         * Arguments: none
         * Return:    none
         * Comments:  none
         */ 
        virtual void OnEntry() {};
        
        /*
         * Method:    OnRunning()
         * Purpose:   called when the thread is running (body)
         * Arguments: none
         * Return:    execution return code
         * Comments:  none
         */ 
        virtual tUint32 OnRunning() {return 0;};        

    protected: // methods

        /*
         * Method:    NotifyHandler()
         * Purpose:   notify the handler of a given event
         * Arguments:
         *
         * [i] Uint32 aEvent, event's ID
         * [i] tUint32 aData, event's data
         *
         * Return:    none
         * Comments:  none
         */ 
        void NotifyHandler(tUint32 aEvent,tUint32 aData = 0);
        
    protected: // from wxThread      

        /*
         * Method:    Entry()
         * Purpose:   thread entry method
         * Arguments: none
         * Return:    none
         * Comments:  do not derive, use OnRunning() instead
         */ 
        ExitCode Entry();

    private: // data

        tInt32        iId;          // Id
        wxEvtHandler* iHandler;     // handler
};
