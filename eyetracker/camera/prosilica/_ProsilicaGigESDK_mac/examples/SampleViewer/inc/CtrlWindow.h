/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         CtrlWindow.h
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Define the window that display the camera controls
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
#include <wx/timer.h>
#include <wx/panel.h>
#include <wx/button.h>
#include <wx/stattext.h>
#include <wx/slider.h>
#include <wx/textctrl.h>
#include <wx/combobox.h>

#include <treelistctrl.h>
#include <mmMultiButton.h>


// event used to indicate when a live window is opened/closed
const int kEvnLiveOpened = 0xA;
const int kEvnLiveClosed = 0xB;

//===== CLASS DEFINITION ======================================================

/*
 * Class:    CMainWindow
 * Purpose:  Derive the standard frame class to create the main window of the
 *           application
 * Comments: none
 */
class CCtrlWindow : public PChildWindow
{
    public: // cons./des.

        /*
         * Method:    CCtrlWindow()
         * Purpose:   constructor
         * Arguments:
         *
         * [i] PChildWindowObserver& aObserver, observer
         * [i] const tPvCameraInfo& aInfo,      camera's information
         * [i] tPvHandle aHandle,               handle to the camera
         * [i] bool aRW,                        true when the camera is open in Read/Write mode
         *
         * Return:    none
         * Comments:  none
         */ 
        CCtrlWindow(PChildWindowObserver& aObserver,const tPvCameraInfo& aInfo,tPvHandle aHandle,bool aRW);

         /*
         * Method:    ~CCtrlWindow()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~CCtrlWindow();

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
         * Method:    OnSelection()
         * Purpose:   called when the user select one of the item from the tree
         * Arguments:
         *
         * [b] wxTreeEvent& aEvent, event received
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnSelection(wxTreeEvent& aEvent);

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
         * Method:    OnEnterPressed()
         * Purpose:   called when the user pressed the ENTER key in
         *            the entry field
         * Arguments:
         *
         * [b] wxCommandEvent& aEvent, event received
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnEnterPressed(wxCommandEvent& aEvent);

        /*
         * Method:    OnSliderScrolled()
         * Purpose:   called when the user use the slider
         * Arguments:
         *
         * [b] wxScrollEvent& aEvent, event received
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnSliderScrolled(wxScrollEvent& aEvent);

        /*
         * Method:    OnEntryChanged()
         * Purpose:   called when the user have changed the
         *            value within the exntry field
         * Arguments:
         *
         * [b] wxCommandEvent& aEvent, event received
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnEntryChanged(wxCommandEvent& aEvent);

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

        DECLARE_EVENT_TABLE()

    private: // methods

        /*
         * Method:    TreeFill()
         * Purpose:   Fill the tree with all the attributes
         * Arguments: none
         * Return:    none
         * Comments:  none
         */   
        void TreeFill();
        
        /*
         * Method:    TreeRefresh()
         * Purpose:   Refresh the value of all the volatile attributes
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        void TreeRefresh();

        /*
         * Method:    PreparePathToAttribute()
         * Purpose:   Get the last item on the path (build the path in the tree if necessary)
         * Arguments:
         *
         * [i] const char* aPath, path to be prepared
         *
         * Return:    last tree item (parent)
         * Comments:  none
         */   
        wxTreeItemId PreparePathToAttribute(const char* aPath);

        /*
         * Method:    SeekChild()
         * Purpose:   Seek a given child of a tree item
         * Arguments:
         *
         * [i] wxTreeItemId aRoot,      parent item
         * [i] const wxString& aLabel,  label of the child to seek
         *
         * Return:    tree item found (will be invalid if not found)
         * Comments:  none
         */   
        wxTreeItemId SeekChild(wxTreeItemId aRoot,const wxString& aLabel);

        /*
         * Method:    SeekPath()
         * Purpose:   Seek a given path of a tree item
         * Arguments:
         *
         * [i] const wxString& aPath,   path to seek
         *
         * Return:    tree item found (will be invalid if not found)
         * Comments:  none
         */ 
        wxTreeItemId SeekPath(const wxString& aPath);

        /*
         * Method:    RefreshChild()
         * Purpose:   Refresh a given child from the tree
         * Arguments:
         *
         * [i] wxTreeItemId aChild, tree item
         * [i] unsigned int aFlag,  flag to be present for the attribute
         *                          to be updated
         *
         * Return:    none
         * Comments:  none         
         */ 
        void RefreshChild(wxTreeItemId aChild,unsigned int aFlag = 0);

        /*
         * Method:    RefreshImpacted()
         * Purpose:   Refresh all the attributes that have
         *            been impacted by a change
         * Arguments:
         *
         * [i] const char* aImpact, impact string
         *
         * Return:    none
         * Comments:  none         
         */ 
        void RefreshImpacted(const char* aImpact);

        /*
         * Method:    RefreshPath()
         * Purpose:   Refresh all the attributes located
         *            at the path
         * Arguments:
         *
         * [i] const wxString& aPath, path
         *
         * Return:    none
         * Comments:  none         
         */ 
        void RefreshPath(const wxString& aPath);

        /*
         * Method:    FormatAttributeValue()
         * Purpose:   Format the attribute value in a string for display
         * Arguments:
         *
         * [i] const char* aLabel,              attribute's label
         * [i] const tPvAttributeInfo &aInfo,   attribute's details
         * [o] wxString& aString,               string to format the value in
         *
         * Return:    false if failed
         * Comments:  none
         */   
        bool FormatAttributeValue(const char* aLabel,const tPvAttributeInfo &aInfo,wxString& aString);

        /*
         * Method:    EditAttribute()
         * Purpose:   edit a currently selected attribute (if possible)
         * Arguments: none
         * Return:    false if failed
         * Comments:  none
         */   
        void EditAttribute();

        /*
         * Method:    ApplyAttribute()
         * Purpose:   apply the attribute change
         * Arguments: none
         * Return:    none
         * Comments:  none
         */  
        void ApplyAttribute();

        /*
         * Method:    ReloadAttribute()
         * Purpose:   reload the attribute change
         * Arguments: none
         * Return:    none
         * Comments:  none
         */  
        void ReloadAttribute();

        /*
         * Method:    SetupField()
         * Purpose:   setup the edition field for the current attribute
         * Arguments: none
         * Return:    false if failed
         * Comments:  none
         */  
        bool SetupField();

        /*
         * Method:    ClearField()
         * Purpose:   remove the edition field (if any)
         * Arguments: none
         * Return:    none
         * Comments:  none
         */          
        void ClearField();

        /*
         * Method:    StreamingStart()
         * Purpose:   Notify the live window that it must restart the
         *            streaming
         * Arguments: none
         * Return:    none
         * Comments:  none
         */          
        void StreamingStart();
                
        /*
         * Method:    StreamingStop()
         * Purpose:   Notify the live window that it must stop the
         *            streaming
         * Arguments: none
         * Return:    none
         * Comments:  none
         */          
        void StreamingStop();             

    private: // data

        // handle to the camera
        tPvHandle        iHandle;
        // set to true when the camera is read only
        bool             iReadOnly;
        // main sizer
        wxBoxSizer*      iMain;
        // tree widget    
        wxTreeListCtrl*  iTree;
        // panel widget
        wxPanel*         iPanel;
        // size to be used within the panel
        wxBoxSizer*      iSizer;
        // number of items placed in the sizer
        int              iCount;
        // root item in the tree
        wxTreeItemId     iRoot;
        // timer for refreshing the attributes
        wxTimer*         iTimer;
         
        // fields used for attribute edition
        wxButton*        iButton;
        wxStaticText*    iLabel;
        wxSlider*        iSlider;
        wxTextCtrl*      iEntry;
        wxComboBox*      iCombo;
        mmMultiButton*   iValidate;
        mmMultiButton*   iReload;

        // tree item currently selected
        wxTreeItemId     iAttrItem;
        // current attribute info
        tPvAttributeInfo iAttrInfo;
        // current attribute label
        wxString         iAttrLabel;
        // min&max&step when the attribute is an Uint (for the slider)
        tPvUint32        iAttrUintMin;
        tPvUint32        iAttrUintMax;
        tPvFloat32       iAttrUintStep;
        // min&max when the attribute is an Float
        tPvFloat32       iAttrFloatMin;
        tPvFloat32       iAttrFloatMax;
        // flag use to indicate when any change to the currently
        // selected attribute will result into a streaming stop/restart
        bool             iNeedRestart;

        // bitmaps used with the mmMultiButton
        wxBitmap*        iBmpVal;
        wxBitmap*        iBmpRld;

        // flag used to indicate when the entry field is changed
        // as the result of a slider action
        bool             iSliding;

        // live window
        PChildWindow*    iLiveWnd;
            
};
