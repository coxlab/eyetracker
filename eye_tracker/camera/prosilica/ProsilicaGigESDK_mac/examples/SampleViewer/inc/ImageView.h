/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         ImageView.h
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
#include <wx/scrolwin.h>
#include <wx/image.h>
#include <wx/bitmap.h>
#include <wx/thread.h>

//===== CLASS DEFINITION ======================================================

/*
 * Class:    CImageView
 * Purpose:  Derive the standard scrolled window to create view that display
 *           frame from the camera
 * Comments: none
 */
class CImageView : public wxScrolledWindow
{
    public: // cons./des.

        /*
         * Method:    CImageView()
         * Purpose:   constructor
         * Arguments:
         *
         * [i] wxWindow* aParent,       parent window
         * [i] const wxSize& aSize,     initial size of the view
         * [i] tPvInterface aInterface, interface used by the camera
         *
         * Return:    none
         * Comments:  none
         */ 
        CImageView(wxWindow* aParent,const wxSize& aSize,tPvInterface aInterface);

         /*
         * Method:    ~CImageView()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~CImageView();

    public: // methods
            
        /*
         * Method:    Update()
         * Purpose:   update the rendering with a given frame
         * Arguments: 
         *
         * [i] tPvFrame* aFrame, frame
         *
         * Return:    true if rendered, false otherwise
         * Comments:  none
         */ 
        bool Update(tPvFrame* aFrame);

        /*
         * Method:    SetToScale()
         * Purpose:   instruct the view to scale the image to fit
         *            in the window
         * Arguments: 
         *
         * [i] bool aScale, true if to scale, false otherwise
         *
         * Return:    none
         * Comments:  none
         */ 
        void SetToScale(bool aScale);

        /*
         * Method:    IsScaling()
         * Purpose:   check if the image is scaled or not
         * Arguments: none
         * Return:    none
         * Comments:  none
         */ 
        bool IsScaling() const {return iScale;};

        /*
         * Method:    SetForceMono()
         * Purpose:   instruct the view to render all color as mono
         * Arguments: 
         *
         * [i] bool aMono, true if to render as mono, false otherwise
         *
         * Return:    none
         * Comments:  none
         */ 
        void SetForceMono(bool aMono) {iForceMono = aMono;};

        /*
         * Method:    IsForcingMono()
         * Purpose:   check if the image is forced as mono
         * Arguments: none
         * Return:    true or false
         * Comments:  none
         */ 
        bool IsForcingMono() const {return iForceMono;};        
        
        /*
         * Method:    Reset()
         * Purpose:   do whatever need to be done when the streaming is re-started
         * Arguments: none
         * Return:    none
         * Comments:  none
         */
        void Reset();

        /*
         * Method:    CopyImage()
         * Purpose:   copy the last image data received into a new image
         *            object
         * Arguments: none
         * Return:    the image (NULL if failed)
         * Comments:  none
         */
        wxImage* CopyImage();
              
    public: // callbacks

        /*
         * Method:    OnDraw()
         * Purpose:   called when the view need to be redraw
         * Arguments:
         *
         * [i] wxDC& aDC, drawing device context
         * 
         * Return:    none
         * Comments:  none
         */     
        void OnDraw(wxDC& aDC);

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
         * Method:    OnAdapt()
         * Purpose:   called when the view need to be adapted due to
         *            a change in the image size
         * Arguments:
         *
         * [i] wxCommandEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnAdapt(wxCommandEvent& aEvent);

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
         * Method:    OnEraseBackground()
         * Purpose:   called when the background of the frame should be
         *            erased
         * Arguments:
         *
         * [i] wxEraseEvent& aEvent, event
         *
         * Return:    none
         * Comments:  none
         */ 
        void OnEraseBackground(wxEraseEvent& aEvent);

        DECLARE_EVENT_TABLE()

    private: // methods

        /*
         * Method:    Process()
         * Purpose:   process a given frame for rendering
         * Arguments: 
         *
         * [i] tPvFrame* aFrame, frame
         *
         * Return:    none
         * Comments:  none
         */             
         void Process(tPvFrame* aFrame);

        /*
         * Method:    AdaptToSize()
         * Purpose:   adapt the view to the image size
         * Arguments: none
         * Return:    none
         * Comments:  none
         */    
         void AdaptToSize();

    private: // data

        // interface type
        tPvInterface  iInterface;
        // true when the image is been scaled
        bool          iScale;
        // true when the image's is to be "converted" to Mono
        bool          iForceMono;
        // image
        wxImage*      iImage;
        wxBitmap*     iBitmap;
        // indicate when the image have been updated but not yet rendered
        bool          iFreshData;
        // lock mecanism for the image
        wxMutex       iLock;
        // image data
        unsigned long iLeft;
        unsigned long iTop;
        unsigned long iWidth;
        unsigned long iHeight;
        bool          iIsBgr;
        float         iWRatio;
        float         iHRatio;
};
