/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         ChildWindow.cpp
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Implement the basic child window class
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

#include <ChildWindow.h>
#include <wx/msgdlg.h>

//===== DEFINES ===============================================================

BEGIN_DECLARE_EVENT_TYPES()
    DECLARE_EVENT_TYPE(dOPEN,wxID_ANY)
END_DECLARE_EVENT_TYPES()

DEFINE_EVENT_TYPE(dOPEN)
DEFINE_EVENT_TYPE(wxEVT_NOTICE)

typedef void (wxEvtHandler::*wxNoticeEventFunction)(CNotifyEvent&);

#define EVT_NOTICE(id,fn) \
    DECLARE_EVENT_TABLE_ENTRY( wxEVT_NOTICE, id, -1, \
    (wxObjectEventFunction) (wxEventFunction) (wxCommandEventFunction) (wxNoticeEventFunction) \
    wxStaticCastEvent( wxNoticeEventFunction, & fn ), (wxObject *) NULL ),

BEGIN_EVENT_TABLE(PChildWindow, wxFrame)
    EVT_CLOSE(PChildWindow::OnClose)
    EVT_COMMAND(wxID_ANY,dOPEN,PChildWindow::OnOpen)
    EVT_NOTICE(wxID_ANY,PChildWindow::OnNotification)
END_EVENT_TABLE()

//===== LOCAL DATA ============================================================

//===== CLASS DEFINITION ======================================================

/*
 * Method:    CNotifyEvent()
 * Purpose:   constructor
 * Comments:  none
 */
CNotifyEvent::CNotifyEvent(int aEvent,void* aData)
    : wxNotifyEvent(wxEVT_NOTICE,wxID_ANY)
{
    iEvent = aEvent;
    iData  = aData;
}

/*
 * Method:    CNotifyEvent()
 * Purpose:   copy constructor
 * Comments:  none
 */
CNotifyEvent::CNotifyEvent(const CNotifyEvent& aEvent)
    : wxNotifyEvent(wxEVT_NOTICE,wxID_ANY)
{
    iEvent = aEvent.iEvent;
    iData  = aEvent.iData;
}

/*
 * Method:    CChildWindow()
 * Purpose:   constructor
 * Comments:  none
 */
PChildWindow::PChildWindow(PChildWindowObserver& aObserver,const wchar_t* aTitle,const wxSize& aSize,long aStyle)
#ifdef __WXMSW__
    : wxFrame(NULL,-1,aTitle,wxDefaultPosition,aSize,aStyle | wxMINIMIZE_BOX | wxSYSTEM_MENU | wxCLOSE_BOX | wxCAPTION), iObserver(aObserver)
#else
    : wxFrame(NULL,-1,aTitle,wxDefaultPosition,aSize,aStyle | wxMINIMIZE_BOX | wxCLOSE_BOX | wxCAPTION), iObserver(aObserver)
#endif
{
    // append a custom event for the ::Open() callback
    wxCommandEvent lEvent(dOPEN,wxID_ANY);
    lEvent.SetEventObject(this);
    GetEventHandler()->AddPendingEvent(lEvent);
}

/*
 * Method:    ~CChildWindow()
 * Purpose:   destructor
 * Comments:  none
 */
PChildWindow::~PChildWindow()
{
}

/*
 * Method:    Notify()
 * Purpose:   Send a notification of an event to the window
 * Comments:  none
 */
void PChildWindow::Notify(int aEvent,void* aData /* = NULL */,bool aNow /* = false */)
{
    CNotifyEvent lEvent(aEvent,aData);
    lEvent.SetEventObject(this);
    if(aNow)
        GetEventHandler()->ProcessEvent(lEvent);
    else    
        GetEventHandler()->AddPendingEvent(lEvent);    
}

/*
 * Method:    OnClose()
 * Purpose:   called when the window is been closed
 * Arguments:
 *
 * [b] wxCloseEvent& aEvent, event received 
 *
 * Return:    none
 * Comments:  none
 */
void PChildWindow::OnClose(wxCloseEvent& aEvent)
{
    iObserver.OnChildClosed(this);
    Destroy();    
}

/*
 * Method:    ReportAnError()
 * Purpose:   report an error to the user
 * Comments:  none
 */
void PChildWindow::ReportAnError(const wchar_t* aMessage,tPvErr aErr /* = ePvErrSuccess */)
{
    iObserver.OnChildError(aMessage,aErr);
}

