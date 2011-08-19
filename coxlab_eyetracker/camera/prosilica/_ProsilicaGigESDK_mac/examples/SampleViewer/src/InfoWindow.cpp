/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         InfoWindow.cpp
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
#include <wx/textctrl.h>
#include <wx/stattext.h>

#include <InfoWindow.h>

//===== BITMAPS ===============================================================

#include <bitmap1.xpm>

//===== DEFINES ===============================================================

//===== LOCAL DATA ============================================================

//===== EVENTS TABLE ==========================================================

BEGIN_EVENT_TABLE(CInfoWindow, PChildWindow)
END_EVENT_TABLE()

//===== CLASS DEFINITION ======================================================

/*
 * Method:    CInfoWindow()
 * Purpose:   constructor
 * Comments:  none
 */
CInfoWindow::CInfoWindow(PChildWindowObserver& aObserver,const tPvCameraInfo& aInfo)
    : PChildWindow(aObserver,L"",wxSize(300,200),0)               
{
    wxString lString;
    wxSizer* lMain;

    // format the title of the window
    lString =  wxString(aInfo.SerialString,wxConvUTF8);
    lString += _T(" (");
    lString += wxString(aInfo.DisplayName,wxConvUTF8);
    lString += _T(") - Information");
    // and set it
    SetTitle(lString);
    // Give it an icon
    SetIcon(wxIcon(bitmap1));
    // center on the screen
    CentreOnScreen(wxBOTH);
    #ifdef __WXMSW__
    // set the background color
    SetBackgroundColour(*wxLIGHT_GREY);
    #endif
    
    // create the main sizer
    lMain = new wxBoxSizer(wxVERTICAL);
    if(lMain)
    {
        // then create a grid size to fit all the label/value in
        wxSizer* lGrid = new wxGridSizer(2,6,5);

        if(lGrid)
        {        
            // Unique ID
  	    lString.Printf(wxT("%lu"),aInfo.UniqueId);
            lGrid->Add(new wxStaticText(this,wxID_ANY,_T("Unique ID:")),
                        wxSizerFlags().Align(wxALIGN_LEFT | wxALIGN_CENTER_VERTICAL));
            lGrid->Add(new wxStaticText(this,wxID_ANY,lString),
                        wxSizerFlags().Align(wxALIGN_RIGHT | wxALIGN_CENTER_VERTICAL));
            // Serial number
            lGrid->Add(new wxStaticText(this,wxID_ANY,_T("Serial Number:")),
                        wxSizerFlags().Align(wxALIGN_LEFT | wxALIGN_CENTER_VERTICAL));
            lGrid->Add(new wxStaticText(this,wxID_ANY,wxString(aInfo.SerialString,wxConvUTF8)),
                        wxSizerFlags().Align(wxALIGN_RIGHT | wxALIGN_CENTER_VERTICAL));
            // Part number
            lString.Printf(wxT("%lu"),aInfo.PartNumber);
            lGrid->Add(new wxStaticText(this,wxID_ANY,_T("Part Number:")),
                        wxSizerFlags().Align(wxALIGN_LEFT | wxALIGN_CENTER_VERTICAL));
            lGrid->Add(new wxStaticText(this,wxID_ANY,lString),
                        wxSizerFlags().Align(wxALIGN_RIGHT | wxALIGN_CENTER_VERTICAL));
            // Part version
            lString.Printf(wxT("%c"),(char)aInfo.PartVersion);
            lGrid->Add(new wxStaticText(this,wxID_ANY,_T("Part Version:")),
                        wxSizerFlags().Align(wxALIGN_LEFT | wxALIGN_CENTER_VERTICAL));
            lGrid->Add(new wxStaticText(this,wxID_ANY,lString),
                        wxSizerFlags().Align(wxALIGN_RIGHT | wxALIGN_CENTER_VERTICAL));
            // Interface type
            lGrid->Add(new wxStaticText(this,wxID_ANY,_T("Interface Type:")),
                        wxSizerFlags().Align(wxALIGN_LEFT | wxALIGN_CENTER_VERTICAL));
            lGrid->Add(new wxStaticText(this,wxID_ANY,
                        (aInfo.InterfaceType == ePvInterfaceEthernet ? _T("Giga-Ethernet") : _T("Firewire"))),
                        wxSizerFlags().Align(wxALIGN_RIGHT | wxALIGN_CENTER_VERTICAL));
            lString.Printf(wxT("%lu"),aInfo.InterfaceId);
            lGrid->Add(new wxStaticText(this,wxID_ANY,_T("Interface ID:")),
                        wxSizerFlags().Align(wxALIGN_LEFT | wxALIGN_CENTER_VERTICAL));
            lGrid->Add(new wxStaticText(this,wxID_ANY,lString),
                        wxSizerFlags().Align(wxALIGN_RIGHT | wxALIGN_CENTER_VERTICAL));
                                   
            // add the grid to the main sizer                       
            lMain->Add(lGrid,wxSizerFlags().Proportion(1).Expand().Border(wxALL,20));
        }
                          
        // set the main sizer in the window
        SetSizer(lMain);
        // and make that the window adjust its size to the sizer
        lMain->Fit(this);
    }
}

/*
 * Method:    ~CInfoWindow()
 * Purpose:   destructor
 * Comments:  none
 */
CInfoWindow::~CInfoWindow()
{
}
