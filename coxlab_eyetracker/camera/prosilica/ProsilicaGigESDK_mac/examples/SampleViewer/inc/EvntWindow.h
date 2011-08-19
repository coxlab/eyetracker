/*
| ==============================================================================
| Copyright (C) 2009 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         EvntWindow.h
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Define the window that display the camera's events
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
#include <ChildWindow.h>
#include <wx/sizer.h>
#include <wx/panel.h>
#include <wx/button.h>
#include <wx/listbox.h>

//===== CLASS DEFINITION ======================================================

/*
 * Class:    CMainWindow
 * Purpose:  Derive the standard frame class to create the main window of the
 *           application
 * Comments: none
 */
class CEvntWindow : public PChildWindow
{
    public: // cons./des.

        /*
         * Method:    CEvntWindow()
         * Purpose:   constructor
         * Arguments:
         *
         * [i] PChildWindowObserver& aObserver, observer
         * [i] const tPvCameraInfoEx& aInfo,    camera's information
         * [i] tPvHandle aHandle,               handle to the camera
         *
         * Return:    none
         * Comments:  none
         */ 
        CEvntWindow(PChildWindowObserver& aObserver,const tPvCameraInfoEx& aInfo,tPvHandle aHandle);

         /*
         * Method:    ~CEvntWindow()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~CEvntWindow();

    public: // callbacks
    
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
        void OnSize(wxSizeEvent& aEvent);

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
        void OnOpen(wxCommandEvent& aEvent);

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
        void OnNotification(CNotifyEvent& aEvent);
        
        /*
         * Method:    OnAppendEvents()
         * Purpose:   called when a set of camera events are to be appended
         * Arguments:
         *
         * [b] wxCommandEvent& aEvent, event received
         *
         * Return:    none
         * Comments:  none
         */       
        void OnAppendEvents(wxCommandEvent& aEvent);    
        
        /*
         * Method:    OnButtonPushed()
         * Purpose:   called when the user pressed one of the buttons
         *            field
         * Arguments:
         *
         * [b] wxCommandEvent& aEvent, event received
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnButtonPushed(wxCommandEvent& aEvent);            

        DECLARE_EVENT_TABLE()

    protected:

        /*
         * Method:    OnCameraEvents()
         * Purpose:   called when a camera event(s) is received
         * Arguments:
         *
         * [i] const tPvCameraEvent* EventList, array of events
         * [i] unsigned long EventListLength,   number of events in the array
         *
         * Return:    none
         * Comments:  none
         */
        void OnCameraEvents(const tPvCameraEvent* EventList,unsigned long EventListLength);

    private: // methods

            

    private: // data

        // handle to the camera
        tPvHandle        iHandle;
        // main sizer
        wxBoxSizer*      iMain;
        // list of events
        wxListBox*      iList;
        // panel
        wxPanel*         iPanel;
        // size to be used within the panel
        wxBoxSizer*      iSizer;  
        //
        wxButton*        iPauseButton;
        // last known event stamp
        double           iStamp;
        // camera frequency
        double           iFrequency;
        //
        bool             iPaused;
        bool             iAutoS;
        
        #ifdef __WXMSW__
        friend void __stdcall CameraEventsCB(void* Context,tPvHandle Camera,const tPvCameraEvent* EventList,unsigned long EventListLength);
        #else
        friend void CameraEventsCB(void* Context,tPvHandle Camera,const tPvCameraEvent* EventList,unsigned long EventListLength);
        #endif              
       
            
};
