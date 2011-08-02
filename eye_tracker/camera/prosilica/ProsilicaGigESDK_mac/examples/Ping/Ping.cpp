/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code, seek out a camera bu using its IP address and display some
| informations on it
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

#ifdef _WINDOWS
#include "StdAfx.h"
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WINDOWS
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <Winsock2.h>
#endif

#if defined(_LINUX) || defined(_QNX) || defined(_OSX)
#include <unistd.h>
#include <time.h>
#include <signal.h>
#include <arpa/inet.h>
#endif

#include <PvApi.h>

#ifndef _WINDOWS
#define TRUE 0
#endif

#if defined(_LINUX) || defined(_QNX) || defined(_OSX)
void Sleep(unsigned int time)
{
    struct timespec t,r;
    
    t.tv_sec    = time / 1000;
    t.tv_nsec   = (time % 1000) * 1000000;    
    
    while(nanosleep(&t,&r)==-1)
        t = r;
}
#endif


int main(int argc, char* argv[])
{
    // initialise the Prosilica API
    if(!PvInitialize())
    { 
        // the only command line argument accepted is the IP@ of the camera to be open
        if(argc>1)
        {
            unsigned long IP = inet_addr(argv[1]);
             
            if(IP)
            {           
                tPvCameraInfo Info;
                tPvIpSettings Conf;
                tPvErr        Err;

                if(!(Err = PvCameraInfoByAddr(IP,&Info,&Conf)))
                {
                    struct in_addr addr;
                
                    printf("-> %s - %s\n",Info.SerialString,Info.DisplayName);
                    printf("Mode supported:\t\t");
                    if(Conf.ConfigModeSupport & ePvIpConfigPersistent)
                        printf("FIXED,");
                    if(Conf.ConfigModeSupport & ePvIpConfigDhcp)
                        printf("DHCP,");
                    if(Conf.ConfigModeSupport & ePvIpConfigAutoIp)
                        printf("AutoIP");
                    printf("\n");
                    printf("Current mode:\t\t");
                    if(Conf.ConfigMode & ePvIpConfigPersistent)
                        printf("FIXED\n");
                    else
                    if(Conf.ConfigMode & ePvIpConfigDhcp)
                        printf("DHCP&AutoIP\n");
                    else
                    if(Conf.ConfigMode & ePvIpConfigAutoIp)
                        printf("AutoIP\n");
                    else
                        printf("None\n");    
    
                    addr.s_addr = Conf.CurrentIpAddress;
                    printf("Current address:\t%s\n",inet_ntoa(addr));
                    addr.s_addr = Conf.CurrentIpSubnet;
                    printf("Current subnet:\t\t%s\n",inet_ntoa(addr));
                    addr.s_addr = Conf.CurrentIpGateway;
                    printf("Current gateway:\t%s\n",inet_ntoa(addr));
                }
                else
                if(Err == ePvErrTimeout)
                    printf("no camera was detected at the address you supplied ...\n");
                else
                    printf("some error (%u) occured\n",Err);    
                
            }
            else
                printf("a valid IP address must be entered\n");
        }
        else
            printf("usage : Ping <IP@>\n");

        // uninitialise the API
        PvUnInitialize();
    }
    else
        printf("failed to initialise the API\n");
    

	return 0;
}
