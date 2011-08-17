/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         ChildWindow.h
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Define the basic child window class
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

#ifndef _CHILD_WINDOW_H
#define _CHILD_WINDOW_H

//===== INCLUDE FILES =========================================================

#include <PvApi.h>
#include <wx/frame.h>
#include <wx/event.h>

//===== CLASS DEFINITION ======================================================

class PChildWindow; // forward def

/*
 * Class:    CNotifyEvent
 * Purpose:  Derive the basic wxEvent class to create a type of event that can
 *           be received by the Child Window(s)
 * Comments: none
 */
class CNotifyEvent : public wxNotifyEvent
{
    public:
    
        /*
         * Method:    CNotifyEvent()
         * Purpose:   constructor
         * Arguments:
         *
         * [i] int aEvent,  event's code
         * [i] void* aData, event's data
         *
         * Return:    none
         * Comments:  none
         */ 
        CNotifyEvent(int aEvent,void* aData);

        /*
         * Method:    CNotifyEvent()
         * Purpose:   copy constructor
         * Arguments:
         *
         * [i] const CNotifyEvent& aEvent, event to copy
         *
         * Return:    none
         * Comments:  none
         */ 
        CNotifyEvent(const CNotifyEvent& aEvent);

        /*
         * Method:    ~CNotifyEvent()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~CNotifyEvent() {};

        /*
         * Method:    Clone()
         * Purpose:   clone the event
         * Arguments: none
         * Return:    a new cloned event
         * Comments:  none
         */   
        wxEvent *Clone(void) const { return new CNotifyEvent(*this); }

        /*
         * Method:    GetEvent()
         * Purpose:   get the event code
         * Arguments: none
         * Return:    the event's code
         * Comments:  none
         */  
        int GetEvent() const {return iEvent;};

        /*
         * Method:    GetData()
         * Purpose:   get the event associated data
         * Arguments: none
         * Return:    can be NULL
         * Comments:  none
         */  
        void* GetData() const {return iData;};

    protected: // data
            
        int   iEvent; // event code
        void* iData;  // event data (can be NULL)  
};


/*
 * Class:    PChildWindowObserver
 * Purpose:  Observer class for reporting child's event(s)
 * Comments: none
 */
class PChildWindowObserver
{
    public:

        /*
         * Method:    ~PChildWindowObserver()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        virtual ~PChildWindowObserver() {};

    protected:

        /*
         * Method:    OnChildClosed()
         * Purpose:   called when a child window is been closed
         * Arguments:
         *
         * [i] PChildWindow* aChild, child window
         *
         * Return:    none
         * Comments:  none
         */  
        virtual void OnChildClosed(PChildWindow* aChild) {};

        /*
         * Method:    OnChildError()
         * Purpose:   called when a child window is reporting an error to the user
         * Arguments:
         *
         * [i] const wchar_t* aMessage, message string
         * [i] tPvErr aErr,          PvAPI error code
         *
         * Return:    none
         * Comments:  none
         */              
        virtual void OnChildError(const wchar_t* aMessage,tPvErr aErr) {};

        friend class PChildWindow;
};

/*
 * Class:    PChildWindow
 * Purpose:  Derive the standard frame class to base of all child windows
 * Comments: none
 */
class PChildWindow : public wxFrame
{
    public: // cons./des.

        /*
         * Method:    PChildWindow()
         * Purpose:   constructor
         * Arguments:
         *
         * [i] PChildWindowObserver& aObserver, observer
         * [i] const wchar_t* aTitle,              title of the window
         * [i] const wxSize& aSize,             size of the window
         * [i] long aStyle,                     expected style of the window
         *
         * Return:    none
         * Comments:  none
         */ 
        PChildWindow(PChildWindowObserver& aObserver,const wchar_t* aTitle,const wxSize& aSize,long aStyle);

        /*
         * Method:    ~PChildWindow()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~PChildWindow();

        /*
         * Method:    Notify()
         * Purpose:   Send a notification of an event to the window
         * Arguments:
         *
         * [i] int aEvent,  Id of the event to notify
         * [i] void* aData, data associated with the event, if any
         * [i] bool aNow,   true if the notification must be synchronous
         *
         * Return:    none
         * Comments:  none
         */   
        void Notify(int aEvent,void* aData = NULL,bool aNow = false);

    public: // callbacks        

        /*
         * Method:    OnOpen()
         * Purpose:   called when the window is open
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        virtual void OnOpen(wxCommandEvent& aEvent) {};

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
        virtual void OnClose(wxCloseEvent& aEvent);

        /*
         * Method:    OnNotification()
         * Purpose:   called when the window is notified of
         *            something
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event (check the ID)
         *
         * Return:    none
         * Comments:  none
         */ 
        virtual void OnNotification(CNotifyEvent& aEvent) {};

    public: // callbacks

        DECLARE_EVENT_TABLE()

    protected: // methods
             
        /*
         * Method:    ReportAnError()
         * Purpose:   report an error to the user
         * Arguments:
         *
         * [i] const wchar_t* aMessage, message string
         * [i] tPvErr aErr,          PvAPI error code (if any)
         *
         * Return:    none
         * Comments:  none
         */              
        void ReportAnError(const wchar_t* aMessage,tPvErr aErr = ePvErrSuccess);

    protected: // data

        // observer
        PChildWindowObserver& iObserver;            
};

#endif // _CHILD_WINDOW_H
