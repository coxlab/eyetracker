/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         Application.h
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Define the application class
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

#include <wx/wx.h>

#include <PvApi.h>
#include <MainWindow.h>

//===== CLASS DEFINITION ======================================================

/*
 * Class:    CApplication
 * Purpose:  Derive the standard wxWidget application
 * Comments: none
 */
class CApplication : public wxApp
{
    public:

        /*
         * Method:    CApplication()
         * Purpose:   constructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */ 
        CApplication();

         /*
         * Method:    ~CApplication()
         * Purpose:   destructor
         * Arguments: none
         * Return:    none
         * Comments:  none
         */        
        ~CApplication();

        /*
         * Method:    OnInit()
         * Purpose:   called when the application is starting
         * Arguments: none
         * Return:    false if the application must terminate
         * Comments:  none
         */        
        virtual bool OnInit();

        /*
         * Method:    OnRun()
         * Purpose:   called when the application is started
         * Arguments: none
         * Return:    application return code
         * Comments:  none
         */        
        virtual int OnRun();

        /*
         * Method:    OnExit()
         * Purpose:   called when the application is exiting
         * Arguments: none
         * Return:    ignored
         * Comments:  none
         */        
        virtual int OnExit();

    protected:

        // main window
        CMainWindow* iMain;
                 
        #ifdef __WXMSW__
        friend void __stdcall LinkEventCB(void* aContext,tPvInterface aInterface,tPvLinkEvent aEvent,unsigned long aUniqueId);           
        #else
        friend void LinkEventCB(void* aContext,tPvInterface aInterface,tPvLinkEvent aEvent,unsigned long aUniqueId);                   
        #endif
};
