/*
| ==============================================================================
| Copyright (C) 2009 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         SerialWindow.cpp
|
| Project/lib:  Linux Sample Viewer
|
| Target:       
|
| Description:  Implement the window that display the camera's serialIO shell
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
#include <wx/button.h>
#include <wx/checkbox.h>
#include <wx/msgdlg.h>

#include <SerialWindow.h>
#include <PvApi.h>
#include <PvRegIo.h>

//===== BITMAPS ===============================================================

#include <bitmap10.xpm>

//===== DEFINES ===============================================================

enum
{
    ID_ENTRY = 1,
    ID_BAUDRATE,
    ID_PARITY,
    ID_CHARLEN,
    ID_STOPBITS,
    ID_CONNECT,
    ID_DISCONNECT,
    ID_SEND
    
};

// Camera registers dealing with Serial IO
#define REG_SIO_INQUIRY			0x16000
#define REG_SIO_MODE_INQUIRY	0x16100
#define REG_SIO_MODE			0x16104
#define REG_SIO_TX_INQUIRY		0x16120
#define REG_SIO_TX_STATUS		0x16124
#define REG_SIO_TX_CONTROL		0x16128
#define REG_SIO_TX_LENGTH		0x1612C
#define REG_SIO_RX_INQUIRY		0x16140
#define REG_SIO_RX_STATUS		0x16144
#define REG_SIO_RX_CONTROL		0x16148
#define REG_SIO_RX_LENGTH		0x1614C
#define REG_SIO_TX_BUFFER		0x16400
#define REG_SIO_RX_BUFFER		0x16800

//===== CONSTANTS =============================================================

// standard size of the window
const int kInitWidth            = 700;
const int kInitHeight           = 500;
// extra padding (scrollbar width)
const int kPadding              = 16;
// height of the panel
const int kPanelHeightTop       = 60;
const int kPanelHeightBottom    = 40;
// height of the list
const int kListHeight           = kInitHeight - (kPanelHeightTop + kPanelHeightBottom);
// attributes refresh interval (ms) in read/write mode
const int kRefreshInterval      = 250;


static const wchar_t* KBaudRates[] = {

    _T("300"),
    _T("600"),
    _T("1200"),
    _T("2400"),
    _T("4800"),
    _T("9600"),
    _T("19200"),
    _T("38400"),
    _T("57600"),
    _T("115200"),
    _T("230400")

};

static const wchar_t* KParities[] = {
    
    _T("None"),
    _T("Odd"),
    _T("Even")

};

static const wchar_t* KCharLens[] = {

    _T("5 bits"),
    _T("6 bits"),
    _T("7 bits"),
    _T("8 bits")

};

static const wchar_t* KStopBits[] = {

    _T("1 bit"),
    _T("1.5 bits"),
    _T("2 bits")

};

//===== INLINES ===============================================================

inline void SetBits(unsigned int& aValue,unsigned int aData,unsigned int aPosition,unsigned int aLength)
{
    unsigned int datamask;   // data mask, before aPosition shift

    if (aLength == 32)
        datamask = 0xFFFFFFFF;
    else
        datamask = (1L << aLength) - 1;

    aValue &= ~(datamask << aPosition);             // Clear bits
    aValue |= (aData & datamask) << aPosition;      // Set value
}

inline void SetBits(unsigned long& aValue,unsigned int aData,unsigned int aPosition,unsigned int aLength)
{
    unsigned int datamask;   // data mask, before aPosition shift

    if (aLength == 32)
        datamask = 0xFFFFFFFF;
    else
        datamask = (1L << aLength) - 1;

    aValue &= ~(datamask << aPosition);             // Clear bits
    aValue |= (aData & datamask) << aPosition;      // Set value
}

inline unsigned int GetBits(unsigned int aValue,unsigned int aPosition,unsigned int aLength)
{
    unsigned int datamask;   // data mask, before aPosition shift

    if (aLength == 32)
        datamask = 0xFFFFFFFF;
    else
        datamask = (1L << aLength) - 1;

    return (aValue >> aPosition) & datamask;
}

bool F_WriteMem(tPvHandle camera,unsigned long address,const unsigned char*	buffer,unsigned long length)
{
	const unsigned long	numRegs = (length + 3) / 4;
	unsigned long*		pAddressArray = new unsigned long[numRegs];
	unsigned long*		pDataArray = new unsigned long[numRegs];
	bool				result;
	unsigned long		i;


	//
	// We want to write an array of bytes from the camera.  To do this, we
	// write sequential registers with the data array.  The register MSB
	// is the first byte of the array.
	//

	// 1.  Generate write addresses, and convert from byte array to MSB-packed
	// registers.
	for (i = 0; i < numRegs; i++)
	{
		pAddressArray[i] = address + (i*4);

		pDataArray[i] = (unsigned long)*(buffer++) << 24;
		pDataArray[i] |= (unsigned long)*(buffer++) << 16;
		pDataArray[i] |= (unsigned long)*(buffer++) << 8;
		pDataArray[i] |= (unsigned long)*(buffer++);
	}

	// 2.  Execute write.
	if (PvRegisterWrite(camera, numRegs, pAddressArray, pDataArray, NULL) == ePvErrSuccess)
		result = true;
	else
		result = false;

	delete [] pAddressArray;
	delete [] pDataArray;

	return result;
}

bool F_ReadMem(tPvHandle camera,unsigned long address,unsigned char* buffer,unsigned long length)
{
	const unsigned long	numRegs = (length + 3) / 4;
	unsigned long*		pAddressArray = new unsigned long[numRegs];
	unsigned long*		pDataArray = new unsigned long[numRegs];
	bool				result;
	unsigned long		i;


	//
	// We want to read an array of bytes from the camera.  To do this, we
	// read sequential registers which contain the data array.  The register
	// MSB is the first byte of the array.
	//

	// 1.  Generate read addresses
	for (i = 0; i < numRegs; i++)
		pAddressArray[i] = address + (i*4);

	// 2.  Execute read.
	if (PvRegisterRead(camera, numRegs, pAddressArray, pDataArray, NULL) == ePvErrSuccess)
	{
        unsigned long data = 0;

		// 3.  Convert from MSB-packed registers to byte array
		for (i = 0; i < length; i++)
		{
			if (i % 4 == 0)
				data = pDataArray[i/4];

			buffer[i] = (unsigned char)((data >> 24) & 0xFF);
			data <<= 8;
		}

		result = true;
	}
	else
		result = false;

	delete [] pAddressArray;
	delete [] pDataArray;

	return result;
}

bool WriteStringToSerialIO(tPvHandle camera,const char* string,unsigned int length)
{
	unsigned long		regAddress;
	unsigned long		regValue;

	// Wait for transmitter ready.
	do
	{
		regAddress = REG_SIO_TX_STATUS;
		if (PvRegisterRead(camera, 1, &regAddress, &regValue, NULL) != ePvErrSuccess)
			return false;
	}
	while (!(regValue & 1));  // Waiting for transmitter-ready bit

	// Write the buffer.
	if (!F_WriteMem(camera, REG_SIO_TX_BUFFER, (const unsigned char*)string, length))
		return false;

	// Write the buffer length.  This triggers transmission.
	regAddress = REG_SIO_TX_LENGTH;
	regValue = length;
	if (PvRegisterWrite(camera, 1, &regAddress, &regValue, NULL) != ePvErrSuccess)
		return false;

	return true;
}

bool ReadStringFromSerialIO(tPvHandle camera,unsigned char*	buffer,unsigned long bufferLength,unsigned long* pReceiveLength)
{
	unsigned long		regAddress;
	unsigned long		dataLength;

	// How many characters to read?
	regAddress = REG_SIO_RX_LENGTH;
	if (PvRegisterRead(camera, 1, &regAddress, &dataLength, NULL) != ePvErrSuccess)
		return false;

	// It must fit in the user's buffer.
	if (dataLength > bufferLength)
		dataLength = bufferLength;

	if (dataLength > 0)
	{
		// Read the data.
		if (!F_ReadMem(camera, REG_SIO_RX_BUFFER, buffer, dataLength))
			return false;

		// Decrement the camera's read index.
		regAddress = REG_SIO_RX_LENGTH;
		if (PvRegisterWrite(camera, 1, &regAddress, &dataLength, NULL) != ePvErrSuccess)
			return false;
	}

	*pReceiveLength = dataLength;

	return true;
}

//===== LOCAL DATA ============================================================

//===== EVENTS TABLE ==========================================================

BEGIN_DECLARE_EVENT_TYPES()
//    DECLARE_EVENT_TYPE(dAPPEND,wxID_ANY)
END_DECLARE_EVENT_TYPES()

//DEFINE_EVENT_TYPE(dAPPEND)

BEGIN_EVENT_TABLE(CSerialWindow, PChildWindow)
    EVT_TIMER(wxID_ANY,CSerialWindow::OnTimer)
    EVT_SIZE(CSerialWindow::OnSize)
    EVT_BUTTON(wxID_ANY,CSerialWindow::OnButtonPushed)
    EVT_CHECKBOX(wxID_ANY,CSerialWindow::OnButtonPushed)
    EVT_COMBOBOX(wxID_ANY,CSerialWindow::OnComboChanged)
    EVT_TEXT_ENTER(ID_ENTRY,CSerialWindow::OnEnterPressed)
END_EVENT_TABLE()

//===== CLASS DEFINITION ======================================================

/*
 * Method:    CSerialWindow()
 * Purpose:   constructor
 * Comments:  none
 */
CSerialWindow::CSerialWindow(PChildWindowObserver& aObserver,const tPvCameraInfoEx& aInfo,tPvHandle aHandle)
    : PChildWindow(aObserver,wxT(""),wxSize(kInitWidth,kInitHeight),wxRESIZE_BORDER) , iHandle(aHandle)
{
    wxString lString;
    
    iMain        = NULL;
    iPanelTop    = NULL;
    iPanelBottom = NULL;
    iList        = NULL;

    // format the title of the window
    lString =  wxString(aInfo.SerialNumber,wxConvUTF8);
    lString += _T(" (");
    lString += wxString(aInfo.CameraName,wxConvUTF8);
    lString += _T(") - Serial IO");
    // and set it
    SetTitle(lString);
    // Give it an icon
    SetIcon(wxIcon(bitmap10));
    // center on the screen
    CentreOnScreen(wxBOTH);
    // set the minimum size
    SetMinSize(wxSize(kInitWidth,kInitHeight));
    
    // create the main sizer
    iMain = new wxBoxSizer(wxVERTICAL);
    if(iMain)
    {    
        // create the top panel
        iPanelTop = new wxPanel(this,wxID_ANY,wxDefaultPosition,wxSize(kInitWidth,kPanelHeightTop));
        
        if(iPanelTop)
        {
            // set the minimum size of the panel
            iPanelTop->SetMinSize(wxSize(kInitWidth,kPanelHeightTop));
            
            if(iPanelTop)
            {
                wxGridSizer*    lSizer = new wxGridSizer(6,2,2);
                wxStaticText*   lLabel;
                
                iPanelTop->SetSizer(lSizer);
                
                /// 1st line
                
                lLabel      = new wxStaticText(iPanelTop,wxID_ANY,_T("Baud Rate"),wxDefaultPosition,wxDefaultSize,wxALIGN_RIGHT);
                iComboBaud  = new wxComboBox(iPanelTop,ID_BAUDRATE,_T(""),wxDefaultPosition,wxSize(150,20),0,NULL,wxCB_DROPDOWN|wxCB_READONLY);
                
                lSizer->Add(lLabel,wxSizerFlags().Proportion(0).Align(wxALIGN_LEFT).Expand().Border(wxALL,6));
                lSizer->Add(iComboBaud,wxSizerFlags().Proportion(0).Align(wxALIGN_RIGHT).Expand().Border(wxALL,2));
                
                lLabel         = new wxStaticText(iPanelTop,wxID_ANY,_T("Parity"),wxDefaultPosition,wxDefaultSize,wxALIGN_RIGHT);
                iComboParity   = new wxComboBox(iPanelTop,ID_PARITY,_T(""),wxDefaultPosition,wxSize(150,20),0,NULL,wxCB_DROPDOWN|wxCB_READONLY); 
                iButtonConnect = new wxButton(iPanelTop,ID_CONNECT,_T("Connect"));
                
                lSizer->Add(lLabel,wxSizerFlags().Proportion(0).Align(wxALIGN_RIGHT).Expand().Border(wxALL,6));
                lSizer->Add(iComboParity,wxSizerFlags().Proportion(0).Align(wxALIGN_RIGHT).Expand().Border(wxALL,2)); 
                lSizer->AddStretchSpacer();
                lSizer->Add(iButtonConnect,wxSizerFlags().Proportion(0).Align(wxALIGN_RIGHT).Expand().Border(wxALL,1));               
            
                /// 2nd line
            
                lLabel        = new wxStaticText(iPanelTop,wxID_ANY,_T("Char Len"),wxDefaultPosition,wxDefaultSize,wxALIGN_RIGHT);
                iComboCharLen = new wxComboBox(iPanelTop,ID_CHARLEN,_T(""),wxDefaultPosition,wxSize(150,20),0,NULL,wxCB_DROPDOWN|wxCB_READONLY);
                
                lSizer->Add(lLabel,wxSizerFlags().Proportion(0).Align(wxALIGN_LEFT).Expand().Border(wxALL,6));
                lSizer->Add(iComboCharLen,wxSizerFlags().Proportion(0).Align(wxALIGN_RIGHT).Expand().Border(wxALL,2));
                
                lLabel            = new wxStaticText(iPanelTop,wxID_ANY,_T("Stop Bits"),wxDefaultPosition,wxDefaultSize,wxALIGN_RIGHT);
                iComboStopBits    = new wxComboBox(iPanelTop,ID_STOPBITS,_T(""),wxDefaultPosition,wxSize(150,20),0,NULL,wxCB_DROPDOWN|wxCB_READONLY); 
                iButtonDisconnect = new wxButton(iPanelTop,ID_DISCONNECT,_T("Disconnect"));
                
                iButtonDisconnect->Disable();
                
                lSizer->Add(lLabel,wxSizerFlags().Proportion(0).Align(wxALIGN_RIGHT).Expand().Border(wxALL,6));
                lSizer->Add(iComboStopBits,wxSizerFlags().Proportion(0).Align(wxALIGN_RIGHT).Expand().Border(wxALL,2)); 
                lSizer->AddStretchSpacer();
                lSizer->Add(iButtonDisconnect,wxSizerFlags().Proportion(0).Align(wxALIGN_RIGHT).Expand().Border(wxALL,1));              
            
                // add it to the sizer
                iMain->Add(iPanelTop,wxSizerFlags().Proportion(0).Align(wxALIGN_TOP).Expand().Border(wxALL,0)); 
                
                // create the list
                iList = new wxListBox(this,wxID_ANY,wxDefaultPosition,wxSize(kInitWidth,kListHeight),0); //wxLB_SINGLE|wxLB_ALWAYS_SB);
                if(iList)
                {
            
                    // add it to the sizer
                    iMain->Add(iList,wxSizerFlags().Proportion(0).Align(wxALIGN_BOTTOM).Expand().Border(wxALL,0));
            
                    // then create the panel
                    iPanelBottom = new wxPanel(this,wxID_ANY,wxDefaultPosition,wxSize(kInitWidth,kPanelHeightBottom));
                    if(iPanelBottom)
                    {
                        // set the minimum size of the panel
                        iPanelBottom->SetMinSize(wxSize(kInitWidth,kPanelHeightBottom));
                        // then create a sizer for the panel
                        iSizer = new wxBoxSizer(wxHORIZONTAL);
                        if(iSizer)
                        {
                            iPanelBottom->SetSizer(iSizer);
                        
                            iEntryField = new wxTextCtrl(iPanelBottom,ID_ENTRY,_T(""),wxDefaultPosition,wxDefaultSize,wxTE_PROCESS_ENTER);
                            iButtonSend = new wxButton(iPanelBottom,ID_SEND,_T("Send"));
                            
                            iEntryField->Disable();
                            iButtonSend->Disable();
                            
                            iSizer->Add(iEntryField,wxSizerFlags().Proportion(1).Align(wxALIGN_LEFT).Expand().Border(wxALL,5));   
                            iSizer->Add(iButtonSend,wxSizerFlags().Proportion(0).Align(wxALIGN_RIGHT).Expand().Border(wxALL,5)); 
                        }   
                    
                        // add it to the sizer
                        iMain->Add(iPanelBottom,wxSizerFlags().Proportion(0).Align(wxALIGN_BOTTOM).Expand().Border(wxALL,0));
                    }  
                        
                    // set the main sizer in the window
                    SetSizer(iMain);
                    // and make that the sizer adjust its size to the window
                    iMain->FitInside(this);
                }
            }
        }
    }
    
    // finaly we create the timer
    iTimer = new wxTimer(this);      
}

/*
 * Method:    ~CSerialWindow()
 * Purpose:   destructor
 * Comments:  none
 */
CSerialWindow::~CSerialWindow()
{
    delete iTimer;
}

/*
 * Method:    OnTimer()
 * Purpose:   called when the timer fires
 * Comments:  none
 */ 
void CSerialWindow::OnTimer(wxTimerEvent& aEvent)
{
    unsigned long lLength;
  
    if(ReadStringFromSerialIO(iHandle,(unsigned char*)&iStringBuffer[iStringIndex],512 - iStringIndex,&lLength) && lLength)
    {
        iStringIndex += lLength;
        if(iStringBuffer[iStringIndex - 1] == '\0' || iStringBuffer[iStringIndex - 1] == '\r')
        {
            if(iStringBuffer[iStringIndex-1] == '\n' || iStringBuffer[iStringIndex - 1] == '\r')
                iStringBuffer[iStringIndex-1] = '\0';
            else
                iStringBuffer[iStringIndex] = '\0';
            iStringIndex = 0;
            
            AddRxString(iStringBuffer);
        }
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
void CSerialWindow::OnSize(wxSizeEvent& aEvent)
{
    wxSize lSize = GetClientSize();

    // force the size to update its widget size and position
    iMain->SetDimension(0,0,lSize.GetWidth(),lSize.GetHeight());
    iMain->Layout();
    iSizer->SetDimension(0,0,iPanelBottom->GetSize().GetWidth(),iPanelBottom->GetSize().GetHeight());  
}

/*
 * Method:    OnOpen()
 * Purpose:   called when the window is open
 * Comments:  none
 */
void CSerialWindow::OnOpen(wxCommandEvent& aEvent)
{ 
    unsigned long lValue[3];
    unsigned long lRegister[3] = {REG_SIO_INQUIRY,REG_SIO_MODE_INQUIRY,REG_SIO_MODE};

    if(PvRegisterRead(iHandle,3,lRegister,lValue,NULL) == ePvErrSuccess && (lValue[0] & 3))
        SetupInitial(lValue[1],lValue[2]);
                
    PChildWindow::OnOpen(aEvent);
}

/*
 * Method:    OnClose()
 * Purpose:   called when the window is been closed
 * Comments:  none
 */
void CSerialWindow::OnClose(wxCloseEvent& aEvent)
{
    PChildWindow::OnClose(aEvent);
}

/*
 * Method:    OnNotification()
 * Purpose:   called when the window is notified of
 *            something
 * Comments:  none
 */
void CSerialWindow::OnNotification(CNotifyEvent& aEvent)
{
}

/*
 * Method:    OnButtonPushed()
 * Purpose:   called when the user pressed one of the buttons
 *            field
 * Comments:  none
 */ 
void CSerialWindow::OnButtonPushed(wxCommandEvent& aEvent)
{
    switch(aEvent.GetId())
    {
        case ID_CONNECT:
        {
            unsigned long lRegisters[3];
	        unsigned long lValues[3];

	        lRegisters[0]   = REG_SIO_TX_CONTROL;
	        lValues[0]	    = 3;  // Reset & enable transmitter
	        lRegisters[1]   = REG_SIO_RX_CONTROL;
	        lValues[1]	    = 3;  // Reset & enable receiver
	        lRegisters[2]   = REG_SIO_RX_STATUS;
	        lValues[2]	    = 0xFFFFFFFF;  // Clear status bits

	        if(PvRegisterWrite(iHandle,3,lRegisters,lValues,NULL) == ePvErrSuccess)
            {
                iStringIndex     = 0;
                iStringBuffer[0] = '\0';
            
                SetupConnected();
                
                iTimer->Start(kRefreshInterval);
            }
            else
            {
                wxMessageBox(L"Sorry, connection failed!",L"Ooops ...",wxOK | wxICON_ERROR,this);
            }            
        
            break;
        }
        case ID_DISCONNECT:
        {
            unsigned long lRegisters[2];
	        unsigned long lValues[2];

	        lRegisters[0]   = REG_SIO_TX_CONTROL;
	        lValues[0]	    = 0;  // Reset & enable transmitter
	        lRegisters[1]   = REG_SIO_RX_CONTROL;
	        lValues[1]	    = 0;  // Reset & enable receiver

	        PvRegisterWrite(iHandle,2,lRegisters,lValues,NULL);

            SetupDisconnected(); 
            
            iTimer->Stop();       
        
            break;
        }        
        case ID_SEND: 
        {
            wxString     lLine = iEntryField->GetLineText(0);
            unsigned int lLength = lLine.Len();
            
            if(lLength && lLength < 512)
            {
                char lString[512];
                         
                strcpy(lString,lLine.mb_str(wxConvUTF8));
                
                lString[lLength++] = '\r';
                lString[lLength] = '\0';
                
                if(WriteStringToSerialIO(iHandle,lString,lLength))
                {
                    lString[lLength-1] = '\0';
                    AddTxString(lString);  
                    iEntryField->Clear();
                }  
                else
                    wxMessageBox(L"Sorry, transmission failed!",L"Ooops ...",wxOK | wxICON_ERROR,this);              
            }
                    
            break;
        }        
    }
}

/*
 * Method:    OnComboChanged()
 * Purpose:   called when the user has changed the value of a combobox
 * Comments:  none
 */        
void CSerialWindow::OnComboChanged(wxCommandEvent& aEvent)
{
    unsigned long lValue;
    unsigned long lRegister = REG_SIO_MODE;

    if(PvRegisterRead(iHandle,1,&lRegister,&lValue,NULL) == ePvErrSuccess)
    {
        switch(aEvent.GetId())
        {
            case ID_BAUDRATE:
            {
                SetBits(lValue,(unsigned long)iComboBaud->GetClientData(iComboBaud->GetSelection()),0,8);  
                break;
            }
            case ID_PARITY:
            {
                SetBits(lValue,(unsigned long)iComboParity->GetClientData(iComboParity->GetSelection()),8,2);
                break;
            }        
            case ID_CHARLEN:
            {
                SetBits(lValue,(unsigned long)iComboCharLen->GetClientData(iComboCharLen->GetSelection()),10,2);
                break;
            }        
            case ID_STOPBITS:
            {
                SetBits(lValue,(unsigned long)iComboStopBits->GetClientData(iComboStopBits->GetSelection()),12,2);
                break;
            }            
        }
        
        PvRegisterWrite(iHandle,1,&lRegister,&lValue,NULL);
    }
}

/*
 * Method:    OnEnterPressed()
 * Purpose:   called when the user has pressed the enter key
 * Comments:  none
 */        
void CSerialWindow::OnEnterPressed(wxCommandEvent& aEvent)
{
    aEvent.SetId(ID_SEND);

    OnButtonPushed(aEvent);
}

/*
 * Method:    SetupInitial()
 * Purpose:   initial setup of the controls
 * Arguments:
 *
 * [i] unsigned int aInquiry, inquiry values
 * [i] unsigned int aModes,   modes values  
 *
 * Return:    none
 * Comments:  none
 */ 
void CSerialWindow::SetupInitial(unsigned long aInquiry,unsigned long aModes)
{
    ///
    for(int i=0;i<10;i++)
    {
        if(aInquiry & (0x1 * (i + 1)))
            iComboBaud->Append(KBaudRates[i],(void*)i);
    } 
    
    for(int i=0;i<3;i++)
    {
        if(aInquiry & (0x10000 * (i + 1)))
            iComboParity->Append(KParities[i],(void*)i);        
    }

    for(int i=0;i<4;i++)
    {
        if(aInquiry & (0x100000 * (i + 1)))
            iComboCharLen->Append(KCharLens[i],(void*)i);        
    }    

    for(int i=0;i<3;i++)
    {
        if(aInquiry & (0x1000000 * (i + 1)))
            iComboStopBits->Append(KStopBits[i],(void*)i);        
    }
    
    ///
    iComboBaud->SetStringSelection(KBaudRates[GetBits(aModes,0,8)]);
    iComboParity->SetStringSelection(KParities[GetBits(aModes,8,2)]);
    iComboCharLen->SetStringSelection(KCharLens[GetBits(aModes,10,2)]);
    iComboStopBits->SetStringSelection(KStopBits[GetBits(aModes,12,2)]);       
}

/*
 * Method:    SetupConnected()
 * Purpose:   setup of the controls when connected
 * Comments:  none
 */         
void CSerialWindow::SetupConnected()
{
    iComboBaud->Disable();
    iComboParity->Disable();
    iComboCharLen->Disable();
    iComboStopBits->Disable();
    
    iButtonConnect->Disable();
    iButtonDisconnect->Enable();
    
    iEntryField->Enable();
    iEntryField->SetFocus();
    iButtonSend->Enable();  
}

/*
 * Method:    SetupDisconnected()
 * Purpose:   setup of the controls when disconnected
 * Comments:  none
 */        
void CSerialWindow::SetupDisconnected()
{
    iComboBaud->Enable();
    iComboParity->Enable();
    iComboCharLen->Enable();
    iComboStopBits->Enable();
    
    iButtonConnect->Enable();
    iButtonDisconnect->Disable();
    
    iEntryField->Disable();
    iButtonSend->Disable();
    iComboBaud->SetFocus();
}

/*
 * Method:    AddRxString()
 * Purpose:   add a received string to the list
 * Arguments:
 *
 * [i] const char* aString, received string
 *
 * Return:    none
 * Comments:  none
 */   
void CSerialWindow::AddRxString(const char* aString)
{
    wxString lString(aString,wxConvUTF8);
    
    lString.Prepend(_T("< "));
    
    iList->Append(lString);
    
    int nCount = iList->GetCount();
    if (nCount > 0)
        iList->SetSelection(nCount-1);     
}

/*
 * Method:    AddTxString()
 * Purpose:   add a transmitted string to the list
 * Arguments:
 *
 * [i] const char* aString, transmitted string
 *
 * Return:    none
 * Comments:  none
 */
void CSerialWindow::AddTxString(const char* aString)
{
    wxString lString(aString,wxConvUTF8);
    
    lString.Prepend(_T("> "));
    
    iList->Append(lString);
    
    int nCount = iList->GetCount();
    if (nCount > 0)
        iList->SetSelection(nCount-1);
}

