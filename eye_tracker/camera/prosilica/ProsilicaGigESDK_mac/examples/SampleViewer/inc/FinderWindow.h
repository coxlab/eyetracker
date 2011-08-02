/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         FinderWindow.h
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Define the window that display live image from a camera
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
#include <ImageView.h>

#include <wx/menu.h>

//===== CONSTANTS =============================================================

// <!> if these two constants are changed, the ones in CtrlWindow.cpp must be
//     updated!
const int kEvnLiveStart = 0xC;
const int kEvnLiveStop  = 0xD;

//===== CLASS DEFINITION ======================================================

/*
 * Class:    CMainWindow
 * Purpose:  Derive the standard frame class to create the main window of the
 *           application
 * Comments: none
 */
class CFinderWindow : public PChildWindow
{
    public: // cons./des.

        /*
         * Method:    CFinderWindow()
         * Purpose:   constructor
         * Arguments:
         *
         * [i] PChildWindowObserver& aObserver, observer
         * [i] const tPvCameraInfo& aInfo,      camera's information
         * [i] tPvHandle aHandle,               handle to the camera
         *
         * Return:    none
         * Comments:  none
         */ 
        CFinderWindow(PChildWindowObserver& aObserver,const tPvCameraInfo& aInfo,tPvHandle aHandle);

         /*
         * Method:    ~CFinderWindow()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~CFinderWindow();

    public: // methods
         
        /*
         * Method:    Start()
         * Purpose:   start streaming from the camera
         * Arguments:
         *
         * [i] bool aNow, when true, the command will be processed right away
         *                and the call block until the streaming is started
         *
         * Return:    none
         * Comments:  none
         */
        void Start(bool aNow = false);

        /*
         * Method:    Stop()
         * Purpose:   stop streaming from the camera
         * Arguments:
         *
         * [i] bool aNow, when true, the command will be processed right away
         *                and the call block until the streaming is stopped
         *
         * Return:    none
         * Comments:  none
         */
        void Stop(bool aNow = false);

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
         * Method:    OnStart()
         * Purpose:   called when the streaming should start
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnStart(wxCommandEvent& aEvent);

        /*
         * Method:    OnStop()
         * Purpose:   called when the streaming should stop
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnStop(wxCommandEvent& aEvent);

        /*
         * Method:    OnUpdate()
         * Purpose:   called when the rendered frame have been updated
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnUpdate(wxCommandEvent& aEvent);

        /*
         * Method:    OnRightClick()
         * Purpose:   called when the right button of the mouse
         *            is been pressed
         * Arguments:
         *
         * [i] wxMouseEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnRightClick(wxMouseEvent& aEvent);

        /*
         * Method:    OnSave()
         * Purpose:   called when the user request the frame to be saved
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnSave(wxCommandEvent& aEvent);

        /*
         * Method:    OnForce()
         * Purpose:   called when the user request the image to be rendered as Mono
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnForce(wxCommandEvent& aEvent);
        
        /*
         * Method:    OnScale()
         * Purpose:   called when the user request the image to be scaled
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnScale(wxCommandEvent& aEvent);

        /*
         * Method:    OnResize()
         * Purpose:   called when the window shall be resized as specified
         *            by the user
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnResize(wxCommandEvent& aEvent);

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

    protected:

        /*
         * Method:    OnFrameDone()
         * Purpose:   called when a frame is returned by the API
         * Arguments:
         *
         * [i] tPvFrame* aFrame, frame
         *
         * Return:    none
         * Comments:  none
         */
        void OnFrameDone(tPvFrame* aFrame);

    private:

        // contextual menu
        wxMenu*         iContextMenu;
        // image view
        CImageView*     iView;
        // handle to the camera
        tPvHandle       iHandle;
        // array of frame used for streaming
        tPvFrame*       iFrames;
        // current bytes per frame
        tPvUint32       iBytesPerFrame;
        // flag used when restarting the streaming
        bool            iFirst;
        // true when streaming
        bool            iStreaming;
        // some other flags
        bool            iBandwidth;
        // known size of the frames
        unsigned long   iWidth;
        unsigned long   iHeight;

        // some flags used for ...
        bool            iSaving;
        bool            iClosed;
        bool            iQueued;

        // lock mecanism
        wxMutex         iLock;

        #ifdef __WXMSW__
        friend void __stdcall FrameDoneCB(tPvFrame* pFrame);
        #else
        friend void FrameDoneCB(tPvFrame* pFrame);
        #endif
};
