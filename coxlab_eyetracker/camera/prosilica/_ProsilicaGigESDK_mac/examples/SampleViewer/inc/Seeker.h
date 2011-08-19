/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         Seeker.h
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Define the worker that seek a camera
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

#include <Worker.h>

//===== CONSTANTS =============================================================

// event's code
const tUint32 kEvnSeekerStarted  = 0x0001;
const tUint32 kEvnSeekerFinished = 0x0002;

//===== CLASS DEFINITION ======================================================

class CSeeker : public PWorker
{
    public:
    
        /*
         * Method:    CSeeker()
         * Purpose:   constructor
         * Arguments: 
         *       
         * [i] tInt32 aId,              Id of the worker
         * [i] wxEvtHandler* aHandler,  handle to be notified by the worker
         * [i] tUint32 aAddr,           IP @ of the camera
         *
         * Return:    none
         * Comments:  none
         */ 
        CSeeker(tInt32 aId,wxEvtHandler* aHandler,tUint32 aAddr);

         /*
         * Method:    ~CSeeker()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~CSeeker();
    
    protected:
    
        /*
         * Method:    OnEntry()
         * Purpose:   called when the thread is starting
         * Arguments: none
         * Return:    none
         * Comments:  none
         */ 
        void OnEntry();
        
        /*
         * Method:    OnExit()
         * Purpose:   called when the thread is terminating
         * Arguments: none
         * Return:    none
         * Comments:  none
         */         
        void OnExit();
        
        /*
         * Method:    OnRunning()
         * Purpose:   called when the thread is running (body)
         * Arguments: none
         * Return:    return code
         * Comments:  none
         */ 
        tUint32 OnRunning();      
    
    private:
    
        tUint32 iAddr;  // ip @
        tBool   iFound; // set to true when the camera have been found
};
