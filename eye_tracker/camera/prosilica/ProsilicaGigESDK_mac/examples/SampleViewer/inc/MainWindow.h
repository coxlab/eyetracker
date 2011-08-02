/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         MainWindow.h
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Define the main window class
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

#include <wx/frame.h>
#include <wx/treectrl.h>
#include <wx/event.h>

#include <ChildWindow.h>
#include <Seeker.h>

//===== CLASS DEFINITION ======================================================

class wxMenuBar;    // forward def
class wxToolBar;    // forward def
class wxBoxSizer;   // forward def
class wxMenu;       // forward def

/*
 * Class:    CLinkEvent
 * Purpose:  Derive the basic wxEvent class to create the type of events received
 *           by the window on link events
 * Comments: none
 */
class CLinkEvent : public wxNotifyEvent
{
    public:
    
        /*
         * Method:    CLinkEvent()
         * Purpose:   constructor
         * Arguments:
         *
         * [i] tPvLinkEvent aEvent,     Event which occurred
         * [i] unsigned long aUniqueId, Unique ID of the camera related to the event
         *
         * Return:    none
         * Comments:  none
         */ 
        CLinkEvent(tPvLinkEvent aEvent,unsigned long aUniqueId);

        /*
         * Method:    CLinkEvent()
         * Purpose:   copy constructor
         * Arguments:
         *
         * [i] const CLinkEvent& aEvent, event to copy
         *
         * Return:    none
         * Comments:  none
         */ 
        CLinkEvent(const CLinkEvent& aEvent);

        /*
         * Method:    ~CLinkEvent()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~CLinkEvent() {};

        /*
         * Method:    Clone()
         * Purpose:   clone the event
         * Arguments: none
         * Return:    a new cloned event
         * Comments:  none
         */   
        wxEvent *Clone(void) const { return new CLinkEvent(*this); }

        /*
         * Method:    GetType()
         * Purpose:   get the link event type
         * Arguments: none
         * Return:    event code
         * Comments:  none
         */ 
        tPvLinkEvent GetType() const {return iEvent;};

        /*
         * Method:    GetUID()
         * Purpose:   get the UID of the camera associated with the
         *            event
         * Arguments: none
         * Return:    the UID
         * Comments:  none
         */         
        unsigned long GetUID() const {return iUniqueId;};
    
    private: // data

        // event type         
        tPvLinkEvent    iEvent;
        // unique ID of the camera related to the event
        unsigned long   iUniqueId;
};

/*
 * Class:    CErrorEvent
 * Purpose:  Derive the basic wxEvent class to create a type of event that can
 *           be received by the main window when an error occured
 * Comments: none
 */
class CErrorEvent : public wxNotifyEvent
{
    public:
    
        /*
         * Method:    CErrorEvent()
         * Purpose:   constructor
         * Arguments:
         *
         * [i] const tChar* aMessage, error message
         * [i] tPvErr aErr,           error code
         *
         * Return:    none
         * Comments:  none
         */ 
        CErrorEvent(const wchar_t* aMessage,tPvErr aErr);

        /*
         * Method:    CErrorEvent()
         * Purpose:   copy constructor
         * Arguments:
         *
         * [i] const CErrorEvent& aEvent, event to copy
         *
         * Return:    none
         * Comments:  none
         */ 
        CErrorEvent(const CErrorEvent& aEvent);

        /*
         * Method:    ~CErrorEvent()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~CErrorEvent() {};

        /*
         * Method:    Clone()
         * Purpose:   clone the event
         * Arguments: none
         * Return:    a new cloned event
         * Comments:  none
         */   
        wxEvent *Clone(void) const { return new CErrorEvent(*this); }

        /*
         * Method:    GetMessage()
         * Purpose:   get the message
         * Arguments: none
         * Return:    a reference to the message string
         * Comments:  none
         */  
        const wxString& GetMessage() const {return iMessage;};

        /*
         * Method:    GetError()
         * Purpose:   get the error code
         * Arguments: none
         * Return:    a PvAPI error code
         * Comments:  none
         */  
        tPvErr GetError() const {return iErr;};

    protected: // data
            
        wxString iMessage;  // message string
        tPvErr   iErr;      // error code
};

/*
 * Class:    CMainWindow
 * Purpose:  Derive the standard frame class to create the main window of the
 *           application
 * Comments: none
 */
class CMainWindow : public wxFrame , public PChildWindowObserver
{
    public: // cons./des.

        /*
         * Method:    CMainWindow()
         * Purpose:   constructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */ 
        CMainWindow();

         /*
         * Method:    ~CMainWindow()
         * Purpose:   destructor
         * Arguments: noneCLinkEvent::
         * Return:    none
         * Comments:  none
         */        
        ~CMainWindow();
        
    public: // callbacks

        /*
         * Method:    OnOpen()
         * Purpose:   called when the window is opening
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnOpen(wxCommandEvent& aEvent);

        /*
         * Method:    OnAbout()
         * Purpose:   called when the user select the "About" item from the menu
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnAbout(wxCommandEvent& aEvent);

        /*
         * Method:    OnQuit()
         * Purpose:   called when the user select the "Exit" item from the menu
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */         
        void OnQuit(wxCommandEvent& aEvent);

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
        void OnClose(wxCloseEvent& aEvent);

        /*
         * Method:    OnToolClick()
         * Purpose:   called when the user click on of the tools on the
         *            toll bar
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  nonePChildWindowObserver
         */         
        void OnToolClick(wxCommandEvent& aEvent);

        /*
         * Method:    OnLinkEvent()
         * Purpose:   called when an event occured on the link
         * Arguments:
         *
         * [i] CLinkEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */    
        void OnLinkEvent(CLinkEvent& aEvent);

        /*
         * Method:    OnErrorEvent()
         * Purpose:   called when an error occured
         * Arguments:
         *
         * [i] CErrorEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */    
        void OnErrorEvent(CErrorEvent& aEvent);

        /*
         * Method:    OnRaiseAll()
         * Purpose:   called when the user select the "Show all" item from the menu
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  this will force all the application windows to be raised
         */ 
        void OnRaiseAll(wxCommandEvent& aEvent);

        /*
         * Method:    OnRaiseOne()
         * Purpose:   called when the user select one of the windows to be raised
         *            from the menu
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnRaiseOne(wxCommandEvent& aEvent);

        /*
         * Method:    OnCloseAll()
         * Purpose:   called when the user select the "Close all" item from the menu
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  this will force all the application windows to be closed
         */ 
        void OnCloseAll(wxCommandEvent& aEvent);
        
        /*
         * Method:    OnSeekerEvent()
         * Purpose:   called when a the seeker sent an event to the window
         * Arguments:
         *
         * [i] CWorkerEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */         
        void OnSeekerEvent(CWorkerEvent& aEvent);

        DECLARE_EVENT_TABLE()

    protected: // from PChildWindowObserver

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
        void OnChildClosed(PChildWindow* aChild);

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
        void OnChildError(const wchar_t* aMessage,tPvErr aErr);

    private: // methods

        /*
         * Method:    ListCameras()
         * Purpose:   list all the cameras already visible
         * Arguments: none
         * Return:    none
         * Comments:  none
         */
        void ListCameras();

        /*
         * Method:    KnownCamera()
         * Purpose:   check if a given camera is known (in the tree)
         * Arguments:
         *
         * [i] unsigned int aUID, Unique ID of the camera
         *
         * Return:    true or false
         * Comments:  none
         */
        bool KnownCamera(unsigned int aUID);

        /*
         * Method:    OpenCamera()
         * Purpose:   open a given camera
         * Arguments:
         *
         * [i] unsigned long aUID, UID of the camera to be open
         * [o] bool& aMaster,      set to true if the camera was open in master mode
         *
         * Return:    handle to the camera, NULL if failed
         * Comments:  none
         */
        tPvHandle OpenCamera(unsigned long aUID,bool& aMaster);

        /*
         * Method:    CloseCamera()
         * Purpose:   close a given camera
         * Arguments:
         *
         * [i] tPvHandle aHandle, handle to the camera
         *
         * Return:    handle to the camera, NULL if failed
         * Comments:  none
         */
        void CloseCamera(tPvHandle aHandle);

        /*
         * Method:    ExportCamera()
         * Purpose:   export the setup of a given camera
         * Arguments:
         *
         * [i] tPvHandle aHandle,           handle to the camera
         * [i] const wxString& aFilename,   filename
         *
         * Return:    false if failed
         * Comments:  none
         */
        bool ExportCamera(tPvHandle aHandle,const wxString& aFilename);
        
        /*
         * Method:    RefreshWindowsList()
         * Purpose:   refresh the windows list in the menu
         * Arguments: none
         * Return:    none
         * Comments:  none
         */
        void RefreshWindowsList();

    private: // data

        // sizer used to "pack" the control on the window
        wxBoxSizer*  iSizer;
        // menu bar        
        wxMenuBar*   iMenuBar;
        // windows menu
        wxMenu*      iMenuWin;
        // tools bar
        wxToolBar*   iToolBar;
        // cameras tree
        wxTreeCtrl*  iTree;
        // root item in the tree
        wxTreeItemId iRoot;
        // thread used when seeking a camera
        CSeeker*     iSeeking;
};
