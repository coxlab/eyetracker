/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         CtrlWindow.cpp
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Implement the window that display the camera controls
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

#include <CtrlWindow.h>

//===== BITMAPS ===============================================================

#include <bitmap2.xpm>
#include <bitmap5.xpm>
#include <bitmap6.xpm>

//===== DEFINES ===============================================================

enum
{
    ID_VALIDATE = 1,
    ID_RELOAD,
    ID_SLIDER,
    ID_ENTRY,
    ID_COMMAND,
    ID_COMBO
};

//===== CONSTANTS =============================================================

// standard size of the window
const int kInitWidth    = 550;
const int kInitHeight   = 400;
// extra padding (scrollbar width)
const int kPadding      = 16;
// height of the panel
const int kPanelHeight  = 40;
// column ratio
const float kLabelRatio  = 0.7;
const float kValueRatio  = 1 - kLabelRatio;

// attributes refresh interval (ms) in read/write mode
const int kRefreshIntervalRW = 350;
// attributes refresh interval (ms) in read only mode
const int kRefreshIntervalRO = 1000;

// Event used to Stop&restart live streaming by sending them to the live
// window (aka FinderWindow)
const int kEvnLiveStart = 0xC;
const int kEvnLiveStop  = 0xD;

//===== LOCAL DATA ============================================================

//===== EVENTS TABLE ==========================================================

BEGIN_EVENT_TABLE(CCtrlWindow, PChildWindow)
    EVT_SIZE(CCtrlWindow::OnSize)
    EVT_TIMER(wxID_ANY,CCtrlWindow::OnTimer)
    EVT_TREE_SEL_CHANGED(wxID_ANY,CCtrlWindow::OnSelection)
    EVT_BUTTON(wxID_ANY,CCtrlWindow::OnButtonPushed)
    EVT_COMMAND_SCROLL(ID_SLIDER,CCtrlWindow::OnSliderScrolled)
    EVT_TEXT(ID_ENTRY,CCtrlWindow::OnEntryChanged)
    EVT_TEXT_ENTER(ID_ENTRY,CCtrlWindow::OnEnterPressed)
END_EVENT_TABLE()

//===== CLASS DEFINITION ======================================================

/*
 * Method:    CCtrlWindow()
 * Purpose:   constructor
 * Comments:  none
 */
CCtrlWindow::CCtrlWindow(PChildWindowObserver& aObserver,const tPvCameraInfo& aInfo,tPvHandle aHandle,bool aRW)
    : PChildWindow(aObserver,wxT(""),wxSize(kInitWidth,kInitHeight),wxRESIZE_BORDER) , iHandle(aHandle), iReadOnly(!aRW)
{
    wxString lString;

    iNeedRestart = false;
    iSliding     = false;
    iCount       = 0;
    iButton      = NULL;
    iLabel       = NULL;
    iSlider      = NULL;
    iEntry       = NULL;
    iCombo       = NULL;
    iValidate    = NULL;
    iReload      = NULL;
    iLiveWnd     = NULL;

    // built the bitmaps we need
    iBmpVal = new wxBitmap(bitmap5);
    iBmpRld = new wxBitmap(bitmap6);

    if(iBmpVal && iBmpRld)
    {
        // format the title of the window
        lString =  wxString(aInfo.SerialString,wxConvUTF8);
        lString += _T(" (");
        lString += wxString(aInfo.DisplayName,wxConvUTF8);
        if(iReadOnly)
            lString += _T(") - Controls (RO)");
        else
            lString += _T(") - Controls");
        // and set it
        SetTitle(lString);
        // Give it an icon
        SetIcon(wxIcon(bitmap2));
        // center on the screen
        CentreOnScreen(wxBOTH);
        // set the minimum size
        SetMinSize(wxSize(kInitWidth,kInitHeight));
    
        // create the main sizer
        iMain = new wxBoxSizer(wxVERTICAL);
        if(iMain)
        {    
            // then create the tree widget
            #ifndef __WXMAC__
            iTree = new wxTreeListCtrl(this,wxID_ANY,wxDefaultPosition,wxDefaultSize,wxTR_HAS_BUTTONS | wxTR_SINGLE);
            #else
            iTree = new wxTreeListCtrl(this,wxID_ANY,wxDefaultPosition,wxDefaultSize,
                                       wxTR_TWIST_BUTTONS | wxTR_HAS_BUTTONS | wxTR_SINGLE | wxTR_FULL_ROW_HIGHLIGHT);
            #endif
            
            if(iTree)
            {
                // add the columns
                iTree->AddColumn(wxTreeListColumnInfo(_T("Attributes"),0,wxALIGN_LEFT));
                iTree->AddColumn(wxTreeListColumnInfo(_T("Values"),0,wxALIGN_LEFT));
        
                // create the root
                iRoot = iTree->AddRoot(_T("/"));
                // add the tree to the sizer
                iMain->Add(iTree,wxSizerFlags().Proportion(1).Align(wxALIGN_TOP).Expand().Border(wxALL,0));
            }
    
            // then create the panel
            iPanel = new wxPanel(this,wxID_ANY,wxDefaultPosition,wxSize(kInitWidth,kPanelHeight));
            if(iPanel)
            {
                // set the minimum size of the panel
                iPanel->SetMinSize(wxSize(kInitWidth,kPanelHeight));
                // then create a sizer for the panel
                iSizer = new wxBoxSizer(wxHORIZONTAL);
                if(iSizer)
                    iPanel->SetSizer(iSizer);
            
                // add it to the sizer
                iMain->Add(iPanel,wxSizerFlags().Proportion(0).Align(wxALIGN_BOTTOM).Expand().Border(wxALL,0));
            }  
                
            // set the main sizer in the window
            SetSizer(iMain);
            // and make that the sizer adjust its size to the window
            iMain->FitInside(this);
            // finaly we create the timer
            iTimer = new wxTimer(this);
        }
    }
}

/*
 * Method:    ~CCtrlWindow()
 * Purpose:   destructor
 * Comments:  none
 */
CCtrlWindow::~CCtrlWindow()
{
    if(iTree)
    {
        iTree->DeleteChildren(iRoot);
        iTree->DeleteRoot();
    }


    delete iBmpVal;
    delete iBmpRld;
}

/*
 * Method:    OnTimer()
 * Purpose:   called when the timer fires
 * Comments:  none
 */
void CCtrlWindow::OnTimer(wxTimerEvent& aEvent)
{
    TreeRefresh();
    // make sure the UI is refreshed (important when streaming as
    // it use lots of CPU)
    Update();
    UpdateWindowUI(wxUPDATE_UI_RECURSE);
}

/*
 * Method:    OnSelection()
 * Purpose:   called when the user select one of the item from the tree
 * Comments:  none
 */
void CCtrlWindow::OnSelection(wxTreeEvent& aEvent)
{
    if(!iReadOnly)
    {
        wxTreeItemId lItem = aEvent.GetItem();
    
        // if the selected item is a "leaf" in the tree, we
        // try to edit it.
                
        if(lItem.IsOk())
            if(!iTree->GetChildrenCount(lItem))
            {
                // set the item as the one currently selected
                iAttrItem = lItem;
                // and edit it
                EditAttribute();
            }
    }
}

/*
 * Method:    OnButtonPushed()
 * Purpose:   called when the user pressed one of the buttons
 *            field
 * Comments:  none
 */
void CCtrlWindow::OnButtonPushed(wxCommandEvent& aEvent)
{
    switch(aEvent.GetId())
    {
        case ID_VALIDATE:
        case ID_COMMAND:
        {
            ApplyAttribute();
            break;
        }
        case ID_RELOAD:
        {
            ReloadAttribute();
            break;
        }        
        default:
            break;
    }
}

/*
 * Method:    OnSliderScrolled()
 * Purpose:   called when the user use the slider
 * Comments:  none
 */
void CCtrlWindow::OnSliderScrolled(wxScrollEvent& aEvent)
{
    wxString lString;
    int      lPos = aEvent.GetPosition();

    // use the position of the slider to compute the attribute value
    // and format it in a string
    if(lPos == iSlider->GetMax())
        lString.Printf(wxT("%lu"),iAttrUintMax);
    else
    if(lPos == iSlider->GetMin())
        lString.Printf(wxT("%lu"),iAttrUintMin);
    else
        lString.Printf(wxT("%lu"),(tPvUint32)ceil((tPvFloat32)lPos * iAttrUintStep));

    // then set it in the entry field
    iSliding = true;
    iEntry->SetValue(lString);
    iSliding = false;
}

/*
 * Method:    OnEntryChanged()
 * Purpose:   called when the user have changed the
 *            value within the exntry field
 * Comments:  none
 */
void CCtrlWindow::OnEntryChanged(wxCommandEvent& aEvent)
{
    // to avoid for-ever loop, we make sure to only handle this
    // event if change was done directly in the entry field
    if(!iSliding && iSlider && iEntry)
    {
        unsigned long lValue;
        wxString      lString = iEntry->GetValue();

        // try to convert the string into a number
        if(lString.ToULong(&lValue))
        {
            // and update the slider according to the value, but only if the value is
            // in the range
            if(lValue >= iAttrUintMin && lValue <= iAttrUintMax)
                iSlider->SetValue((int)ceil((tPvFloat32)lValue / iAttrUintStep));
        }
    }
}

/*
 * Method:    OnEnterPressed()
 * Purpose:   called when the user pressed the ENTER key in
 *            the entry field
 * Comments:  none
 */
void CCtrlWindow::OnEnterPressed(wxCommandEvent& aEvent)
{
    ApplyAttribute();
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
void CCtrlWindow::OnSize(wxSizeEvent& aEvent)
{
    wxSize lSize = GetClientSize();

    // force the size to update its widget size and position
    iMain->SetDimension(0,0,lSize.GetWidth(),lSize.GetHeight());
    iMain->Layout();
    iSizer->SetDimension(0,0,iPanel->GetSize().GetWidth(),iPanel->GetSize().GetHeight());
   
    if(iTree)
    {
        // then adjust the column
        iTree->SetColumnWidth(0,(lSize.GetWidth() - kPadding) * kLabelRatio);
        iTree->SetColumnWidth(1,(lSize.GetWidth() - kPadding) * kValueRatio);
    }
}

/*
 * Method:    OnOpen()
 * Purpose:   called when the window is open
 * Comments:  none
 */
void CCtrlWindow::OnOpen(wxCommandEvent& aEvent)
{
    TreeFill();
    
    if(iTimer)
    {
        if(iReadOnly)
            iTimer->Start(kRefreshIntervalRO);
        else
            iTimer->Start(kRefreshIntervalRW);
    }
}

/*
 * Method:    OnClose()
 * Purpose:   called when the window is been closed
 * Comments:  none
 */
void CCtrlWindow::OnClose(wxCloseEvent& aEvent)
{
    if(iTimer)
        iTimer->Stop();

    PChildWindow::OnClose(aEvent);
}

/*
 * Method:    OnNotification()
 * Purpose:   called when the window is notified of
 *            something
 * Comments:  none
 */
void CCtrlWindow::OnNotification(CNotifyEvent& aEvent)
{
    switch(aEvent.GetEvent())
    {
        case kEvnLiveOpened:
        {
            iLiveWnd = (PChildWindow*)aEvent.GetData();
            break;
        }
        case kEvnLiveClosed:
        {
            iLiveWnd = NULL;
            break;
        }
        default:
            break;
    }
}

/*
 * Method:    TreeFill()
 * Purpose:   Fill the tree with all the attributes
 * Comments:  none
 */  
void CCtrlWindow::TreeFill()
{
    unsigned long   lCount;
    tPvAttrListPtr  lAttrs;
    tPvErr          lErr;

    // retreive the list of all the attributes available for the camera
    if(!(lErr = PvAttrList(iHandle,&lAttrs,&lCount)))
    {
        tPvAttributeInfo lInfo;
        wxString         lLabel;
        wxTreeItemId     lRoot,lItem;
        wxString         lValue;
        wxTreeItemId      lChild;
        wxTreeItemIdValue lCookie;        

        // then loop over each one and insert them
        for(unsigned long i=0;i<lCount;i++)
        {
	   lLabel = wxString(lAttrs[i],wxConvUTF8);

           // retreive its details
           if(!PvAttrInfo(iHandle,lLabel.mb_str(wxConvUTF8),&lInfo))
           {
                // get the root where the attribute should be
                lRoot = PreparePathToAttribute(lInfo.Category);
                if(lRoot.IsOk())
                {
                    lValue.Clear();
                
                    // format the value to be displayed
                    if(FormatAttributeValue(lLabel.mb_str(wxConvUTF8),lInfo,lValue))
                    {
                        // append the item
                        lItem = iTree->AppendItem(lRoot,lLabel);
                        if(lItem.IsOk())
                        {
                            // then add the value in the second column
                            iTree->SetItemText(lItem,1,lValue);
                        }
                    }
                }
           }
        }

        // sort all the children
        iTree->SortChildren(iRoot);
        // then expand the root & select it
        iTree->Expand(iRoot);         
        iTree->SelectItem(iRoot);
        // and expand all its direct children
        lChild = iTree->GetFirstChild(iRoot,lCookie);
        while(lChild.IsOk())
        {
            iTree->Expand(lChild);  
            lChild = iTree->GetNextChild(iRoot,lCookie);
        }                 
    }
    else
    {
        ReportAnError(wxT("Failed to retreive the list of attributes"),lErr);
    }
}

/*
 * Method:    TreeRefresh()
 * Purpose:   Refresh the value of all the volatile attributes
 * Comments:  none
 */
void CCtrlWindow::TreeRefresh()
{   
    if(iReadOnly)
        RefreshChild(iRoot);       
    else     
        RefreshChild(iRoot,ePvFlagVolatile);
}

/*
 * Method:    PreparePathToAttribute()
 * Purpose:   Get the last item on the path (build the path in the tree if necessary)
 * Comments:  none
 */
wxTreeItemId CCtrlWindow::PreparePathToAttribute(const char* aPath)
{
    wxString lPath = wxString(aPath,wxConvUTF8);
    wxString lPart;
    wxTreeItemId lParent = iRoot;
    wxTreeItemId lChild;

    while(lPath.Length())
    {
        lPart = lPath.BeforeFirst('/');
        lPath = lPath.AfterFirst('/');

        if(lPart.Length())
        {
            lChild = SeekChild(lParent,lPart);
            if(!lChild.IsOk())
                lParent = iTree->AppendItem(lParent,lPart);
            else
                lParent = lChild; 
        }
    }
    
    return lParent;     
}

/*
 * Method:    SeekChild()
 * Purpose:   Seek a give child of a tree item
 * Comments:  none
 */ 
wxTreeItemId CCtrlWindow::SeekChild(wxTreeItemId aRoot,const wxString& aLabel)
{
    wxTreeItemId      lChild;
    wxTreeItemIdValue lCookie;

    // get the first child
    lChild = iTree->GetFirstChild(aRoot,lCookie);
    // then loop until we find it
    while(lChild.IsOk())
    {
        if(iTree->GetItemText(lChild) == aLabel)
            break;
        else
            lChild = iTree->GetNextChild(aRoot,lCookie);
    }

    return lChild;
}

/*
 * Method:    SeekPath()
 * Purpose:   Seek a given path of a tree item
 * Comments:  none
 */
wxTreeItemId CCtrlWindow::SeekPath(const wxString& aPath)
{
    if(aPath == wxString(wxT("/")))
        return iRoot;
    else
    {    
        wxString lPath = aPath;
        wxString lPart;
        wxTreeItemId lParent = iRoot;
        wxTreeItemId lChild;
    
    
        while(lPath.Length())
        {
            lPart = lPath.BeforeFirst('/');
            lPath = lPath.AfterFirst('/');
    
            if(lPart.Length())
            {
                lChild = SeekChild(lParent,lPart);
                if(lChild.IsOk())
                    lParent = lChild; 
            }
        }
        
        return lChild;
    }      
}

/*
 * Method:    RefreshChild()
 * Purpose:   Refresh a given child from the tree
 * Comments:  none
 */ 
void CCtrlWindow::RefreshChild(wxTreeItemId aItem,unsigned int aFlag)
{
    // if the child have some children, we will refresh them all
    if(iTree->GetChildrenCount(aItem))
    {
        wxTreeItemId      lChild;
        wxTreeItemIdValue lCookie;
    
        // get the first child
        lChild = iTree->GetFirstChild(aItem,lCookie);
        // then loop over all the children
        while(lChild.IsOk())
        {
            // and call the method recursively
            RefreshChild(lChild,aFlag);
            // then switch to the next children
            lChild = iTree->GetNextChild(aItem,lCookie);
        }        
    }
    else
    {
        tPvAttributeInfo lInfo;
        wxString lLabel = iTree->GetItemText(aItem);

        // retreive its details
        if(!PvAttrInfo(iHandle,lLabel.mb_str(wxConvUTF8),&lInfo))
        {
            wxString lValue ;

            if(!aFlag || lInfo.Flags & aFlag)
            {
                // format the value to be displayed
                FormatAttributeValue(lLabel.mb_str(wxConvUTF8),lInfo,lValue);
                // then update the value in the second column
                iTree->SetItemText(aItem,1,lValue);
            }
        }        
    }
}

/*
 * Method:    RefreshImpacted()
 * Purpose:   Refresh all the attributes that have
 *            been impacted by a change
 * Comments:  none
 */
void CCtrlWindow::RefreshImpacted(const char* aImpact)
{
    wxString lPath;
    wxString lString = wxString(aImpact,wxConvUTF8);

    // parse the string and refresh all the path we found
    // in it
    while(lString.Length())
    {
        lPath = lString.BeforeFirst(',');
        lString = lString.AfterFirst(',');

        if(lPath.Length())
            RefreshPath(lPath);
    }
}

/*
 * Method:    RefreshPath()
 * Purpose:   Refresh all the attributes located
 *            at the path
 * Comments:  none
 */
void CCtrlWindow::RefreshPath(const wxString& aPath)
{
    wxTreeItemId lPath;

    // seek to the end of the path
    lPath = SeekPath(aPath);
    // and refresh it
    if(lPath.IsOk())
        RefreshChild(lPath);    
}

/*
 * Method:    FormatAttributeValue()
 * Purpose:   Format the attribute value in a string for display
 * Comments:  none
 */
bool CCtrlWindow::FormatAttributeValue(const char* aLabel,const tPvAttributeInfo &aInfo,wxString& aString)
{
    bool lRet = true;

    /*
    if(PvAttrIsAvailable(iHandle,aLabel))
    {
        aString = "unavailable";
        return true;        
    }
    */

    // if the attribute cannot be read, we will display
    // a special string instead of it's value
    if(!(aInfo.Flags & ePvFlagRead))
    {
        aString = wxT("N/A");
        return true;
    }

    // else we will format the value according to the type of the attribute
    switch(aInfo.Datatype)
    {
        case ePvDatatypeUnknown:
        case ePvDatatypeCommand:
        case ePvDatatypeRaw:
            break;
        case ePvDatatypeString:
        {
            char lValue[256];

            if(!PvAttrStringGet(iHandle,aLabel,lValue,256,NULL))
	        aString = wxString(lValue,wxConvUTF8);
            else
                lRet = false;

            break;
        }
        case ePvDatatypeEnum:
        {
            char lValue[256];

            if(!PvAttrEnumGet(iHandle,aLabel,lValue,256,NULL))
                aString = wxString(lValue,wxConvUTF8);
            else
                lRet = false;

            break;
        }
        case ePvDatatypeUint32:
        {
            tPvUint32 lValue;

            if(!PvAttrUint32Get(iHandle,aLabel,&lValue))
  	        aString.Printf(wxT("%lu"),lValue);
            else
                lRet = false;

            break;
        }
        case ePvDatatypeFloat32:
        {
            tPvFloat32 lValue;

            if(!PvAttrFloat32Get(iHandle,aLabel,&lValue))
	        aString.Printf(wxT("%.3g"),lValue);
            else
                lRet = false;
                          
            break;
        }
        default:
        {
	    aString = wxT("");
            break;
        }
    }

    return lRet;
}

/*
 * Method:    EditAttribute()
 * Purpose:   edit a given attribute (if possible)
 * Comments:  none
 */   
void CCtrlWindow::EditAttribute()
{
    tPvErr   lErr;

    // clear the field
    ClearField();
    // get the attribute label
    iAttrLabel = iTree->GetItemText(iAttrItem);
    // retreive details on the attribute
    if(!(lErr = PvAttrInfo(iHandle,iAttrLabel.mb_str(wxConvUTF8),&iAttrInfo)))
    {
        // only attribute that can bet write to and command will have an edit
        // field
        if((iAttrInfo.Flags & ePvFlagWrite || iAttrInfo.Datatype == ePvDatatypeCommand) &&
            !PvAttrIsAvailable(iHandle,iAttrLabel.mb_str(wxConvUTF8)))
        {
            if(!SetupField())
                ReportAnError(_T("The edition field couldn't be created"));
            else
            {
                // if the attribute have an impact on the streaming, we may need to
                // stop and restart the streaming
                if(iAttrInfo.Impact)
                {
		    wxString lString = wxString(iAttrInfo.Impact,wxConvUTF8);
                    iNeedRestart = lString.Find(_T("/Image")) != -1 || lString == wxString(wxT("/"));
                }
            }
        }
    }
    else
        ReportAnError(_T("Failed to get info on the attribute"),lErr);
}

/*
 * Method:    ApplyAttribute()
 * Purpose:   apply the attribute change
 * Comments:  none
 */
void CCtrlWindow::ApplyAttribute()
{
    tPvErr lErr = ePvErrSuccess;

    // if we are streaming from the camera and that
    // a restart of the stream is necessary, we'll stop
    // the streaming
    if(iLiveWnd && iNeedRestart)
        StreamingStop();

    switch(iAttrInfo.Datatype)
    {
        case ePvDatatypeEnum:
        {
            wxString lValue = iCombo->GetValue();

            lErr = PvAttrEnumSet(iHandle,iAttrLabel.mb_str(wxConvUTF8),lValue.mb_str(wxConvUTF8));
        
            break;
        }
        case ePvDatatypeUint32:
        {
            wxString      lString = iEntry->GetValue();
            unsigned long lValue;
            
            // try to convert the string into a number
            if(lString.ToULong(&lValue))
            {
                // check that the value is within the accepted range
                if(lValue >= iAttrUintMin && lValue <= iAttrUintMax)
                {
                    // then write the value in the attribute
                    lErr = PvAttrUint32Set(iHandle,iAttrLabel.mb_str(wxConvUTF8),lValue);
                }
                else
                    ReportAnError(_T("Value is out of range!"));
            }            
        
            break;
        }        
        case ePvDatatypeFloat32:
        {
            wxString   lString = iEntry->GetValue();
            double     lValue;
            
            // try to convert the string into a number
            if(lString.ToDouble(&lValue))
            {
                // check that the value is within the accepted range
                if(lValue >= iAttrFloatMin && lValue <= iAttrFloatMax)
                {
                    // then write the value in the attribute
                    lErr = PvAttrFloat32Set(iHandle,iAttrLabel.mb_str(wxConvUTF8),(tPvFloat32)lValue);
                }
                else
                    ReportAnError(_T("Value is out of range!"));
            }            
        
            break;
        }        
        case ePvDatatypeCommand:
        {
            lErr = PvCommandRun(iHandle,iAttrLabel.mb_str(wxConvUTF8));

            if(lErr)
	        ReportAnError(wxT("Failed to run the command"),lErr);            
        
            break;    
        }     
        case ePvDatatypeString:
        {
            wxString lValue = iEntry->GetValue();

            lErr = PvAttrStringSet(iHandle,iAttrLabel.mb_str(wxConvUTF8),lValue.mb_str(wxConvUTF8));
                        
            break;      
        }
        default:
            break;     
    }

    // and restart the streaming if necessary
    if(iLiveWnd && iNeedRestart)
        StreamingStart();

    if(!lErr)
    {
        // we need to refresh the attribute in the tree
        RefreshChild(iAttrItem);
        // and also refresh any impacts the change may have add on other attributes
        RefreshImpacted(iAttrInfo.Impact);
    }
    else
        ReportAnError(_T("Failed to write to the attribute"),lErr);
}

/*
 * Method:    ReloadAttribute()
 * Purpose:   reload the attribute change
 * Comments:  none
 */
void CCtrlWindow::ReloadAttribute()
{
    // first refresh the attribute in the tree
    RefreshChild(iAttrItem);
    // then we update the field according to the attribute type
    switch(iAttrInfo.Datatype)
    {
        case ePvDatatypeEnum:
        {
            char   lRange[256];
            char   lValue[32];
            tPvErr lErr;
    
            // retreive the range and the value of the attribute
            if(!(lErr = PvAttrRangeEnum(iHandle,iAttrLabel.mb_str(wxConvUTF8),lRange,256,NULL)) &&
               !(lErr = PvAttrEnumGet(iHandle,iAttrLabel.mb_str(wxConvUTF8),lValue,32,NULL)))
            {
                wxString lStrRange,lStrItem;
                wxArrayString lArray;
            
                // parse the range string to extract all the possible values and put
                // then in an array to be passed to the combobox
                lStrRange = wxString(lRange,wxConvUTF8);
                while(lStrRange.Length())
                {
                    lStrItem  = lStrRange.BeforeFirst(',');
                    lStrRange = lStrRange.AfterFirst(',');
            
                    if(lStrItem.Length())
                        lArray.Add(lStrItem);           
                }

                // replace the possible choice
                iCombo->Clear();
                iCombo->Append(lArray);
                // set the value
                iCombo->SetValue(wxString(lValue,wxConvUTF8));

             }
             else
	         ReportAnError(wxT("Failed to reload the attribute"),lErr);
        
            break;
        }
        case ePvDatatypeUint32:
        {
            // first, we need to retreive the min&max&value of the attribute
            tPvUint32 lValue;
            tPvUint32 lMin,lMax;
            tPvErr    lErr;
    
            // retreive the range and the value
            if(!(lErr = PvAttrRangeUint32(iHandle,iAttrLabel.mb_str(wxConvUTF8),&lMin,&lMax)) &&
               !(lErr = PvAttrUint32Get(iHandle,iAttrLabel.mb_str(wxConvUTF8),&lValue)))
            {
                int      lRangeMin,lRangeMax,lPos;
                wxString lString;

                // keep the min&max for the attribute
                iAttrUintMin = lMin;
                iAttrUintMax = lMax;

                // then we compute the min&max&step to be used on the slider
                if(lMax - lMin> 0xFFFF)
                {
                    lRangeMin      = 0;
                    lRangeMax      = 0xFFFF;
                    iAttrUintStep  = (tPvFloat32)(lMax - lMin) / (tPvFloat32)0x10000;
                }
                else
                {
                    iAttrUintStep  = 1;
                    lRangeMin      = lMin;
                    lRangeMax      = lMax;
                }

                // and the current position of the slider according to the attribute value
                lPos = (int)ceil((tPvFloat32)lValue / iAttrUintStep);
                // the put the current value in a string to be display in the entry field
                lString.Printf(wxT("%lu"),lValue);
                            
                // then update the widgets
                iSlider->SetRange(lRangeMin,lRangeMax);
                iSlider->SetValue(lPos);
                iSliding = true;
                iEntry->SetValue(lString);
                iSliding = false;
            }
            else
	      ReportAnError(wxT("Failed to reload the attribute"),lErr);
        
            break;
        }
        case ePvDatatypeFloat32:
        {
            tPvFloat32 lValue;
            tPvErr lErr;

            // retreive the min&max&value of the attribute
            if(!(lErr = PvAttrRangeFloat32(iHandle,iAttrLabel.mb_str(wxConvUTF8),&iAttrFloatMin,&iAttrFloatMax)) &&
               !(lErr = PvAttrFloat32Get(iHandle,iAttrLabel.mb_str(wxConvUTF8),&lValue)))
            {
                wxString lString;

                // the put the current value in a string to be display in the entry field
                lString.Printf(wxT("%.3f"),lValue);
                // and update the entry field
                iEntry->SetValue(lString);
            }
            else
	        ReportAnError(wxT("Failed to reload the attribute"),lErr);
        
            break;
        }
        case ePvDatatypeString:
        {
            char   lValue[256];
            tPvErr lErr;
    
            // retreive the range and the value of the attribute
            if(!(lErr = PvAttrStringGet(iHandle,iAttrLabel.mb_str(wxConvUTF8),lValue,256,NULL)))
            {
	        wxString lString = wxString(lValue,wxConvUTF8);

                // update the entry field
                iEntry->SetValue(lString);
             }
             else
	        ReportAnError(wxT("Failed to reload the attribute"),lErr);
                         
            break;   
        }
        default:
            break;        
    }
}

/*
 * Method:    SetupField()
 * Purpose:   setup the edition field for a given attribute
 * Comments:  none
 */  
bool CCtrlWindow::SetupField()
{
    bool lRet = true;
    
    switch(iAttrInfo.Datatype)
    {
        case ePvDatatypeEnum:
        {
            char lRange[256];
            char lValue[32];
    
            // retreive the range and the value of the attribute
            if(!(PvAttrRangeEnum(iHandle,iAttrLabel.mb_str(wxConvUTF8),lRange,256,NULL)) &&
                !(PvAttrEnumGet(iHandle,iAttrLabel.mb_str(wxConvUTF8),lValue,32,NULL)))
            {
                wxString lStrRange,lStrItem;
                wxArrayString lArray;
            
                // parse the range string to extract all the possible values and put
                // then in an array to be passed to the combobox
                lStrRange = wxString(lRange,wxConvUTF8);
                while(lStrRange.Length())
                {
                    lStrItem  = lStrRange.BeforeFirst(',');
                    lStrRange = lStrRange.AfterFirst(',');
            
                    if(lStrItem.Length())
                        lArray.Add(lStrItem);           
                }
            
                // create all the widget we need to the field
                iLabel    = new wxStaticText(iPanel,wxID_ANY,iAttrLabel);
                #ifdef __WXMAC__
                iCombo    = new wxComboBox(iPanel,ID_COMBO,wxString(lValue,wxConvUTF8),wxDefaultPosition,wxSize(200,22),
                                           lArray,wxCB_READONLY | wxCB_SORT);                                     
                #else
                iCombo    = new wxComboBox(iPanel,ID_COMBO,wxString(lValue,wxConvUTF8),wxDefaultPosition,wxSize(200,20),
                                           lArray,wxCB_READONLY | wxCB_SORT);        
                #endif                                           
                iValidate = new mmMultiButton(iPanel,ID_VALIDATE,wxEmptyString,*iBmpVal,
                                              wxDefaultPosition,wxSize(20,20),mmMB_NO_AUTOSIZE);
                iReload   = new mmMultiButton(iPanel,ID_RELOAD,wxEmptyString,*iBmpRld,
                                              wxDefaultPosition,wxSize(20,20),mmMB_NO_AUTOSIZE);
                                              
                if(iLabel && iCombo && iValidate && iReload)
                {                
                    // then add them to the sizer
                    iSizer->Add(0, 0, 1, wxCENTRE);
                    iSizer->Add(iLabel,0,wxCENTRE | wxLEFT,2);
                    iSizer->Add(iCombo,0,wxCENTRE | wxLEFT | wxRIGHT,2);
                    iSizer->Add(iValidate,0,wxCENTRE | wxLEFT | wxRIGHT,2);
                    iSizer->Add(iReload,0,wxCENTRE);
                    iSizer->Add(0, 0, 1, wxCENTRE);
        
                    // and ask the sizer to recompute its layout
                    iSizer->Layout();
                    // set how many items were placed on the sizer
                    iCount = 6;
                }
                else
                {
                    delete iLabel;
                    delete iCombo;
                    delete iValidate;
                    delete iReload;

                    iLabel    = NULL;
                    iCombo    = NULL;
                    iValidate = NULL;
                    iReload   = NULL;
                    
                    lRet = false;
                }                
            }
            else
                lRet = false;
        
            break;
        }
        case ePvDatatypeUint32:
        {
            // first, we need to retreive the min&max&value of the attribute
            tPvUint32 lValue;
            tPvUint32 lMin,lMax;
    
            // retreive the range
            if(!(PvAttrRangeUint32(iHandle,iAttrLabel.mb_str(wxConvUTF8),&lMin,&lMax)) &&
               !(PvAttrUint32Get(iHandle,iAttrLabel.mb_str(wxConvUTF8),&lValue)))
            {
                int      lRangeMin,lRangeMax,lPos;
                wxString lString;

                // keep the min&max for the attribute
                iAttrUintMin = lMin;
                iAttrUintMax = lMax;

                // then we compute the min&max&step to be used on the slider
                if(lMax - lMin> 0xFFFF)
                {
                    lRangeMin      = 0;
                    lRangeMax      = 0xFFFF;
                    iAttrUintStep  = (tPvFloat32)(lMax - lMin) / (tPvFloat32)0x10000;
                }
                else
                {
                    iAttrUintStep  = 1;
                    lRangeMin      = lMin;
                    lRangeMax      = lMax;
                }

                // and the current position of the slider according to the attribute value
                lPos = (int)ceil((tPvFloat32)lValue / iAttrUintStep);
                // the put the current value in a string to be display in the entry field
                lString.Printf(wxT("%lu"),lValue);

                // create all the widget we need to the field
                iLabel    = new wxStaticText(iPanel,wxID_ANY,iAttrLabel);
                iSlider   = new wxSlider(iPanel,ID_SLIDER,lPos,lRangeMin,
                                         lRangeMax,wxDefaultPosition,wxSize(180,20));
                iEntry    = new wxTextCtrl(iPanel,ID_ENTRY,lString,wxDefaultPosition,
                                           wxSize(120,20),wxTE_RIGHT|wxTE_PROCESS_ENTER,wxTextValidator(wxFILTER_NUMERIC));
                iValidate = new mmMultiButton(iPanel,ID_VALIDATE,wxEmptyString,*iBmpVal,
                                              wxDefaultPosition,wxSize(20,20),mmMB_NO_AUTOSIZE);
                iReload   = new mmMultiButton(iPanel,ID_RELOAD,wxEmptyString,*iBmpRld,
                                              wxDefaultPosition,wxSize(20,20),mmMB_NO_AUTOSIZE);
                                              
                if(iLabel && iSlider && iEntry && iValidate && iReload)
                {
                    // then add them to the sizer
                    iSizer->Add(0, 0, 1, wxCENTRE);
                    iSizer->Add(iLabel,0,wxCENTRE | wxLEFT,2);
                    iSizer->Add(iSlider,0,wxCENTRE | wxLEFT | wxRIGHT,2);
                    iSizer->Add(iEntry,0,wxCENTRE | wxLEFT | wxRIGHT,2);
                    iSizer->Add(iValidate,0,wxCENTRE | wxLEFT | wxRIGHT,2);
                    iSizer->Add(iReload,0,wxCENTRE);
                    iSizer->Add(0, 0, 1, wxCENTRE);
    
                    // and ask the sizer to recompute its layout
                    iSizer->Layout();
                    // set how many items were placed on the sizer
                    iCount = 7;                
                }
                else
                {
                    delete iLabel;
                    delete iSlider;
                    delete iEntry;
                    delete iValidate;
                    delete iReload;

                    iLabel    = NULL;
                    iSlider   = NULL;
                    iEntry    = NULL;
                    iValidate = NULL;
                    iReload   = NULL;
                    
                    lRet = false;
                }
            }
            else
                lRet = false;
        
            break;
        }        
        case ePvDatatypeFloat32:
        {
            // first, we need to retreive the min&max&value of the attribute
            tPvFloat32 lValue;
            
            // retreive the range
            if(!(PvAttrRangeFloat32(iHandle,iAttrLabel.mb_str(wxConvUTF8),&iAttrFloatMin,&iAttrFloatMax)) &&
               !(PvAttrFloat32Get(iHandle,iAttrLabel.mb_str(wxConvUTF8),&lValue)))
            {
                wxString lString;

                // the put the current value in a string to be display in the entry field
                lString.Printf(wxT("%.3f"),lValue);

                // create all the widget we need to the field
                iLabel    = new wxStaticText(iPanel,wxID_ANY,iAttrLabel);
                iEntry    = new wxTextCtrl(iPanel,ID_ENTRY,lString,wxDefaultPosition,
                                           wxSize(200,20),wxTE_RIGHT|wxTE_PROCESS_ENTER,wxTextValidator(wxFILTER_NUMERIC));
                iValidate = new mmMultiButton(iPanel,ID_VALIDATE,wxEmptyString,*iBmpVal,
                                              wxDefaultPosition,wxSize(20,20),mmMB_NO_AUTOSIZE);
                iReload   = new mmMultiButton(iPanel,ID_RELOAD,wxEmptyString,*iBmpRld,
                                              wxDefaultPosition,wxSize(20,20),mmMB_NO_AUTOSIZE);
                                              
                if(iLabel && iEntry && iValidate && iReload)
                {
                    // then add them to the sizer
                    iSizer->Add(0, 0, 1, wxCENTRE);
                    iSizer->Add(iLabel,0,wxCENTRE | wxLEFT,2);
                    iSizer->Add(iEntry,0,wxCENTRE | wxLEFT | wxRIGHT,2);
                    iSizer->Add(iValidate,0,wxCENTRE | wxLEFT | wxRIGHT,2);
                    iSizer->Add(iReload,0,wxCENTRE);
                    iSizer->Add(0, 0, 1, wxCENTRE);
    
                    // and ask the sizer to recompute its layout
                    iSizer->Layout();
                    // set how many items were placed on the sizer
                    iCount = 6;                
                }
                else
                {
                    delete iLabel;
                    delete iEntry;
                    delete iValidate;
                    delete iReload;

                    iLabel    = NULL;
                    iEntry    = NULL;
                    iValidate = NULL;
                    iReload   = NULL;
                    
                    lRet = false;
                }
            }
            else
                lRet = false;
        
            break;
        }        
        case ePvDatatypeCommand:
        {
            // create the button
            iButton = new wxButton(iPanel,ID_COMMAND,iAttrLabel);
            if(iButton)
            {
                // add the button to the sizer (make it centered)
                iSizer->Add(0, 0, 1, wxCENTRE);
                iSizer->Add(iButton,1,wxCENTRE);
                iSizer->Add(0, 0, 1, wxCENTRE);
                // and ask the sizer to recompute its layout
                iSizer->Layout();
                // set how many items were placed on the sizer
                iCount = 3;
            }
            else
                lRet = false;
            
            break;    
        }        
        case ePvDatatypeString:
        {
            char lValue[256];
    
            // retreive the range and the value of the attribute
            if(!(PvAttrStringGet(iHandle,iAttrLabel.mb_str(wxConvUTF8),lValue,256,NULL)))
            {
	        wxString lString = wxString(lValue,wxConvUTF8);

                // create all the widget we need to the field
                iLabel    = new wxStaticText(iPanel,wxID_ANY,iAttrLabel);
                iEntry    = new wxTextCtrl(iPanel,ID_ENTRY,lString,wxDefaultPosition,
                                           wxSize(200,20),wxTE_RIGHT|wxTE_PROCESS_ENTER,wxTextValidator());
                iValidate = new mmMultiButton(iPanel,ID_VALIDATE,wxEmptyString,*iBmpVal,
                                              wxDefaultPosition,wxSize(20,20),mmMB_NO_AUTOSIZE);
                iReload   = new mmMultiButton(iPanel,ID_RELOAD,wxEmptyString,*iBmpRld,
                                              wxDefaultPosition,wxSize(20,20),mmMB_NO_AUTOSIZE);
                                              
                if(iLabel && iEntry && iValidate && iReload)
                {
                    // then add them to the sizer
                    iSizer->Add(0, 0, 1, wxCENTRE);
                    iSizer->Add(iLabel,0,wxCENTRE | wxLEFT,2);
                    iSizer->Add(iEntry,0,wxCENTRE | wxLEFT | wxRIGHT,2);
                    iSizer->Add(iValidate,0,wxCENTRE | wxLEFT | wxRIGHT,2);
                    iSizer->Add(iReload,0,wxCENTRE);
                    iSizer->Add(0, 0, 1, wxCENTRE);
    
                    // and ask the sizer to recompute its layout
                    iSizer->Layout();
                    // set how many items were placed on the sizer
                    iCount = 6;                
                }
                else
                {
                    delete iLabel;
                    delete iEntry;
                    delete iValidate;
                    delete iReload;

                    iLabel    = NULL;
                    iEntry    = NULL;
                    iValidate = NULL;
                    iReload   = NULL;
                    
                    lRet = false;
                }
            }
            else
                lRet = false;            
            
            
            break;   
        }
        default:
            lRet = false;      
    }
    
    return lRet;
}

/*
 * Method:    ClearField()
 * Purpose:   remove the edition field (if any)
 * Arguments: none
 * Return:    none
 * Comments:  none
 */    
void CCtrlWindow::ClearField()
{
    // loop over all the item in the sizer and detach them
    for(int i=iCount - 1;i>=0;i--)
        iSizer->Detach(i);

    // then delete the widgets
    if(iButton)
    {
        iButton->Destroy();
        iButton = NULL;
    }
    if(iLabel)
    {
        iLabel->Destroy();
        iLabel = NULL;
    }
    if(iSlider)
    {
        iSlider->Destroy();
        iSlider = NULL;
    }
    if(iEntry)
    {
        iEntry->Destroy();
        iEntry = NULL;
    }
    if(iCombo)
    {
        iCombo->Destroy();
        iCombo = NULL;
    }    
    if(iValidate)
    {
        iValidate->Destroy();
        iValidate = NULL;
    }
    if(iReload)
    {
        iReload->Destroy();
        iReload = NULL;
    }                     

    // and recompute the layout
    iSizer->Layout();

    // reset the count
    iCount = 0;
}

/*
 * Method:    StreamingStart()
 * Purpose:   Notify the live window that it must restart the
 *            streaming
 * Comments:  none
 */
void CCtrlWindow::StreamingStart()
{
    iLiveWnd->Notify(kEvnLiveStart,NULL,true);
}

/*
 * Method:    StreamingStop()
 * Purpose:   Notify the live window that it must stop the
 *            streaming
 * Comments:  none
 */
void CCtrlWindow::StreamingStop()
{
    iLiveWnd->Notify(kEvnLiveStop,NULL,true);
}
