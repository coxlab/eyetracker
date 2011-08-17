/*
| ==============================================================================
| Copyright (C) 2009 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         EvntWindow.cpp
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Implement the window that display the camera's events
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

#include <wx/icon.h>
#include <wx/stattext.h>
#include <wx/button.h>
#include <wx/checkbox.h>

#include <EvntWindow.h>

//===== BITMAPS ===============================================================

#include <bitmap9.xpm>

//===== DEFINES ===============================================================

enum
{
    ID_CLEAR = 1,
    ID_PAUSE,
    ID_AUTOS
};

//===== CONSTANTS =============================================================

// standard size of the window
const int kInitWidth    = 550;
const int kInitHeight   = 400;
// extra padding (scrollbar width)
const int kPadding      = 16;
// height of the panel
const int kPanelHeight  = 40;
//
const int kMaxEvents    = 5;
// max number of events displayed in the list
const int kMaxListCount = 5000;

//===== LOCAL DATA ============================================================

//===== EVENTS TABLE ==========================================================

BEGIN_DECLARE_EVENT_TYPES()
    DECLARE_EVENT_TYPE(dAPPEND,wxID_ANY)
END_DECLARE_EVENT_TYPES()

DEFINE_EVENT_TYPE(dAPPEND)

BEGIN_EVENT_TABLE(CEvntWindow, PChildWindow)
    EVT_SIZE(CEvntWindow::OnSize)
    EVT_COMMAND(wxID_ANY,dAPPEND,CEvntWindow::OnAppendEvents)
    EVT_BUTTON(wxID_ANY,CEvntWindow::OnButtonPushed)
    EVT_CHECKBOX(wxID_ANY,CEvntWindow::OnButtonPushed)
END_EVENT_TABLE()

//===== CLASS DEFINITION ======================================================


class wxEventsEvent : public wxCommandEvent
{
    public:
    
        wxEventsEvent(WXTYPE commandEventType = 0,int id = 0);
        wxEventsEvent(const wxEventsEvent& aSource);
        ~wxEventsEvent() {};
        
        void Clear() {memset(iEvents,0,sizeof(iEvents));}
        
        wxEvent* Clone() const {
        
            return new wxEventsEvent(*this);
        
        }
    
    public:    
    
        tPvCameraEvent iEvents[kMaxEvents];

};

wxEventsEvent::wxEventsEvent(WXTYPE commandEventType,int id)
    : wxCommandEvent(commandEventType,id)
{
    memset(iEvents,0,sizeof(iEvents));
}

wxEventsEvent::wxEventsEvent(const wxEventsEvent& aSource)
    : wxCommandEvent(aSource)
{
    memcpy(iEvents,aSource.iEvents,sizeof(iEvents));
}

#ifdef __WXMSW__
void __stdcall CameraEventsCB(void* Context,tPvHandle Camera,const tPvCameraEvent* EventList,unsigned long EventListLength);
#else
void CameraEventsCB(void* Context,tPvHandle Camera,const tPvCameraEvent* EventList,unsigned long EventListLength);
#endif 

/*
 * Method:    CEvntWindow()
 * Purpose:   constructor
 * Comments:  none
 */
CEvntWindow::CEvntWindow(PChildWindowObserver& aObserver,const tPvCameraInfoEx& aInfo,tPvHandle aHandle)
    : PChildWindow(aObserver,wxT(""),wxSize(kInitWidth,kInitHeight),wxRESIZE_BORDER) , iHandle(aHandle)
{
    wxString lString;
    
    iMain   = NULL;
    iPanel  = NULL;
    iList   = NULL;
    iStamp  = 0;
    iPaused = false;
    iAutoS  = true;

    // format the title of the window
    lString =  wxString(aInfo.SerialNumber,wxConvUTF8);
    lString += _T(" (");
    lString += wxString(aInfo.CameraName,wxConvUTF8);
    lString += _T(") - Events");
    // and set it
    SetTitle(lString);
    // Give it an icon
    SetIcon(wxIcon(bitmap9));
    // center on the screen
    CentreOnScreen(wxBOTH);
    // set the minimum size
    SetMinSize(wxSize(kInitWidth,kInitHeight));

    // create the main sizer
    iMain = new wxBoxSizer(wxVERTICAL);
    if(iMain)
    {    
        // create the list
        iList = new wxListBox(this,wxID_ANY,wxDefaultPosition,wxSize(kInitWidth,kInitHeight - kPanelHeight),0); //wxLB_SINGLE|wxLB_ALWAYS_SB);
        if(iList)
        {
    
            // add it to the sizer
            iMain->Add(iList,wxSizerFlags().Proportion(0).Align(wxALIGN_BOTTOM).Expand().Border(wxALL,0));
    
            // then create the panel
            iPanel = new wxPanel(this,wxID_ANY,wxDefaultPosition,wxSize(kInitWidth,kPanelHeight));
            if(iPanel)
            {
                wxCheckBox* lBox = new wxCheckBox(iPanel,ID_AUTOS,_T("Auto-scroll"));
                
                lBox->SetValue(true);
            
                // set the minimum size of the panel
                iPanel->SetMinSize(wxSize(kInitWidth,kPanelHeight));
                // then create a sizer for the panel
                iSizer = new wxBoxSizer(wxHORIZONTAL);
                if(iSizer)
                    iPanel->SetSizer(iSizer);
                    
                iPauseButton = new wxButton(iPanel,ID_PAUSE,_T("Pause"));    
                    
                iSizer->Add(new wxButton(iPanel,ID_CLEAR,_T("Clear")),wxSizerFlags().Proportion(0).Align(wxALIGN_LEFT).Expand().Border(wxALL,0));
                iSizer->Add(iPauseButton,wxSizerFlags().Proportion(0).Align(wxALIGN_LEFT).Expand().Border(wxALL,0));
                iSizer->Add(lBox,wxSizerFlags().Proportion(0).Align(wxALIGN_RIGHT).Expand().Border(wxALL,0));    
            
                // add it to the sizer
                iMain->Add(iPanel,wxSizerFlags().Proportion(0).Align(wxALIGN_BOTTOM).Expand().Border(wxALL,0));
            }  
                
            // set the main sizer in the window
            SetSizer(iMain);
            // and make that the sizer adjust its size to the window
            iMain->FitInside(this);
        }
    }
}

/*
 * Method:    ~CEvntWindow()
 * Purpose:   destructor
 * Comments:  none
 */
CEvntWindow::~CEvntWindow()
{
}

/*
 * Method:    OnSize()
 * Purpose:   called when the window size is been changed
 * Arguments:
 *
 * [b] wxSizeEvent& aEvent, event received
 *
 * Return:    none
 * Comments:  none
 */
void CEvntWindow::OnSize(wxSizeEvent& aEvent)
{
    wxSize lSize = GetClientSize();

    // force the size to update its widget size and position
    iMain->SetDimension(0,0,lSize.GetWidth(),lSize.GetHeight());
    iMain->Layout();
    iSizer->SetDimension(0,0,iPanel->GetSize().GetWidth(),iPanel->GetSize().GetHeight());  
}

/*
 * Method:    OnOpen()
 * Purpose:   called when the window is open
 * Comments:  none
 */
void CEvntWindow::OnOpen(wxCommandEvent& aEvent)
{
    tPvUint32 lFreq;

    // retreive the timestamp frequency of the camera
    if(!PvAttrUint32Get(iHandle,"TimeStampFrequency",&lFreq))
        iFrequency = (double)lFreq;
    else
        iFrequency = 0;

    // register a callback for events
    PvCameraEventCallbackRegister(iHandle,CameraEventsCB,this);
    
    PChildWindow::OnOpen(aEvent);
}

/*
 * Method:    OnClose()
 * Purpose:   called when the window is been closed
 * Comments:  none
 */
void CEvntWindow::OnClose(wxCloseEvent& aEvent)
{
    PvCameraEventCallbackUnRegister(iHandle,CameraEventsCB);

    PChildWindow::OnClose(aEvent);
}

/*
 * Method:    OnNotification()
 * Purpose:   called when the window is notified of
 *            something
 * Comments:  none
 */
void CEvntWindow::OnNotification(CNotifyEvent& aEvent)
{
}

/*
 * Method:    OnButtonPushed()
 * Purpose:   called when the user pressed one of the buttons
 *            field
 * Comments:  none
 */ 
void CEvntWindow::OnButtonPushed(wxCommandEvent& aEvent)
{
    switch(aEvent.GetId())
    {
        case ID_CLEAR:
        {
            iList->Clear();
            break;
        }
        case ID_PAUSE:
        {
            iPaused = !iPaused;
            
            if(iPaused)
                iPauseButton->SetLabel(_T("Resume"));
            else
                iPauseButton->SetLabel(_T("Pause"));
            
            break;
        }        
        case ID_AUTOS:
        {
            iAutoS = !iAutoS;   
            break;
        }
        default:
            break;
    }    
}

/*
 * Method:    OnAppendEvents()
 * Purpose:   called when a set of camera events are to be appended
 * Comments:  none
 */       
void CEvntWindow::OnAppendEvents(wxCommandEvent& aEvent)
{
    if(!iPaused)
    {
        unsigned long long  lStamp;
        double              lTime;
        char                lBuffer[128];
        wxEventsEvent&      lEvent = (wxEventsEvent&)aEvent;

        // limit the number of displayed events        
        while(iList->GetCount() > kMaxListCount)
            iList->Delete(0);
        
        for(int i=0;i<kMaxEvents;i++)
            if(lEvent.iEvents[i].EventId)
            {
                lStamp = lEvent.iEvents[i].TimestampHi;
                lStamp <<= 32;
                lStamp += lEvent.iEvents[i].TimestampLo;

                if(iStamp)
                    lTime = ((long double)lStamp - (long double)iStamp) / iFrequency;
                else
                {
                    lTime = 0;
                    iStamp = lStamp;
                }        
            
                sprintf(lBuffer,"% 10.2lf : %u [0x%08X,0x%08X,0x%08X,0x%08X]",lTime,
                lEvent.iEvents[i].EventId,lEvent.iEvents[i].Data[0],lEvent.iEvents[i].Data[1],lEvent.iEvents[i].Data[2],lEvent.iEvents[i].Data[3]);

                iList->Append(wxString(lBuffer,wxConvUTF8));
            }   
            
        if(iAutoS)    
            iList->SetFirstItem(iList->GetCount() - 1);    
    } 
}

/*
 * Method:    OnCameraEvents()
 * Purpose:   called when a camera event(s) is received
 * Comments:  none
 */
void CEvntWindow::OnCameraEvents(const tPvCameraEvent* EventList,unsigned long EventListLength)
{
    int i,j;
    wxEventsEvent lEvent(dAPPEND,wxID_ANY);
    
    lEvent.SetEventObject(this);
    
    for(j=0,i=0;i<EventListLength;i++)
    {
        lEvent.iEvents[j] = EventList[i];
        
        j++;
        
        if(j==kMaxEvents)
        {
            GetEventHandler()->AddPendingEvent(lEvent);
            lEvent.Clear();
            j=0;
        }
    }
    
    if(j)
        GetEventHandler()->AddPendingEvent(lEvent);    
}

#ifdef __WXMSW__
void __stdcall CameraEventsCB(void* Context,tPvHandle Camera,const tPvCameraEvent* EventList,unsigned long EventListLength)
#else
void CameraEventsCB(void* Context,tPvHandle Camera,const tPvCameraEvent* EventList,unsigned long EventListLength)
#endif 
{
    CEvntWindow* lWindow = (CEvntWindow*)Context;

    if(lWindow)
        lWindow->OnCameraEvents(EventList,EventListLength);    
}
