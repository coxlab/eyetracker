/*
| ==============================================================================
| Copyright (C) 2006-2008 Prosilica.  All Rights Reserved.
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

#include <PvApi.h>
#include <MainWindow.h>
#include <ChildWindow.h>
#include <InfoWindow.h>
#include <FinderWindow.h>
#include <CtrlWindow.h>

#include <wx/event.h>
#include <wx/menu.h>
#include <wx/msgdlg.h>
#include <wx/toolbar.h>
#include <wx/treectrl.h>
#include <wx/sizer.h>
#include <wx/string.h>
#include <wx/textdlg.h>
#include <wx/progdlg.h>

#ifndef __WXMSW__
#include <arpa/inet.h>
#endif

#include <Tools.h>

//===== BITMAPS ===============================================================

#include <bitmap1.xpm>
#include <bitmap2.xpm>
#include <bitmap3.xpm>
#include <bitmap7.xpm>
#include <bitmap8.xpm>
#include <SampleViewer.xpm>

//===== DEFINES ===============================================================

enum
{
    ID_QUIT     = 1,
    ID_ABOUT,
    ID_INFO,
    ID_CTRL,
    ID_LIVE,
    ID_SEEK,
    ID_EXPO,
    ID_RAISE,
    ID_CLOSE,
    ID_WINDOW // must alway be the last one
};

#define dMAINWINDOW wxID_HIGHEST + 1
#define dSEEKER     dMAINWINDOW  + 1

//===== EVENTS DEF. ===========================================================

BEGIN_DECLARE_EVENT_TYPES()
    DECLARE_EVENT_TYPE(dOPENING,wxID_ANY)
END_DECLARE_EVENT_TYPES()

DEFINE_EVENT_TYPE(dOPENING)
DEFINE_EVENT_TYPE(wxEVT_LINK)
DEFINE_EVENT_TYPE(wxEVT_ERROR)

typedef void (wxEvtHandler::*wxLinkEventFunction)(CLinkEvent&);

#define EVT_LINK(id,fn) \
    DECLARE_EVENT_TABLE_ENTRY( wxEVT_LINK, id, -1, \
    (wxObjectEventFunction) (wxEventFunction) (wxCommandEventFunction) (wxNotifyEventFunction) \
    wxStaticCastEvent( wxLinkEventFunction, & fn ), (wxObject *) NULL ),

typedef void (wxEvtHandler::*wxErrorEventFunction)(CErrorEvent&);

#define EVT_ERROR(id,fn) \
    DECLARE_EVENT_TABLE_ENTRY( wxEVT_ERROR, id, -1, \
    (wxObjectEventFunction) (wxEventFunction) (wxCommandEventFunction) (wxNotifyEventFunction) \
    wxStaticCastEvent( wxErrorEventFunction, & fn ), (wxObject *) NULL ),

//===== CONSTANTS =============================================================

// UI refresh interval (ms)
const int kRefreshInterval    = 500;
// maximum number of cameras we expect to see when listing all cameras visible
const int kMaxPossibleCameras = 30;

//===== LOCAL DATA ============================================================

const wchar_t* gMainWindowTitle = L"SampleViewer";

//===== EVENTS TABLE ==========================================================

BEGIN_EVENT_TABLE(CMainWindow, wxFrame)
#ifdef __WXMAC__
    EVT_MENU(wxID_EXIT,CMainWindow::OnQuit)
    EVT_MENU(wxID_ABOUT,CMainWindow::OnAbout)
#else
    EVT_MENU(ID_QUIT, CMainWindow::OnQuit)
    EVT_MENU(ID_ABOUT, CMainWindow::OnAbout)
    EVT_MENU(ID_RAISE, CMainWindow::OnRaiseAll)
    EVT_MENU(ID_CLOSE, CMainWindow::OnCloseAll)
#endif    
    EVT_CLOSE(CMainWindow::OnClose)
    EVT_COMMAND(dMAINWINDOW,dOPENING,CMainWindow::OnOpen)
    EVT_MENU_RANGE(ID_INFO, ID_EXPO,CMainWindow::OnToolClick)
    EVT_LINK(dMAINWINDOW,CMainWindow::OnLinkEvent)
    EVT_ERROR(dMAINWINDOW,CMainWindow::OnErrorEvent)
    EVT_WORKER(dSEEKER,CMainWindow::OnSeekerEvent)
    EVT_MENU(wxID_ANY,CMainWindow::OnRaiseOne) // <!> must be last
END_EVENT_TABLE()

//===== CLASS DEFINITION ======================================================

class CTreeItemData : public wxTreeItemData
{
    public:

        CTreeItemData();

    public: // data

        // camera info
        tPvCameraInfo  iData;
        // handle to the camera (when opened)
        tPvHandle      iHandle;
        // have we open the camera as master?
        bool           iOwner;
        // info window
        CInfoWindow*   iInfo;
        // finder window
        CFinderWindow* iFinder;
        // control window
        CCtrlWindow*   iCtrl;
};

//===== CLASS IMPLEMENTATION ==================================================

CTreeItemData::CTreeItemData()
{
    memset(&iData,0,sizeof(tPvCameraInfo));
    iHandle = NULL;
    iInfo   = NULL;
    iFinder = NULL;
    iCtrl   = NULL;
}

/*
 * Method:    CLinkEvent()
 * Purpose:   constructor
 * Comments:  none
 */
CLinkEvent::CLinkEvent(tPvLinkEvent aEvent,unsigned long aUniqueId)
    : wxNotifyEvent(wxEVT_LINK,dMAINWINDOW)
{
    iEvent      = aEvent;
    iUniqueId   = aUniqueId;
}

/*
 * Method:    CLinkEvent()
 * Purpose:   copy constructor
 * Comments:  none
 */
CLinkEvent::CLinkEvent(const CLinkEvent& aEvent)
    : wxNotifyEvent(wxEVT_LINK,dMAINWINDOW)
{
    iEvent      = aEvent.iEvent;
    iUniqueId   = aEvent.iUniqueId;
}

/*
 * Method:    CErrorEvent()
 * Purpose:   constructor
 * Comments:  none
 */
CErrorEvent::CErrorEvent(const wchar_t* aMessage,tPvErr aErr)
    : wxNotifyEvent(wxEVT_ERROR,dMAINWINDOW)
{
    iMessage = aMessage;
    iErr     = aErr;
}

/*
 * Method:    CErrorEvent()
 * Purpose:   copy constructor
 * Comments:  none
 */
CErrorEvent::CErrorEvent(const CErrorEvent& aEvent)
    : wxNotifyEvent(wxEVT_ERROR,dMAINWINDOW)
{
   iMessage = aEvent.iMessage;
   iErr     = aEvent.iErr;
}

/*
 * Method:    CMainWindow()
 * Purpose:   constructor
 * Comments:  none
 */
CMainWindow::CMainWindow()
    : wxFrame(NULL,dMAINWINDOW,gMainWindowTitle,wxDefaultPosition,wxSize(250,350),
              wxMINIMIZE_BOX | wxSYSTEM_MENU | wxCAPTION | wxCLOSE_BOX | wxCLIP_CHILDREN)
{
    // Give it an icon
    SetIcon(wxIcon(SampleViewer));

    iSeeking = NULL;

    iMenuBar = new wxMenuBar;
    if(iMenuBar)
    {
        #ifndef __WXMAC__
        wxMenu* lMenu = new wxMenu;
        if(lMenu)
        {
            lMenu->Append(ID_ABOUT,L"&About ...");
            lMenu->AppendSeparator();
            lMenu->Append(ID_QUIT,L"E&xit");
           
            iMenuBar->Append(lMenu,L"&File");
        }

        iMenuWin = new wxMenu;
        if(iMenuWin)
        {
            iMenuWin->Append(ID_RAISE,L"&Show all");
            iMenuWin->Append(ID_CLOSE,L"&Close all");
            iMenuWin->AppendSeparator();
            iMenuBar->Append(iMenuWin,L"&Windows");

            iMenuWin->Enable(ID_RAISE,false);
            iMenuWin->Enable(ID_CLOSE,false);
        }
        #endif

        SetMenuBar(iMenuBar);
        CreateStatusBar();

        // create the tool barCTreeItemData
        iToolBar = CreateToolBar();
        if(iToolBar)
        {
            // fill the toolbar
            iToolBar->AddTool(ID_INFO,_T("info"),wxBitmap(bitmap1),_T("Information"));
            iToolBar->AddTool(ID_CTRL,_T("ctrl"),wxBitmap(bitmap2),_T("Controls"));
            iToolBar->AddTool(ID_LIVE,_T("live"),wxBitmap(bitmap3),_T("Live view"));
            iToolBar->AddTool(ID_SEEK,_T("seek"),wxBitmap(bitmap7),_T("Seek a camera"));
            iToolBar->AddTool(ID_EXPO,_T("expo"),wxBitmap(bitmap8),_T("Export camera's setup"));
            iToolBar->Realize();
        }

        // creat the cameras tree
        iTree = new wxTreeCtrl(this,wxID_ANY,wxDefaultPosition,wxDefaultSize,wxTR_HAS_BUTTONS | wxTR_SINGLE);
        if(iTree)
            iRoot = iTree->AddRoot(_T("Host"));

        // append a custom event to simuate a post-on-screen event
        wxCommandEvent lEvent(dOPENING,GetId());
        lEvent.SetEventObject(this);
        GetEventHandler()->AddPendingEvent(lEvent);
    }
}

/*
 * Method:    ~CMainWindow()
 * Purpose:   destructor
 * Comments:  none
 */
CMainWindow::~CMainWindow()
{
}

/*
 * Method:    OnChildClosed()
 * Purpose:   called when a child window is been closed
 * Comments:  none
 */
void CMainWindow::OnChildClosed(PChildWindow* aChild)
{
    wxTreeItemId      lChild;
    wxTreeItemIdValue lCookie;
    CTreeItemData*    lData;
    bool              lFound = false;

    // get the first child
    lChild = iTree->GetFirstChild(iRoot,lCookie);
    // then loop over the child in search of the window that
    // was closed
    while(lChild.IsOk() && !lFound)
    {
        lData = (CTreeItemData *)iTree->GetItemData(lChild);

        if(lData->iInfo == aChild)
        {
            lData->iInfo = NULL;
            lFound = true;
        }
        else
        if(lData->iFinder == aChild)
        {
            lData->iFinder = NULL;
            lFound = true;

            // if the control window is still open, we notify it
            // that the live window is a gonner
            if(lData->iCtrl)
                lData->iCtrl->Notify(kEvnLiveClosed,NULL,true);
        }
        else
        if(lData->iCtrl == aChild)
        {
            lData->iCtrl = NULL;
            lFound = true;
        }

        // if all the window are closed  and that we had the camera
        // open, we close it
        if(!lData->iFinder && !lData->iCtrl && lData->iHandle)
        {
            SetStatusText(L"Closing a camera");
            CloseCamera(lData->iHandle);
            lData->iHandle = NULL;
        }

        lChild = iTree->GetNextChild(iRoot,lCookie);
    }

    RefreshWindowsList();
}

/*
 * Method:    OnChildError()
 * Purpose:   called when a child window is reporting an error to the user
 * Comments:  none
 */
void CMainWindow::OnChildError(const wchar_t* aMessage,tPvErr aErr)
{
    // append a custom event
    CErrorEvent lEvent(aMessage,aErr);
    lEvent.SetEventObject(this);
    GetEventHandler()->AddPendingEvent(lEvent);
}

/*
 * Method:    OnOpen()
 * Purpose:   called when the window is open
 * Comments:  none
 */
void CMainWindow::OnOpen(wxCommandEvent& aEvent)
{
    // set the initial status text
    SetStatusText(L"Ready ...");
    // then list all the cameras already plugged
    ListCameras();
}

/*
 * Method:    OnAbout()
 * Purpose:   called when the user select the "About" item from the menu
 * Comments:  none
 */
void CMainWindow::OnAbout(wxCommandEvent& aEvent)
{
    wxString lString;
    unsigned long lMinor,lMajor;

    PvVersion(&lMajor,&lMinor);
    lString = wxString::Format(L"SampleViewer Version %u.%u\nProsilica Inc.\nCopyright (C) 2006-2007",lMajor,lMinor);

    wxMessageBox(lString,
                 L"About SampleViewer",
                 wxOK | wxICON_INFORMATION,this);
}

/*
 * Method:    OnQuit()
 * Purpose:   called when the user select the "Exit" item from the menu
 * Comments:  none
 */
void CMainWindow::OnQuit(wxCommandEvent& aEvent)
{
    Close(true);
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
void CMainWindow::OnClose(wxCloseEvent& aEvent)
{
    if(!iSeeking || (iSeeking && !iSeeking->IsAlive()))
    {
        wxTreeItemId      lChild;
        wxTreeItemIdValue lCookie;
        CTreeItemData*    lData;

        SetStatusText(L"Closing down ...");

        if(iSeeking)
        {
            iSeeking->Wait();
            delete iSeeking;
            iSeeking = NULL;
        }

        // get the first child
        lChild = iTree->GetFirstChild(iRoot,lCookie);
        // then loop over all the
        while(lChild.IsOk())
        {
            lData = (CTreeItemData *)iTree->GetItemData(lChild);

            // if there was some windows associated with that camera, we
            // close them
            if(lData->iInfo)
            {
                lData->iInfo->Close(true);
                lData->iInfo = NULL;
            }
            if(lData->iFinder)
            {
                lData->iFinder->Close(true);
                lData->iFinder = NULL;
            }
            if(lData->iCtrl)
            {
                lData->iCtrl->Close(true);
                lData->iCtrl = NULL;
            }

            lChild = iTree->GetNextChild(iRoot,lCookie);
        }

        Destroy();
    }
}

/*
 * Method:    OnToolClick()
 * Purpose:   called when the user click on of the tools on the
 *            toll bar
 * Comments:  none
 */
void CMainWindow::OnToolClick(wxCommandEvent& aEvent)
{
    wxTreeItemId   lItem = iTree->GetSelection();
  
    if(lItem.IsOk() && lItem != iRoot || aEvent.GetId() == ID_SEEK)
    {
        CTreeItemData* lData = (CTreeItemData *)iTree->GetItemData(lItem);
    
        switch(aEvent.GetId())
        {
            case ID_INFO:
            {
                if(!lData->iInfo)
                {
                    // create the info window
                    CInfoWindow* lWindow = new CInfoWindow(*this,lData->iData);

                    if(lWindow)
                    {
                        // keep a pointer to it
                        lData->iInfo = lWindow;
                        // and show the window
                        lWindow->Show(true);
                    }
                }
                else
                    lData->iInfo->Raise();

                break;
            }
            case ID_CTRL:
            {
                if(!lData->iCtrl)
                {
                    if(!lData->iHandle)
                        lData->iHandle = OpenCamera(lData->iData.UniqueId,lData->iOwner);

                    if(lData->iHandle)
                    {
                        // create the info window
                        CCtrlWindow* lWindow = new CCtrlWindow(*this,lData->iData,lData->iHandle,lData->iOwner);

                        if(lWindow)
                        {
                            // keep a pointer to it
                            lData->iCtrl = lWindow;
                            // and show the window
                            lWindow->Show(true);

                            if(lData->iFinder)
                                lData->iCtrl->Notify(kEvnLiveOpened,lData->iFinder,true);
                        }
                    }
                    else
                    {
                        wxMessageBox(L"Sorry, the camera couldn't be open.",
                                     L"Ooops ...",
                                     wxOK | wxICON_ERROR,this);
                    }
                }
                else
                    lData->iCtrl->Raise();

                break;
            }
            case ID_LIVE:
            {
                if(!lData->iFinder)
                {
                    if(!lData->iHandle)
                        lData->iHandle = OpenCamera(lData->iData.UniqueId,lData->iOwner);

                    if(lData->iHandle)
                    {
                        // create the info window
                        CFinderWindow* lWindow = new CFinderWindow(*this,lData->iData,lData->iHandle);

                        if(lWindow)
                        {
                            // keep a pointer to it
                            lData->iFinder = lWindow;
                            // and show the window
                            lWindow->Show(true);

                            if(lData->iCtrl)
                                lData->iCtrl->Notify(kEvnLiveOpened,lWindow,true);
                        }
                    }
                    else
                    {
                        wxMessageBox(L"Sorry, the camera couldn't be open.",
                                     L"Ooops ...",
                                     wxOK | wxICON_ERROR,this);
                    }
                }
                else
                    lData->iFinder->Raise();
                
                break;      
            }    
            case ID_SEEK:
            {
                wxTextEntryDialog lDialog(this,L"Please enter the IP address of the camera",L"Seek a camera ...",L"0.0.0.0");

                if(lDialog.ShowModal() == wxID_OK)
                {
                    unsigned long lAddr = inet_addr(lDialog.GetValue().mb_str(wxConvUTF8));
                
                    if(lAddr)
                    {
                        iSeeking = new CSeeker(dSEEKER,GetEventHandler(),lAddr);
                        if(iSeeking)
                            if(!iSeeking->Start())
                            {
                                delete iSeeking;
                                iSeeking = NULL;
                            }
                    }
                    else
                        wxMessageBox(L"You need to enter a valid IP address",
                                     L"Ooops ...",
                                     wxOK | wxICON_ERROR,this);
                }

                break;
            }
            case ID_EXPO:
            {
                bool lClose = false;

                if(!lData->iHandle)
                {
                    lData->iHandle = OpenCamera(lData->iData.UniqueId,lData->iOwner);
                    lClose = true;
                }

                if(lData->iHandle)
                {
		  wxFileDialog lDialog(NULL,wxT("Select an output file"),wxT(""),wxString(lData->iData.SerialString,wxConvUTF8),wxT("Text files (*.txt)|*.txt"),wxSAVE | wxOVERWRITE_PROMPT);

                    if(lDialog.ShowModal() == wxID_OK)
                    {
     		        wxString lExt  = wxT(".txt");
                        wxString lPath = lDialog.GetPath();

                        if(!lPath.Contains(lExt))
                            lPath = lPath + lExt;

                        if(!ExportCamera(lData->iHandle,lPath))
			    wxMessageBox(wxT("Camera's setup export failed."),wxT("Ooops ..."),wxOK | wxICON_ERROR,this);
                    }

                    if(lClose)
                    {
                        CloseCamera(lData->iHandle);
                        lData->iHandle = NULL;
                    }
                }

                break;
            }
        }

        // refresh the list of window
        RefreshWindowsList();
        // and force the window to be updated
        Update();
    }
    else
    {
        wxMessageBox(L"You must select a camera first.",
                     L"Ooops ...",
                     wxOK | wxICON_ERROR,this);
    }
}

/*
 * Method:    OnLinkEvent()
 * Purpose:   called when an event occured on the link
 * Comments:  none
 */
void CMainWindow::OnLinkEvent(CLinkEvent& aEvent)
{
    switch(aEvent.GetType())
    {
        case ePvLinkAdd:
        {
            // if we know the camera already no need to continue
            if(!KnownCamera(aEvent.GetUID()))
            {
                CTreeItemData *lItem = new CTreeItemData;

                // update the status text
                SetStatusText(L"A camera was detected ...");

                // then append the new camera to the tree
                if(lItem)
                {
                    // get the info on the camera
                    if(!PvCameraInfo(aEvent.GetUID(),&lItem->iData))
                    {
                        wxString     lString;
                        wxTreeItemId lChild;

                        // make the string to be displayed
                        lString =  wxString(lItem->iData.SerialString,wxConvUTF8);
                        lString += _T(" (");
                        lString += wxString(lItem->iData.DisplayName,wxConvUTF8);
                        lString += _T(")");

                        // then, insert the item
                        lChild = iTree->AppendItem(iRoot,lString,-1,-1,lItem);
                        // and make sure the root is expanded
                        iTree->Expand(iRoot);
                        // and select the newly added item
                        iTree->SelectItem(lChild,true);
                    }
                    else
                        delete lItem;
                }
            }

            break;
        }
        case ePvLinkRemove:
        {
            wxTreeItemId      lChild;
            wxTreeItemIdValue lCookie;
            bool              lFound = false;
            CTreeItemData*    lData;

            SetStatusText(L"A camera was unplugged ...");

            // get the first child
            lChild = iTree->GetFirstChild(iRoot,lCookie);
            // then loop until we either found the camera unplugged or reach the end of the list
            while(!lFound && lChild.IsOk())
            {
                lData = (CTreeItemData *)iTree->GetItemData(lChild);
                lFound = lData->iData.UniqueId == aEvent.GetUID();
                if(!lFound)
                    lChild = iTree->GetNextChild(iRoot,lCookie);
            }

            // if we have found it, we remove it
            if(lFound)
            {
                // if there was some windows associated with that camera, we
                // close them
                if(lData->iInfo)
                    lData->iInfo->Close(true);
                if(lData->iFinder)
                    lData->iFinder->Close(true);
                if(lData->iCtrl)
                    lData->iCtrl->Close(true);

                iTree->Delete(lChild);
            }

            break;
        }
        default:
            break;
    }
}

/*
 * Method:    OnErrorEvent()
 * Purpose:   called when an error occured
 * Comments:  none
 */
void CMainWindow::OnErrorEvent(CErrorEvent& aEvent)
{
    if(!aEvent.GetError())
        wxMessageBox(aEvent.GetMessage(),L"Ooops ...",wxOK | wxICON_ERROR,NULL);
    else
    {
        wxString lMessage = aEvent.GetMessage();

        lMessage += wxT(" : ");
        lMessage += wxString(GetStringForError(aEvent.GetError()),wxConvUTF8);

        wxMessageBox(lMessage,wxT("Ooops ..."),wxOK | wxICON_ERROR,NULL);
    }
}

/*
 * Method:    OnRaiseAll()
 * Purpose:   called when the user select the "Show all" item from the menu
 * Comments:  this will force all the application windows to be raised
 */
void CMainWindow::OnRaiseAll(wxCommandEvent& aEvent)
{
    wxTreeItemId      lChild;
    wxTreeItemIdValue lCookie;
    CTreeItemData*    lData;

    SetStatusText(L"Showing all windows");

    // get the first child
    lChild = iTree->GetFirstChild(iRoot,lCookie);
    // then loop
    while(lChild.IsOk())
    {
        lData = (CTreeItemData *)iTree->GetItemData(lChild);

        if(lData->iInfo)
            lData->iInfo->Raise();
        if(lData->iFinder)
            lData->iFinder->Raise();
        if(lData->iCtrl)
            lData->iCtrl->Raise();

        lChild = iTree->GetNextChild(iRoot,lCookie);
    }
}

/*
 * Method:    OnCloseAll()
 * Purpose:   called when the user select the "Close all" item from the menu
 * Comments:  this will force all the application windows to be closed
 */
void CMainWindow::OnCloseAll(wxCommandEvent& aEvent)
{
    wxTreeItemId      lChild;
    wxTreeItemIdValue lCookie;
    CTreeItemData*    lData;

    SetStatusText(L"Closing all windows");

    // get the first child
    lChild = iTree->GetFirstChild(iRoot,lCookie);
    // then loop
    while(lChild.IsOk())
    {
        lData = (CTreeItemData *)iTree->GetItemData(lChild);

        if(lData->iInfo)
            lData->iInfo->Close(true);
        if(lData->iFinder)
            lData->iFinder->Close(true);
        if(lData->iCtrl)
            lData->iCtrl->Close(true);

        lChild = iTree->GetNextChild(iRoot,lCookie);
    }
}

/*
 * Method:    OnRaiseOne()
 * Purpose:   called when the user select the "Show all" item from the menu
 * Comments:  this will force all the application windows to be raised
 */
void CMainWindow::OnRaiseOne(wxCommandEvent& aEvent)
{
    wxTreeItemId      lChild;
    wxTreeItemIdValue lCookie;
    CTreeItemData*    lData;
    int               lIndex = aEvent.GetId() - ID_WINDOW;
    int               lCount = 0;

    // then we loop over all the windows and add them to the menu
    // get the first child
    lChild = iTree->GetFirstChild(iRoot,lCookie);
    while(lChild.IsOk())
    {
        lData = (CTreeItemData *)iTree->GetItemData(lChild);

        if(lData->iInfo)
        {
            if(lCount == lIndex)
            {
                lData->iInfo->Raise();
                break;
            }
            else
                lCount++;
        }
        if(lData->iFinder)
        {
            if(lCount == lIndex)
            {
                lData->iFinder->Raise();
                break;
            }
            else
                lCount++;
        }
        if(lData->iCtrl)
        {
            if(lCount == lIndex)
            {
                lData->iCtrl->Raise();
                break;
            }
            else
                lCount++;
        }

        lChild = iTree->GetNextChild(iRoot,lCookie);
    }
}

/*
 * Method:    OnSeekerEvent()
 * Purpose:   called when a worker thread sent an event to the window
 * Comments:  none
 */
void CMainWindow::OnSeekerEvent(CWorkerEvent& aEvent)
{
    switch(aEvent.iEvent)
    {
        case kEvnSeekerStarted:
        {
            SetStatusText(L"Seeking camera ...");
            break;
        }
        case kEvnSeekerFinished:
        {
            if(!aEvent.iData)
                wxMessageBox(L"This camera couldn't be contacted",
                             L"Ooops ...",
                             wxOK | wxICON_EXCLAMATION,this);

            break;
        }
    }
}

/*
 * Method:    RefreshWindowsList()
 * Purpose:   refresh the windows list in the menu
 * Comments:  none
 */
void CMainWindow::RefreshWindowsList()
{
    #ifndef __WXMAC__
    wxTreeItemId      lChild;
    wxTreeItemIdValue lCookie;
    CTreeItemData*    lData;
    wxMenuItem*       lItem;
    int               lCount = 0;

    // first we remove the menu items that are not the 3 firsts
    for(int lIndex = iMenuWin->GetMenuItemCount() - 1;lIndex>2;lIndex--)
    {
        lItem = iMenuWin->FindItemByPosition(lIndex);
        iMenuWin->Destroy(lItem);
    }

    // then we loop over all the windows and add them to the menu
    // get the first child
    lChild = iTree->GetFirstChild(iRoot,lCookie);
    while(lChild.IsOk())
    {
        lData = (CTreeItemData *)iTree->GetItemData(lChild);

        if(lData->iInfo)
        {
            iMenuWin->Append(ID_WINDOW + lCount,lData->iInfo->GetTitle());
            lCount++;
        }
        if(lData->iFinder)
        {
            iMenuWin->Append(ID_WINDOW + lCount,lData->iFinder->GetTitle());
            lCount++;
        }
        if(lData->iCtrl)
        {
            iMenuWin->Append(ID_WINDOW + lCount,lData->iCtrl->GetTitle());
            lCount++;
        }

        lChild = iTree->GetNextChild(iRoot,lCookie);
    }

    if(lCount)
    {
        iMenuWin->Enable(ID_RAISE,true);
        iMenuWin->Enable(ID_CLOSE,true);
    }
    else
    {
        iMenuWin->Enable(ID_RAISE,false);
        iMenuWin->Enable(ID_CLOSE,false);
    }
    #endif
}

/*
 * Method:    ListCameras()
 * Purpose:   list all the cameras already visible
 * Comments:  none
 */
void CMainWindow::ListCameras()
{
    tPvCameraInfo   lInfos[kMaxPossibleCameras];
    tPvUint32       lCount;

    // list all the cameras currently connected
    if(PvCameraList(lInfos,kMaxPossibleCameras,&lCount))
    {
        // and loop over all the cameras found and add them to the tree
        for(tPvUint32 lIndex=0;lIndex<lCount;lIndex++)
        {
            CTreeItemData *lItem = new CTreeItemData;

            if(lItem)
            {
                wxString     lString;
                wxTreeItemId lChild;

                // copy the camera info in the tree item
                memcpy(&lItem->iData,&lInfos[lIndex],sizeof(tPvCameraInfo));

                // make the string to be displayed
                lString =  wxString(lItem->iData.SerialString,wxConvUTF8);
                lString += _T(" (");
                lString += wxString(lItem->iData.DisplayName,wxConvUTF8);
                lString += _T(")");

                // then, insert the item
                lChild = iTree->AppendItem(iRoot,lString,-1,-1,lItem);
                // and make sure the root is expanded
                iTree->Expand(iRoot);
                // and select the newly added item
                iTree->SelectItem(lChild,true);
            }
        }
    }
}

/*
 * Method:    KnownCamera()
 * Purpose:   check if a given camera is known (in the tree)
 * Comments:  none
 */
bool CMainWindow::KnownCamera(unsigned int aUID)
{
    wxTreeItemId      lChild;
    wxTreeItemIdValue lCookie;
    bool              lFound = false;
    CTreeItemData*    lData;

    // get the first child
    lChild = iTree->GetFirstChild(iRoot,lCookie);
    // then loop until we either found the camera unplugged or reach the end of the list
    while(!lFound && lChild.IsOk())
    {
        lData = (CTreeItemData *)iTree->GetItemData(lChild);
        lFound = lData->iData.UniqueId == aUID;
        if(!lFound)
            lChild = iTree->GetNextChild(iRoot,lCookie);
    }

    return lFound;
}

/*
 * Method:    OpenCamera()
 * Purpose:   open a given camera
 * Comments:  none
 */
tPvHandle CMainWindow::OpenCamera(unsigned long aUID,bool& aMaster)
{
    tPvHandle lHandle = NULL;

    if(PvCameraOpen(aUID,ePvAccessMaster,&lHandle))
    {
        if(!PvCameraOpen(aUID,ePvAccessMonitor,&lHandle))
            aMaster = false;
    }
    else
    {
        tPvUint32 lMaxSize = 8228;

        // get the last packet size set on the camera
        PvAttrUint32Get(lHandle,"PacketSize",&lMaxSize);
        // adjust the packet size according to the current network capacity
        PvCaptureAdjustPacketSize(lHandle,lMaxSize);

        aMaster = true;
    }

    return lHandle;
}

/*
 * Method:    CloseCamera()
 * Purpose:   close a given camera
 * Comments:  none
 */
void CMainWindow::CloseCamera(tPvHandle aHandle)
{
    PvCameraClose(aHandle);
}

// encode the value of a given attribute in a string
bool Value2String(tPvHandle aCamera,const char* aLabel,tPvDatatype aType,char* aString,unsigned long aLength)
{
    switch(aType)
    {
        case ePvDatatypeString:
        {
            if(!PvAttrStringGet(aCamera,aLabel,aString,aLength,NULL))
                return true;
            else
                return false;
        }
        case ePvDatatypeEnum:
        {
            if(!PvAttrEnumGet(aCamera,aLabel,aString,aLength,NULL))
                return true;
            else
                return false;
        }
        case ePvDatatypeUint32:
        {
            tPvUint32 lValue;

            if(!PvAttrUint32Get(aCamera,aLabel,&lValue))
            {
                sprintf(aString,"%lu",lValue);
                return true;
            }
            else
                return false;

        }
        case ePvDatatypeFloat32:
        {
            tPvFloat32 lValue;

            if(!PvAttrFloat32Get(aCamera,aLabel,&lValue))
            {
                sprintf(aString,"%g",lValue);
                return true;
            }
            else
                return false;
        }
        default:
            return false;
    }
}

// write a given attribute in a text file
void WriteAttribute(tPvHandle aHandle,const char* aLabel,FILE* aFile)
{
    tPvAttributeInfo lInfo;

    if(!PvAttrInfo(aHandle,aLabel,&lInfo))
    {
        if(lInfo.Datatype != ePvDatatypeCommand)
        {
            char lValue[128];

            if(Value2String(aHandle,aLabel,lInfo.Datatype,lValue,128))
                fprintf(aFile,"%s = %s\n",aLabel,lValue);
        }
    }
}


/*
 * Method:    DoCameraExport()
 * Purpose:   export the setup of a given camera
 * Comments:  none
 */
bool CMainWindow::ExportCamera(tPvHandle aHandle,const wxString& aFilename)
{
  FILE* lFile = fopen(aFilename.mb_str(wxConvUTF8),"w+");

    if(lFile)
    {
        bool            lRet = true;
        tPvAttrListPtr  lAttrs;
        tPvUint32       lCount;

        if(!PvAttrList(aHandle,&lAttrs,&lCount))
        {
            for(tPvUint32 i=0;i<lCount;i++)
                WriteAttribute(aHandle,lAttrs[i],lFile);
        }
        else
            lRet = false;

        fclose(lFile);

        return lRet;
    }
    else
        return false;
}
