/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         Application.cpp
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Implement the application class
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

#include <Application.h>
#include <PvApi.h>

//===== FUNCTION PROTOTYPES ===================================================

/*
 * Function:  LinkEventCB()
 * Purpose:   Callback to be run by PvApi when an event occurs on the Link
 * Arguments:
 *
 *  [i] void* aContext,          Context, as provided to PvLinkCallbackRegister
 *  [i] tPvInterface aInterface, Interface on which the event occurred
 *  [i] tPvLinkEvent aEvent,     Event which occurred
 *  [i] unsigned long aUniqueId, Unique ID of the camera related to the event
 *
 * Return:    none
 * Comments:  none
 */    
#ifdef __WXMSW__
void __stdcall LinkEventCB(void* aContext,tPvInterface aInterface,tPvLinkEvent aEvent,unsigned long aUniqueId);
#else
void LinkEventCB(void* aContext,tPvInterface aInterface,tPvLinkEvent aEvent,unsigned long aUniqueId);
#endif

//===== CLASS IMPLEMENTATIONS =================================================

/*
 * Method:    CApplication()
 * Purpose:   constructor
 * Comments:  none
 */
CApplication::CApplication()
{
    iMain = NULL;

    #ifndef _x64
    SetUseBestVisual(true);
    #endif
    SetAppName(L"wxViewer");
    SetVendorName(L"Prosilica Inc.");
}

/*
 * Method:    ~CApplication()
 * Purpose:   destructor
 * Comments:  none
 */
CApplication::~CApplication()
{
}

/*
 * Method:    OnInit()
 * Purpose:   called when the application is starting
 * Comments:  none
 */
bool CApplication::OnInit()
{
    if(!PvInitialize())
    {
        iMain = new CMainWindow();
        if(iMain)
        {
            iMain->Show(true);
            SetTopWindow(iMain);

            // register the callback for the link events
            PvLinkCallbackRegister(LinkEventCB,ePvLinkAdd,this);
            PvLinkCallbackRegister(LinkEventCB,ePvLinkRemove,this);
                
            return true;
        }
        else
            return false;
    }
    else
    {
        fprintf(stderr,"Failed to initialize PvAPI ...\n");
        return false;
    }
}

/*
 * Method:    OnExit()
 * Purpose:   called when the application is exiting
 * Comments:  none
 */
int CApplication::OnExit()
{
    if(iMain)
    {
        // unregister the callback for the camera events
        PvLinkCallbackUnRegister(LinkEventCB,ePvLinkAdd);
        PvLinkCallbackUnRegister(LinkEventCB,ePvLinkRemove);
    }

    PvUnInitialize();
    
    return wxApp::OnExit();   
}

/*
 * Method:    OnRun()
 * Purpose:   called when the application is started
 * Comments:  none
 */
int CApplication::OnRun()
{
    return wxApp::OnRun();    
}

/*
 * Function:  LinkEventCB()
 * Purpose:   Callback to be run by PvApi when an event occurs on the Link
 * Comments:  none
 */    
#ifdef __WXMSW__
void __stdcall LinkEventCB(void* aContext,tPvInterface aInterface,tPvLinkEvent aEvent,unsigned long aUniqueId)
#else
void LinkEventCB(void* aContext,tPvInterface aInterface,tPvLinkEvent aEvent,unsigned long aUniqueId)
#endif
{
    CApplication* lApplication = (CApplication*)aContext;

    if(lApplication->iMain)
    {
        // append a custom event
        CLinkEvent lEvent(aEvent,aUniqueId);
        lEvent.SetEventObject(lApplication);
        ::wxPostEvent(lApplication->iMain->GetEventHandler(),lEvent);
    }            
}


IMPLEMENT_APP(CApplication)
