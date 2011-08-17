/*
| ==============================================================================
| Copyright (C) 2005-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code allow access to the Serial I/O on the camera, using direct
| register IO.
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

// When enabled, the receive timestamp mode is used.
#define RX_TIMESTAMP		0

//===== INCLUDE FILES =========================================================

#include <PvApi.h>
#include <PvRegIo.h>

#include <stdio.h>  
#include <string.h>  
#include <stdlib.h>
    
#if defined(_WINDOWS) || defined(_WIN64)
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#endif

#if defined(_LINUX) || defined(_QNX) || defined(_OSX)
#include <unistd.h>
#include <time.h>
#include <signal.h>
#endif

#if defined(_WINDOWS) || defined(_WIN64)
#define _STDCALL __stdcall
#define snprintf _snprintf
#else
#define _STDCALL
#define TRUE     0
#endif

//===== #DEFINES ==============================================================

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


//===== TYPE DEFINITIONS ======================================================

//===== FUNCTION PROTOTYPES ===================================================

// Handle CTRL-C and other console exceptions.
#if defined(_WINDOWS) || defined(_WIN64)
static BOOL WINAPI F_CtrlCHandler(DWORD dwCtrlType);
#else
static void F_CtrlCHandler(int Signo);
#endif  


// Various serial-io operations (return true if successful):
static bool F_DisplayInfo(tPvHandle camera);
static bool F_SetupSio(tPvHandle camera);
static bool F_ReadData(tPvHandle camera, unsigned char* buffer,
					   unsigned long bufferLength, unsigned long* pReceiveLength);
static bool F_WriteData(tPvHandle camera, const unsigned char* buffer,
						unsigned long length);


// Read a byte array from the camera.
static bool F_ReadMem(tPvHandle camera, unsigned long address,
					  unsigned char* buffer, unsigned long length);

// Write a byte array to the camera.
static bool F_WriteMem(tPvHandle camera, unsigned long address,
					   const unsigned char* buffer, unsigned long length);


#if defined(_LINUX) || defined(_QNX) || defined(_OSX)
void Sleep(unsigned int time)
{
  struct timespec t,r;
    
  t.tv_sec    = time / 1000;
  t.tv_nsec   = (time % 1000) * 1000000;    
    
  while(nanosleep(&t,&r)==-1)
    t = r;
}

void SetConsoleCtrlHandler(void (*func)(int), int junk)
{
  signal(SIGINT, func);
}
#endif

//===== DATA (PUBLIC) =========================================================

//===== DATA (PRIVATE) ========================================================

// Global, so we can close the camera down in F_CtrlCHandler().
static tPvHandle G_Camera;

//===== IMPLEMENTATION ========================================================


int main(int argc, char* argv[])
{

	G_Camera = 0;

	SetConsoleCtrlHandler(F_CtrlCHandler, TRUE);

	printf("Serial IO Test.  Press CTRL-C to end.\n\n");

	try
	{
		tPvCameraInfo	info;
		unsigned long	i;


		if (PvInitialize() != ePvErrSuccess)
			throw "PvAPI initialization";

		printf("Searching for a camera...");

		// Search for a camera.  We expect the user to break out of this
		// CTRL-BREAK if necessary.
		while (1)
		{
			if (PvCameraList(&info, 1, NULL) == 1)
				break;  // Found a camera

			Sleep(500);
			printf(".");
		}

		printf(" found.\n\n");

		if (PvCameraOpen(info.UniqueId, ePvAccessMaster, &G_Camera) != ePvErrSuccess)
			throw "opening camera";

		// 1.  Display serial I/O info:
		if (!F_DisplayInfo(G_Camera))
			throw "info display";

		// 2.  Setup serial port:
		if (!F_SetupSio(G_Camera))
			throw "setup serial port";

		// 3.  Test pattern out & receive display:
		i = 0;
		while (1)
		{
            char			transmitBuffer[100];
            unsigned char	receiveBuffer[1000];
			unsigned long	receiveLength;


			// Output: test pattern

			snprintf(transmitBuffer, sizeof(transmitBuffer),
					  "%010lu %010lu %010lu %010lu\r\n", i, i+1, i+2, i+3);

			if (!F_WriteData(G_Camera, (unsigned char*)transmitBuffer, (unsigned long)strlen(transmitBuffer)))
				throw "write data";

			// Input: read and display data

			if (!F_ReadData(G_Camera, receiveBuffer, sizeof(receiveBuffer)-1, &receiveLength))
				throw "read data";

#if RX_TIMESTAMP
			for (unsigned int i = 0; i < receiveLength; i += 9)
			{
				const __int64 timestamp = ((__int64)receiveBuffer[i] << 56)
											| ((__int64)receiveBuffer[i+1] << 48)
											| ((__int64)receiveBuffer[i+2] << 40)
											| ((__int64)receiveBuffer[i+3] << 32)
											| ((__int64)receiveBuffer[i+4] << 24)
											| ((__int64)receiveBuffer[i+5] << 16)
											| ((__int64)receiveBuffer[i+6] << 8)
											| (__int64)receiveBuffer[i+7];

				printf("%020I64i: %c\n", timestamp, receiveBuffer[i+8]);
			}
#else
			if (receiveLength > 0)
			{
				receiveBuffer[receiveLength] = 0;
				printf("%s", receiveBuffer);
			}
#endif

			Sleep(100);

			i++;
		}

	}
	catch (const char* errString)
	{
		printf("Error: %s\n", errString);

		if (G_Camera)
			PvCameraClose(G_Camera);

		PvUnInitialize();
	}

	return 0;
}


#if defined(_WINDOWS) || defined(_WIN64)
BOOL WINAPI F_CtrlCHandler(DWORD dwCtrlType)
#else
void F_CtrlCHandler(int Signo)
#endif  
{
	if (G_Camera)
		PvCameraClose(G_Camera);

	PvUnInitialize();

	printf("\nBye!\n");
	exit(0);
}


bool F_DisplayInfo(tPvHandle camera)
{
	unsigned long		regAddresses[4];
	unsigned long		regValues[4];


	regAddresses[0] = REG_SIO_INQUIRY;
	regAddresses[1] = REG_SIO_MODE_INQUIRY;
	regAddresses[2] = REG_SIO_TX_INQUIRY;
	regAddresses[3] = REG_SIO_RX_INQUIRY;

	if (PvRegisterRead(camera, 4, regAddresses, regValues, NULL) == ePvErrSuccess)
	{
		printf("SerialIoInquiry:    0x%08lx\n", regValues[0]);
		printf("SerialModeInquiry:  0x%08lx\n", regValues[1]);
		printf("SerialTxInquiry:    0x%08lx\n", regValues[2]);
		printf("SerialRxInquiry:    0x%08lx\n\n", regValues[3]);

#if RX_TIMESTAMP
		if (!(regValues[0] & 0x00000004))
		{
			printf("Timestamp receive mode is not available!\n\n");
			return false;
		}
#endif

		return true;
	}
	else
		return false;
}


bool F_SetupSio(tPvHandle camera)
{
	unsigned long		regAddresses[4];
	unsigned long		regValues[4];


	regAddresses[0] = REG_SIO_MODE;
	regValues[0]	= 0x00000C05;  // 9600, N, 8, 1

	regAddresses[1] = REG_SIO_TX_CONTROL;
	regValues[1]	= 3;  // Reset & enable transmitter

	regAddresses[2] = REG_SIO_RX_CONTROL;
	regValues[2]	= 3;  // Reset & enable receiver

#if RX_TIMESTAMP
	regValues[2] |= 4;  // Use timestamp mode
#endif

	regAddresses[3] = REG_SIO_RX_STATUS;
	regValues[3]	= 0xFFFFFFFF;  // Clear status bits


	if (PvRegisterWrite(camera, 4, regAddresses, regValues, NULL) == ePvErrSuccess)
		return true;
	else
		return false;
}


bool F_ReadData
(
	tPvHandle			camera,
	unsigned char*		buffer,
	unsigned long		bufferLength,
	unsigned long*		pReceiveLength
)
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


bool F_WriteData
(
	tPvHandle				camera,
	const unsigned char*	buffer,
	unsigned long			length
)
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
	if (!F_WriteMem(camera, REG_SIO_TX_BUFFER, buffer, length))
		return false;

	// Write the buffer length.  This triggers transmission.
	regAddress = REG_SIO_TX_LENGTH;
	regValue = length;
	if (PvRegisterWrite(camera, 1, &regAddress, &regValue, NULL) != ePvErrSuccess)
		return false;

	return true;
}


bool F_ReadMem
(
	tPvHandle			camera,
	unsigned long		address,
	unsigned char*		buffer,
	unsigned long		length
)
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


bool F_WriteMem
(
	tPvHandle				camera,
	unsigned long			address,
	const unsigned char*	buffer,
	unsigned long			length
)
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

