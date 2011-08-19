/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         FinderWindow.cpp
|
| Project/lib:  Linux Sample Viewer
|
| Target:
|
| Description:  Implement the window that display basic informations on the
|               camera
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
#include <wx/sizer.h>
#include <wx/filedlg.h>

#include <FinderWindow.h>

//===== BITMAPS ===============================================================

#include <bitmap3.xpm>

//===== DEFINES ===============================================================

enum {
    ID_SAVE = 0,
    ID_FORCE,
    ID_SCALE,
    ID_100,
    ID_90,
    ID_80,
    ID_70,
    ID_60,
    ID_50,
    ID_40,
    ID_30,
    ID_20,
    ID_10,
};

#define min(a,b) (a < b ? a : b)

//===== CONSTANTS =============================================================

// number of frames used for streaming
const int kMaxFrames     = 5;
const int kMaxInitWidth  = 800;
const int kMaxInitHeight = 600;

//===== FUNCTION PROTOTYPES ===================================================

/*
 * Function:  FrameDoneCB()
 * Purpose:   Callback from PvAPI related to the post handling of a frame
 * Arguments:
 *
 *  [i] tPvFrame* Frame, frame handled by the API
 *
 * Return:    none
 * Comments:  none
 */
#ifdef __WXMSW__
void __stdcall FrameDoneCB(tPvFrame* pFrame);
#else
void FrameDoneCB(tPvFrame* pFrame);
#endif

//===== LOCAL DATA ============================================================

//===== EVENTS TABLE ==========================================================

BEGIN_DECLARE_EVENT_TYPES()
    DECLARE_EVENT_TYPE(dSTART,wxID_ANY)
    DECLARE_EVENT_TYPE(dSTOP,wxID_ANY)
    DECLARE_EVENT_TYPE(dUPDATE,wxID_ANY)
END_DECLARE_EVENT_TYPES()

DEFINE_EVENT_TYPE(dSTART)
DEFINE_EVENT_TYPE(dSTOP)
DEFINE_EVENT_TYPE(dUPDATE)

BEGIN_EVENT_TABLE(CFinderWindow, PChildWindow)
    EVT_SIZE(CFinderWindow::OnSize)
    EVT_COMMAND(wxID_ANY,dSTART,CFinderWindow::OnStart)
    EVT_COMMAND(wxID_ANY,dSTOP,CFinderWindow::OnStop)
    EVT_COMMAND(wxID_ANY,dUPDATE,CFinderWindow::OnUpdate)
    EVT_RIGHT_DOWN(CFinderWindow::OnRightClick)
    EVT_MENU(ID_SAVE,CFinderWindow::OnSave)
    EVT_MENU(ID_FORCE,CFinderWindow::OnForce)
    EVT_MENU(ID_SCALE,CFinderWindow::OnScale)
    EVT_MENU_RANGE(ID_100,ID_10,CFinderWindow::OnResize)
END_EVENT_TABLE()

//===== CLASS DEFINITION ======================================================

/*
 * Method:    CFinderWindow()
 * Purpose:   constructor
 * Comments:  none
 */
CFinderWindow::CFinderWindow(PChildWindowObserver& aObserver,const tPvCameraInfo& aInfo,tPvHandle aHandle)
    : PChildWindow(aObserver,L"",wxDefaultSize,wxRESIZE_BORDER | wxMAXIMIZE_BOX) , iHandle(aHandle)
{
    wxString lString;
    wxSizer* lMain;

    iWidth      = 0;
    iHeight     = 0;
    iFirst      = true;
    iStreaming  = false;
    iSaving     = false;
    iClosed     = false;
    iQueued     = false;

    // format the title of the window
    lString =  wxString(aInfo.SerialString,wxConvUTF8);
    lString += _T(" (");
    lString += wxString(aInfo.DisplayName,wxConvUTF8);
    lString += _T(") - View");
    // and set it
    SetTitle(lString);
    // Give it an icon
    SetIcon(wxIcon(bitmap3));
    // center on the screen
    CentreOnScreen(wxBOTH);

    // create the main sizer{
    lMain = new wxBoxSizer(wxVERTICAL);
    if(lMain)
    {
        // create the view and add it to the sizer
        iView = new CImageView(this,wxSize(640,480),aInfo.InterfaceType);
        if(iView)
            lMain->Add(iView,wxSizerFlags().Proportion(1).Expand().Border(wxALL,0));

        // set the main sizer in the window
        SetSizer(lMain);
        // and make that the window adjust its size to the sizer
        lMain->Fit(this);
    }

    // create the popup menu
    iContextMenu = new wxMenu();
    if(iContextMenu)
    {
        iContextMenu->Append(ID_SAVE,wxT("Save to disk"));
        iContextMenu->AppendCheckItem(ID_FORCE,wxT("Force Mono"));
        iContextMenu->AppendCheckItem(ID_SCALE,wxT("Scale"));
        iContextMenu->AppendSeparator();
        iContextMenu->AppendRadioItem(ID_100,wxT("100%"));
        iContextMenu->AppendRadioItem(ID_90,wxT("90%"));
        iContextMenu->AppendRadioItem(ID_80,wxT("80%"));
        iContextMenu->AppendRadioItem(ID_70,wxT("70%"));
        iContextMenu->AppendRadioItem(ID_60,wxT("60%"));
        iContextMenu->AppendRadioItem(ID_50,wxT("50%"));
        iContextMenu->AppendRadioItem(ID_40,wxT("40%"));
        iContextMenu->AppendRadioItem(ID_30,wxT("30%"));
        iContextMenu->AppendRadioItem(ID_20,wxT("20%"));
        iContextMenu->AppendRadioItem(ID_10,wxT("10%"));
    }

    // allocates the frames structures
    iFrames = new tPvFrame[kMaxFrames];
    if(iFrames)
        memset(iFrames,0,sizeof(tPvFrame) * kMaxFrames);

    // set the minimum size of the window
    SetMinSize(wxSize(100,100));
    // and of the view (necessary)
    if(iView)
        iView->SetMinSize(wxSize(100,100));
}

/*
 * Method:    ~CFinderWindow()
 * Purpose:   destructor
 * Comments:  none
 */
CFinderWindow::~CFinderWindow()
{
   // delete the image buffer of the frames
    for(int i=0;i<kMaxFrames;i++)
        delete [] (char *)iFrames[i].ImageBuffer;

    // and delete the frames structure
    delete [] iFrames;
}

/*
 * Method:    Start()
 * Purpose:   start streaming from the camera
 * Comments:  none
 */
void CFinderWindow::Start(bool aNow /* = false */)
{
    wxCommandEvent lEvent(dSTART,wxID_ANY);
    lEvent.SetEventObject(this);

    if(aNow)
        GetEventHandler()->ProcessEvent(lEvent);
    else
        GetEventHandler()->AddPendingEvent(lEvent);
}

/*
 * Method:    Stop()
 * Purpose:   stop streaming from the camera
 * Comments:  none
 */
void CFinderWindow::Stop(bool aNow /* = false */)
{
    wxCommandEvent lEvent(dSTOP,wxID_ANY);
    lEvent.SetEventObject(this);

    if(aNow)
        GetEventHandler()->ProcessEvent(lEvent);
    else
        GetEventHandler()->AddPendingEvent(lEvent);
}

/*
 * Method:    OnOpen()
 * Purpose:   called when the window is open
 * Comments:  none
 */
void CFinderWindow::OnOpen(wxCommandEvent& aEvent)
{
    // start the streaming
    Start(true);
}

/*
 * Method:    OnClose()
 * Purpose:   called when the window is been closed
 * Comments:  none
 */
void CFinderWindow::OnClose(wxCloseEvent& aEvent)
{
    // stop the streaming
    Stop(true);

    if(!iSaving)
        PChildWindow::OnClose(aEvent);
    else
    {
        iClosed = true;
        aEvent.Veto(true);
    }
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
void CFinderWindow::OnSize(wxSizeEvent& aEvent)
{
    // update the size of the view
    #if defined(__WXMSW__) || defined(__WXMAC__)
    iView->SetSize(GetClientSize());
    #else
    iView->SetSize(GetSize());
    #endif
    // and force the UI to be refreshed
    UpdateWindowUI(wxUPDATE_UI_RECURSE);
}

/*
 * Method:    OnStart()
 * Purpose:   called when the streaming should start
 * Comments:  none
 */
void CFinderWindow::OnStart(wxCommandEvent& aEvent)
{
    unsigned long lCapturing;
    tPvErr        lErr;

    // is the camera IDLE?
    if(!(lErr = PvCaptureQuery(iHandle,&lCapturing)))
    {
        if(!lCapturing)
        {
            // Setup the streaming
            if(!(lErr = PvCaptureStart(iHandle)))
            {
                // get the number of bytes needed for each frame as well as the width&height
                if(!(lErr = PvAttrUint32Get(iHandle,"TotalBytesPerFrame",&iBytesPerFrame)) &&
                   !(lErr = PvAttrUint32Get(iHandle,"Width",&iWidth)) &&
                   !(lErr = PvAttrUint32Get(iHandle,"Height",&iHeight)))
                {
                    // reset the rendering view if this isn't the first timer that we starting
                    // the streaming
                    if(iFirst)
                    {
                        iFirst = false;
                        // adjust the size of the window according to the expected frame dim.
                        #if defined(__WXMSW__) || defined(__WXMAC__)
                        SetClientSize(min(kMaxInitWidth,iWidth),min(kMaxInitHeight,iHeight));
                        #else
                        SetSize(min(kMaxInitWidth,iWidth),min(kMaxInitHeight,iHeight));
                        #endif
                    }
                    else
                        iView->Reset();

                    if(iBytesPerFrame)
                    {
                        // allocate the image buffer for each of the frames
                        for(int i=0;i<kMaxFrames && !lErr;i++)
                        {
                            if(iFrames[i].ImageBufferSize != iBytesPerFrame)
                            {
                                // delete the image buffer in case we have stopped then restarted
                                delete (char*)iFrames[i].ImageBuffer;
                                // then allocate the new one
                                iFrames[i].ImageBuffer = new char[iBytesPerFrame];
                                if(!iFrames[i].ImageBuffer)
                                    lErr = ePvErrResources;
                                else
                                {
                                    iFrames[i].ImageBufferSize = iBytesPerFrame;
                                    iFrames[i].Context[0]      = this;
                                }
                            }
                        }

                        if(!lErr)
                        {
                            // reset bandwith issue indicator
                            iBandwidth = false;

                            // and enqueue all the frames
                            for(int i=0;i<kMaxFrames && !lErr;i++)
                                lErr = PvCaptureQueueFrame(iHandle,&iFrames[i],FrameDoneCB);

                            if(!lErr)
                            {
                                iLock.Lock();
                                iStreaming = true;
                                iLock.Unlock();

                                // then force the acquisition mode to continuous to get the camera streaming
                                lErr = PvCommandRun(iHandle,"AcquisitionStart");

                                if(lErr && lErr != ePvErrForbidden)
                                {
                                    iLock.Lock();
                                    iStreaming = false;
                                    iLock.Unlock();

                                    ReportAnError(wxT("Acquisition couldn't be started"),lErr);
                                }
                                else
                                    lErr = ePvErrSuccess;
                            }
                            else
                                ReportAnError(_T("An error occured while enqueing the frames"),lErr);

                            // if there was an error, we'll dequeue all the queued frames, we won't
                            // delete the frames' buffers however
                            if(lErr)
                                PvCaptureQueueClear(iHandle);
                        }
                        else
                            ReportAnError(_T("failed to create the buffers!"));
                    }
                    else
                        ReportAnError(_T("Incorrect frame size"));
                }
                else
                    ReportAnError(_T("Failed to talk to the camera"),lErr);

                // if there was an error, we unsetup the streaming
                if(lErr)
                    PvCaptureEnd(iHandle);
            }
            else
                ReportAnError(_T("Streaming couldn't be setup"),lErr);
        }
        else
            ReportAnError(_T("Camera is not in IDLE mode"),lErr);
    }
    else
        ReportAnError(_T("Failed to talk to the camera"),lErr);
}

/*
 * Method:    OnStop()
 * Purpose:   called when the streaming should stop
 * Comments:  none
 */
void CFinderWindow::OnStop(wxCommandEvent& aEvent)
{
    unsigned long lCapturing;
    tPvErr        lErr;

    // is the camera not IDLE?
    if(!(lErr = PvCaptureQuery(iHandle,&lCapturing)))
    {
        if(lCapturing)
        {
            // then force the acquisition mode to stopped to get the camera to stop streaming
            lErr = PvCommandRun(iHandle,"AcquisitionStop");

            if(!lErr || lErr == ePvErrForbidden)
            {
                // stop streaming
                if((lErr = PvCaptureEnd(iHandle)) && (lErr != ePvErrUnplugged))
                    ReportAnError(_T("Failed to stop the streaming"),lErr);
            }
            else
            if(lErr != ePvErrUnplugged)
                ReportAnError(_T("Failed to stop the streaming"),lErr);

            iLock.Lock();
            iStreaming = false;
            iLock.Unlock();
            // then dequeue all the frames still in the queue (we
            // will ignore any error as the capture was stopped anyway)
            PvCaptureQueueClear(iHandle);
        }
        else
        {
            // then dequeue all the frame still in the queue
            // in case there is any left in it and that the camera
            // was unplugged (we will ignore any error as the
            // capture was stopped anyway)
            PvCaptureQueueClear(iHandle);
            iLock.Lock();
            iStreaming = false;
            iLock.Unlock();
        }
    }

     // was the camera unplugged while we were streaming?
    if(lErr == ePvErrUnplugged)
    {
        // we still need to dequeue all queued frames
        PvCaptureQueueClear(iHandle);
        iLock.Lock();
        iStreaming = false;
        iLock.Unlock();
    }
}

/*
 * Method:    OnUpdate()
 * Purpose:   called when the rendered frame have been updated
 * Comments:  none
 */
void CFinderWindow::OnUpdate(wxCommandEvent& aEvent)
{
    tPvFrame* lFrame = (tPvFrame*)aEvent.GetExtraLong();
        
    // only render if not iconized
    if(!IsIconized())
    {
        // flag for repaint
        iView->Refresh();
        // update
        iView->Update(lFrame);
    }
    
    iLock.Lock();
    iQueued = false;
    iLock.Unlock();
    
    if(iStreaming)
        PvCaptureQueueFrame(iHandle,lFrame,FrameDoneCB);
}

/*
 * Method:    OnRightClick()
 * Purpose:   called when the right button of the mouse
 *            is been pressed
 * Comments:  none
 */
void CFinderWindow::OnRightClick(wxMouseEvent& aEvent)
{
    // refresh the menu items
    iContextMenu->Check(ID_SCALE,iView->IsScaling());
    iContextMenu->Check(ID_FORCE,iView->IsForcingMono());

    // pop-up the contextual menu
    PopupMenu(iContextMenu);

    // flag the view so that it'll get repainted
    iView->Refresh();
    // and force the UI to be refreshed
    UpdateWindowUI(wxUPDATE_UI_RECURSE);
}

/*
 * Method:    OnSave()
 * Purpose:   called when the user request the frame to be saved
 * Comments:  none
 */
void CFinderWindow::OnSave(wxCommandEvent& aEvent)
{
    wxImage* lImage = iView->CopyImage();

    iSaving = true;

    if(lImage)
    {
        #ifndef __WXMAC__
        wxFileDialog lDialog(NULL,wxT("Select a file"),wxT(""),wxT("Snapshot.bmp"),wxT("BMP and JPG files (*.bmp;*.jpg)|*.bmp;*.jpg|PNG files (*.png)|*.png"),wxSAVE | wxOVERWRITE_PROMPT);
        #else
        wxFileDialog lDialog(NULL,wxT("Select a file"),wxT(""),wxT("Snapshot.bmp"),wxT("BMP files (*.bmp)|*.bmp"),wxSAVE | wxOVERWRITE_PROMPT);
        #endif

        if(lDialog.ShowModal() == wxID_OK)
            if(!lImage->SaveFile(lDialog.GetPath()))
  	            ReportAnError(wxT("Failed to save the image ..."));

        delete lImage;

    }
    else
        ReportAnError(wxT("There is no image to be saved ..."));

    iSaving = false;
    if(iClosed)
        Close(true);
}

/*
 * Method:    OnForce()
 * Purpose:   called when the user request the image to be rendered as Mono
 * Comments:  none
 */
void CFinderWindow::OnForce(wxCommandEvent& aEvent)
{
    iView->SetForceMono(!iView->IsForcingMono());
}

/*
 * Method:    OnScale()
 * Purpose:   called when the user request the image to be scaled
 * Comments:  none
 */
void CFinderWindow::OnScale(wxCommandEvent& aEvent)
{
    iView->SetToScale(!iView->IsScaling());
}

/*
 * Method:    OnResize()
 * Purpose:   called when the window shall be resized as specified
 *            by the user
 * Comments:  none
*/
void CFinderWindow::OnResize(wxCommandEvent& aEvent)
{
    float lRatio = (100 - ((aEvent.GetId() - ID_100) * 10)) / 100.0;

    #if defined(__WXMSW__) || defined(__WXMAC__)
    SetClientSize((int)(iWidth * lRatio),(int)(iHeight * lRatio));
    #else
    SetSize((int)(iWidth * lRatio),(int)(iHeight * lRatio));
    #endif
}

/*
 * Method:    OnNotification()
 * Purpose:   called when the window is notified of
 *            something
 * Comments:  none
 */
void CFinderWindow::OnNotification(CNotifyEvent& aEvent)
{
    switch(aEvent.GetEvent())
    {
        case kEvnLiveStart:
        {
            Start(true);
            break;
        }
        case kEvnLiveStop:
        {
            Stop(true);
            break;
        }
        default:
            break;
    }
}


/*
 * Method:    OnFrameDone()
 * Purpose:   called when a frame is returned by the API
 * Comments:  none
 */
void CFinderWindow::OnFrameDone(tPvFrame* aFrame)
{
    iLock.Lock();

    if(iStreaming)
    {
        if(!iQueued && aFrame->Status == ePvErrSuccess)
        {
            wxCommandEvent lEvent(dUPDATE,wxID_ANY);
            lEvent.SetEventObject(this);
            lEvent.SetExtraLong((long)aFrame);
            GetEventHandler()->AddPendingEvent(lEvent);
            
            iQueued = true;              
        }
        else
            PvCaptureQueueFrame(iHandle,aFrame,FrameDoneCB);
    }

    iLock.Unlock();
}

/*
 * Function:  FrameDoneCB()
 * Purpose:   Callback from PvAPI related to the post handling of a frame
 * Comments:  none
 */
#ifdef __WXMSW__
void __stdcall FrameDoneCB(tPvFrame* pFrame)
#else
void FrameDoneCB(tPvFrame* pFrame)
#endif
{
    CFinderWindow* lWindow = (CFinderWindow*)pFrame->Context[0];

    if(lWindow)
        lWindow->OnFrameDone(pFrame);
}
