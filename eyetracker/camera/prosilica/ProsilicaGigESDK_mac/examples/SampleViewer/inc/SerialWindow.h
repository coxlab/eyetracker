/*
| ==============================================================================
| Copyright (C) 2009 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         SerialWindow.h
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Define the window that display the camera's serialIO shell
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
#include <wx/textctrl.h>
#include <wx/combobox.h>
#include <wx/timer.h>

//===== CLASS DEFINITION ======================================================

/*
 * Class:    CMainWindow
 * Purpose:  Derive the standard frame class to create the main window of the
 *           application
 * Comments: none
 */
class CSerialWindow : public PChildWindow
{
    public: // cons./des.

        /*
         * Method:    CSerialWindow()
         * Purpose:   constructor
         * Arguments:
         *
         * [i] PChildWindowObserver& aObserver, observer
         * [i] const tPvCameraInfoEx& aInfo,      camera's information
         * [i] tPvHandle aHandle,               handle to the camera
         *
         * Return:    none
         * Comments:  none
         */ 
        CSerialWindow(PChildWindowObserver& aObserver,const tPvCameraInfoEx& aInfo,tPvHandle aHandle);

         /*
         * Method:    ~CSerialWindow()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~CSerialWindow();

    public: // callbacks
    
        /*
         * Method:    OnTimer()
         * Purpose:   called when the timer fires
         * Arguments:
         *
         * [b] wxTimerEvent& aEvent, event received
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnTimer(wxTimerEvent& aEvent);    
    
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
        
        /*
         * Method:    OnComboChanged()
         * Purpose:   called when the user has changed the value of a combobox
         * Arguments:
         *
         * [b] wxCommandEvent& aEvent, event received
         *
         * Return:    none
         * Comments:  none
         */        
        void OnComboChanged(wxCommandEvent& aEvent);   
        
        /*
         * Method:    OnEnterPressed()
         * Purpose:   called when the user has pressed the enter key
         * Arguments:
         *
         * [b] wxCommandEvent& aEvent, event received
         *
         * Return:    none
         * Comments:  none
         */        
        void OnEnterPressed(wxCommandEvent& aEvent);            

        DECLARE_EVENT_TABLE()

    protected:

    private: // methods

        /*
         * Method:    SetupInitial()
         * Purpose:   initial setup of the controls
         * Arguments:
         *
         * [i] unsigned long aInquiry, inquiry values
         * [i] unsigned long aModes,   modes values  
         *
         * Return:    none
         * Comments:  none
         */ 
        void SetupInitial(unsigned long aInquiry,unsigned long aModes);  
        
        /*
         * Method:    SetupConnected()
         * Purpose:   setup of the controls when connected
         * Arguments: none
         * Return:    none
         * Comments:  none
         */         
        void SetupConnected();
        
        /*
         * Method:    SetupDisconnected()
         * Purpose:   setup of the controls when disconnected
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        void SetupDisconnected();  
        
        /*
         * Method:    AddRxString()
         * Purpose:   add a received string to the list
         * Arguments:
         *
         * [i] const char* aString, received string
         *
         * Return:    none
         * Comments:  none
         */        
        void AddRxString(const char* aString);
        
        /*
         * Method:    AddTxString()
         * Purpose:   add a transmitted string to the list
         * Arguments:
         *
         * [i] const char* aString, transmitted string
         *
         * Return:    none
         * Comments:  none
         */        
        void AddTxString(const char* aString);

    private: // data

        // handle to the camera
        tPvHandle        iHandle;
        // main sizer
        wxBoxSizer*      iMain;
        // list of strings
        wxListBox*       iList;
        // panels
        wxPanel*         iPanelTop;
        wxPanel*         iPanelBottom;
        // size to be used within the panel
        wxBoxSizer*      iSizer;  
        // controls
        wxTextCtrl*      iEntryField;   
        wxButton*        iButtonSend;
        wxComboBox*      iComboBaud; 
        wxComboBox*      iComboParity;
        wxComboBox*      iComboCharLen;
        wxComboBox*      iComboStopBits;
        wxButton*        iButtonConnect;
        wxButton*        iButtonDisconnect;
        // timer
        wxTimer*         iTimer;
        //
        char             iStringBuffer[512];
        unsigned int     iStringIndex;
            
};
