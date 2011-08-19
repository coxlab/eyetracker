/*
| ==============================================================================
| Copyright (C) 2006-2007 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| File:         ImageView.cpp
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

#include <ImageView.h>
#include <wx/dc.h>
#include <wx/rawbmp.h>
#include <wx/region.h>
#include <wx/dcclient.h>
#include <wx/dcmemory.h>

//===== DEFINES ===============================================================

#define ULONG_PADDING(x) (((x+3) & ~3) - x)
#define max(a,b) (a > b ? a : b )
#define min(a,b) (a < b ? a : b )

//#define _USE_BITMAP 1

//===== TYPES =================================================================

typedef struct {

    unsigned char LByte;
    unsigned char MByte;
    unsigned char UByte;

} Packed12BitsPixel_t;

//===== EVENTS TABLE ==========================================================

BEGIN_DECLARE_EVENT_TYPES()
    DECLARE_EVENT_TYPE(dADAPT,wxID_ANY)
END_DECLARE_EVENT_TYPES()

DEFINE_EVENT_TYPE(dADAPT)

BEGIN_EVENT_TABLE(CImageView, wxScrolledWindow)
    EVT_SIZE(CImageView::OnSize)
    EVT_COMMAND(wxID_ANY,dADAPT,CImageView::OnAdapt)
    EVT_RIGHT_DOWN(CImageView::OnRightClick)
    EVT_ERASE_BACKGROUND(CImageView::OnEraseBackground) 	
END_EVENT_TABLE()

//===== LOCAL DATA ============================================================

#ifdef _USE_BITMAP
typedef wxPixelData<wxBitmap, wxNativePixelFormat> tPixelData;
#endif

//===== CLASS DEFINITION ======================================================

// convert YUV to RGB
inline void YUV2RGB(int y,int u,int v,int& r,int& g,int& b)
{
   // u and v are +-0.5
   u -= 128;
   v -= 128;

   // Conversion (clamped to 0..255)
   r = min(max(0,(int)(y + 1.370705 * (float)v)),255);
   g = min(max(0,(int)(y - 0.698001 * (float)v - 0.337633 * (float)u)),255);
   b = min(max(0,(int)(y + 1.732446 * (float)u)),255);
}

// convert YUV to RGB
inline void YUV2RGB(int y,int u,int v,int& r,int& g,int& b,bool interpolate)
{
    if(interpolate)
    {
        // u and v are +-0.5
        u -= 128;
        v -= 128;

        // Conversion (clamped to 0..255)
        r = min(max(0,(int)(y + 1.370705 * (float)v)),255);
        g = min(max(0,(int)(y - 0.698001 * (float)v - 0.337633 * (float)u)),255);
        b = min(max(0,(int)(y + 1.732446 * (float)u)),255);
    }
    else
    {
        r = g = b = min(max(0,y),255); 
    }
}

#ifdef _ppc
// sawp a short little endian into big endian
inline unsigned short swap16(unsigned short aValue)
{
    unsigned short lValue = aValue;
    unsigned char* lArray = (unsigned char*)&lValue;
    unsigned char  lTmp;

    lTmp = lArray[0];
    lArray[0] = lArray[1];
    lArray[1] = lTmp;

    return lValue;
}
#endif

/*
 * Method:    CImageView()
 * Purpose:   constructor
 * Comments:  none
 */
CImageView::CImageView(wxWindow* aParent,const wxSize& aSize,tPvInterface aInterface)
    : wxScrolledWindow(aParent,wxID_ANY,wxDefaultPosition,aSize) , iInterface(aInterface)
{
    iScale              = false;
    iColorInterpolate   = false;
    iFreshData          = false;
    iWidth              = 0;
    iHeight             = 0;
    iWRatio             = 1;
    iHRatio             = 1;

    iImage              = NULL;
    iBitmap             = NULL;

    SetBackgroundColour(*wxLIGHT_GREY);
}

/*
 * Method:    ~CImageView()
 * Purpose:   destructor
 * Comments:  none
 */
CImageView::~CImageView()
{
    delete iImage;
    delete iBitmap;
}

/*
 * Method:    Update()
 * Purpose:   update the rendering with a given frame
 * Comments:  none
 */
bool CImageView::Update(tPvFrame* aFrame)
{
    iFreshData = true;  
      
    Process(aFrame);    
    
    wxScrolledWindow::Update();
    
    return true;            
}

/*
 * Method:    SetToScale()
 * Purpose:   instruct the view to scale the image to fit
 *            in the window
 * Comments:  none
 */
void CImageView::SetToScale(bool aScale)
{
    iScale = aScale;
    AdaptToSize();
}

/*
 * Method:    Reset()
 * Purpose:   do whatever need to be done when the streaming is re-started
 * Comments:  none
 */
void CImageView::Reset()
{
}

/*
 * Method:    CopyImage()
 * Purpose:   copy the last image data received into a new image object
 * Comments:  none
 */
wxImage* CImageView::CopyImage()
{
#ifdef _USE_BITMAP

    wxImage* lImage = NULL;

    iLock.Lock();

    if(iBitmap)
        lImage = new wxImage(iBitmap->ConvertToImage());
    else
        lImage = NULL;

    iLock.Unlock();

    return lImage;

#else
    wxImage* lImage = NULL;

    iLock.Lock();

    if(iImage)
        lImage = new wxImage(*iImage);
    else
        lImage = NULL;

    iLock.Unlock();

    return lImage;
#endif
}

/*
 * Method:    Process()
 * Purpose:   process a given frame for rendering
 * Comments:  none
 */
void CImageView::Process(tPvFrame* aFrame)
{

    // if we don't have an image yet, or if the frame size have changed, we need
    // to allocate a new image
#ifdef _USE_BITMAP
    if(!iBitmap || iWidth != aFrame->Width || iHeight != aFrame->Height)
#else
    if(!iImage || iWidth != aFrame->Width || iHeight != aFrame->Height)
#endif
    {

#ifdef _USE_BITMAP
        // delete the previous bitmap (if there was one)
        delete iBitmap;
#else
        // delete the previous image (if there was one)
        delete iImage;
#endif

        // set the data
        iWidth      = aFrame->Width;
        iHeight     = aFrame->Height;

#ifdef _USE_BITMAP
        // create the image
        iBitmap = new wxBitmap(iWidth,iHeight,24);      
#else
        // create the image
        iImage = new wxImage(iWidth,iHeight,false);
#endif

        // and send a async event so that the view take the new
        // image size in consideration
        wxCommandEvent lEvent(dADAPT,wxID_ANY);
        lEvent.SetEventObject(this);
        GetEventHandler()->AddPendingEvent(lEvent);
    }

#ifdef _USE_BITMAP
    if(iBitmap)
    {
        tPixelData              lPixels(*iBitmap);
        tPixelData::Iterator    lData(lPixels);
        long                    lRemainder = lPixels.GetRowStride() - 3 * iWidth; 
#else
    if(iImage)
    {
#endif

        if(!iColorInterpolate)        
        {
            switch(aFrame->Format)
            {
                case ePvFmtBayer8:
                {
                    aFrame->Format = ePvFmtMono8;
                    break;
                }
                case ePvFmtBayer16:
                {
                    aFrame->Format = ePvFmtMono16;
                    break;
                }
                case ePvFmtBayer12Packed:
                {
                    aFrame->Format = ePvFmtMono12Packed;
                    break;
                }
                default:
                    break;
            }
        }

        // copy the frame data into the image
        switch(aFrame->Format)
        {
            case ePvFmtMono8:
            {
#ifdef _USE_BITMAP
                const unsigned char*    lSrc    = (unsigned char*)aFrame->ImageBuffer;
                const unsigned char*    lSrcEnd = lSrc + (iWidth * iHeight);
                unsigned char*          lDest = (unsigned char*)&lData.Data();

                while(lSrc < lSrcEnd)
                {
                    for (unsigned long i = 0;i<iWidth;i++)
                    {
                        lDest[0] = lDest[1] = lDest[2] = *lSrc;                

                        lDest+=3;
                        lSrc++;
                    }
                    
                    if(lRemainder)
                        lDest+=lRemainder;
                }
#else
                unsigned char*       lDest = iImage->GetData();
                const unsigned char* lSrc    = (unsigned char*)aFrame->ImageBuffer;
                const unsigned char* lSrcEnd = lSrc + (iWidth * iHeight);

                while(lSrc < lSrcEnd)
                {
                    lDest[0] = lDest[1] = lDest[2] = *lSrc;
                    lSrc++;
                    lDest += 3;
                }
#endif
                
                break;
            }
            case ePvFmtMono16:
            {
#ifdef _USE_BITMAP
                const unsigned short*   lSrc = (unsigned short*)aFrame->ImageBuffer;
                const unsigned short*   lSrcEnd = lSrc + (iWidth * iHeight);
                const unsigned char     lBitshift = (unsigned char)aFrame->BitDepth - 8;
                unsigned char*          lDest = (unsigned char*)&lData.Data();

                while(lSrc < lSrcEnd)
                {
                    for (unsigned long i = 0;i<iWidth;i++)
                    {
                        #ifdef _ppc
                        lDest[0] = lDest[1] = lDest[2] =  *lSrc << lBitshift;    
                        #else
                        lDest[0] = lDest[1] = lDest[2] =  *lSrc >> lBitshift; 
                        #endif              

                        lSrc++;
                        lDest+=3;
                    }

                    if(lRemainder)
                        lDest+=lRemainder;
                }
#else
                unsigned char*        lDest = iImage->GetData();
                const unsigned short* lSrc = (unsigned short*)aFrame->ImageBuffer;
                const unsigned short* lSrcEnd = lSrc + (iWidth * iHeight);
                const unsigned char   lBitshift = (unsigned char)aFrame->BitDepth - 8;

                while(lSrc < lSrcEnd)
                {
                    #ifdef _ppc
                    lDest[0] = lDest[1] = lDest[2] = *lSrc << lBitshift;
                    #else
                    lDest[0] = lDest[1] = lDest[2] = *lSrc >> lBitshift;
                    #endif
                    lSrc++;
                    lDest += 3;
                }
#endif
                
                break;
            }
            case ePvFmtBayer8:
            {
#ifdef _USE_BITMAP
                unsigned char* lDest = (unsigned char*)&lData.Data();

                PvUtilityColorInterpolate(aFrame,&lDest[0],&lDest[1],&lDest[2],2,lRemainder);

#else
                unsigned char* lDest = iImage->GetData();
                
                PvUtilityColorInterpolate(aFrame,&lDest[0],&lDest[1],&lDest[2],2,0);
#endif     
    
                break;
            }
            case ePvFmtBayer16:
            {
#ifdef _USE_BITMAP
                unsigned char*        lDest     = (unsigned char*)&lData.Data();
                unsigned char*        lSrc      = (unsigned char*)aFrame->ImageBuffer;
                const unsigned short* lSrcS     = (unsigned short*)aFrame->ImageBuffer;
                const unsigned short* lSrcEnd   = lSrcS + (iWidth * iHeight);
                const unsigned char   lBitshift = (unsigned char)aFrame->BitDepth - 8;

                // convert to 8 bit

                while(lSrcS < lSrcEnd)
                {
                    #ifdef _ppc
                    *(lSrc++) = swap16(*(lSrcS++)) >> lBitshift;
                    #else
                    *(lSrc++) = *(lSrcS++) >> lBitshift;
                    #endif
                }
                      
                aFrame->Format = ePvFmtBayer8;

                PvUtilityColorInterpolate(aFrame,&lDest[0],&lDest[1],&lDest[2],2,lRemainder);      
#else

                unsigned char*        lDest = iImage->GetData();
                unsigned char*        lSrc = (unsigned char*)aFrame->ImageBuffer;
                const unsigned short* lSrcS = (unsigned short*)aFrame->ImageBuffer;
                const unsigned short* lSrcEnd = lSrcS + (iWidth * iHeight);
                const unsigned char   lBitshift = (unsigned char)aFrame->BitDepth - 8;

                // convert to 8 bit

                while(lSrcS < lSrcEnd)
                {
                    #ifdef _ppc
                    *(lSrc++) = swap16(*(lSrcS++)) >> lBitshift;
                    #else
                    *(lSrc++) = *(lSrcS++) >> lBitshift;
                    #endif
                }
                      
                aFrame->Format = ePvFmtBayer8;

                PvUtilityColorInterpolate(aFrame,&lDest[0],&lDest[1],&lDest[2],2,0);
#endif                    

                break;
            }
            case ePvFmtRgb24:
            {
#ifdef _USE_BITMAP
                unsigned char*        lDest   = (unsigned char*)&lData.Data();
                const unsigned char*  lSrc    = (unsigned char*)aFrame->ImageBuffer;
                const unsigned char*  lSrcEnd = lSrc + (iWidth * iHeight * 3);

                while(lSrc < lSrcEnd)
                {
                    memcpy(lDest,lSrc,iWidth * 3);

                    lDest += iWidth * 3;
                    lSrc  += iWidth * 3;
                
                    if(lRemainder)
                        lDest+=lRemainder;
                }
#else
                unsigned char*       lDest   = iImage->GetData();
                const unsigned char* lSrc    = (unsigned char*)aFrame->ImageBuffer;
                const unsigned char* lSrcEnd = lSrc + (iWidth * iHeight * 3);

                while(lSrc < lSrcEnd)
                {
                    lDest[0] = lSrc[0];
                    lDest[1] = lSrc[1];
                    lDest[2] = lSrc[2];
                    lSrc += 3;
                    lDest += 3;
                }
#endif
                
                break;
            }
            case ePvFmtBgr24:
            {
#ifdef _USE_BITMAP
                unsigned char*       lDest   = (unsigned char*)&lData.Data();
                const unsigned char* lSrc    = (unsigned char*)aFrame->ImageBuffer;
                const unsigned char* lSrcEnd = lSrc + (iWidth * iHeight * 3);

                while(lSrc < lSrcEnd)
                {
                    for(unsigned long i = 0;i<iWidth;i++)
                    {
                        lDest[0] = lSrc[2];
                        lDest[1] = lSrc[1];
                        lDest[2] = lSrc[0];

                        lSrc += 3;
                        lDest += 3;
                    }

                    if(lRemainder)
                        lDest+=lRemainder;
                } 
#else
                unsigned char*       lDest   = iImage->GetData();
                const unsigned char* lSrc    = (unsigned char*)aFrame->ImageBuffer;
                const unsigned char* lSrcEnd = lSrc + (iWidth * iHeight * 3);

                while(lSrc < lSrcEnd)
                {
                    lDest[0] = lSrc[2];
                    lDest[1] = lSrc[1];
                    lDest[2] = lSrc[0];
                    lSrc += 3;
                    lDest += 3;
                }
#endif            
           
                break;
            }
            case ePvFmtRgba32:
            {
#ifdef _USE_BITMAP
                unsigned char*       lDest   = (unsigned char*)&lData.Data();
                const unsigned char* lSrc    = (unsigned char*)aFrame->ImageBuffer;
                const unsigned char* lSrcEnd = lSrc + (iWidth * iHeight * 4);

                while(lSrc < lSrcEnd)
                {
                    for(unsigned long i = 0;i<iWidth;i++)
                    {
                        lDest[0] = lSrc[0];
                        lDest[1] = lSrc[1];
                        lDest[2] = lSrc[2];
                        lSrc += 4;
                        lDest += 3;
                    }

                    if(lRemainder)
                        lDest+=lRemainder;
                }
#else
                unsigned char*       lDest   = iImage->GetData();
                const unsigned char* lSrc    = (unsigned char*)aFrame->ImageBuffer;
                const unsigned char* lSrcEnd = lSrc + (iWidth * iHeight * 4);

                while(lSrc < lSrcEnd)
                {
                    lDest[0] = lSrc[0];
                    lDest[1] = lSrc[1];
                    lDest[2] = lSrc[2];
                    lSrc += 4;
                    lDest += 3;
                }  
#endif 
                              
                break;
            }
            case ePvFmtBgra32:
            {
#ifdef _USE_BITMAP
                unsigned char*       lDest   = (unsigned char*)&lData.Data();
                const unsigned char* lSrc    = (unsigned char*)aFrame->ImageBuffer;
                const unsigned char* lSrcEnd = lSrc + (iWidth * iHeight * 4);

                while(lSrc < lSrcEnd)
                {
                    for(unsigned long i = 0;i<iWidth;i++)
                    {
                        lDest[0] = lSrc[2];
                        lDest[1] = lSrc[1];
                        lDest[2] = lSrc[0];
                        lSrc += 4;
                        lDest += 3;
                    }

                    if(lRemainder)
                        lDest+=lRemainder;
                }
#else
                unsigned char*       lDest   = iImage->GetData();
                const unsigned char* lSrc    = (unsigned char*)aFrame->ImageBuffer;
                const unsigned char* lSrcEnd = lSrc + (iWidth * iHeight * 4);

                while(lSrc < lSrcEnd)
                {
                    lDest[0] = lSrc[2];
                    lDest[1] = lSrc[1];
                    lDest[2] = lSrc[0];
                    lSrc += 4;
                    lDest += 3;
                }
#endif
                
                break;
            }                
            case ePvFmtYuv411:
            {
#ifdef _USE_BITMAP
                unsigned char*       lDest    = (unsigned char*)&lData.Data();
                unsigned char*       lDestEnd = lDest +  ((iWidth + lRemainder) * iHeight * 3);
                const unsigned char* pSrc     = (unsigned char*) aFrame->ImageBuffer;
                const unsigned char* pSrcEnd  = pSrc + (unsigned int)(iWidth * iHeight * 1.5);
                
                if(iColorInterpolate)
                {                
                    int y1,y2,y3,y4,u,v;
                    int r,g,b;

                    while (pSrc < pSrcEnd)
                    {
                        for(unsigned long i = 0;i<iWidth;i++)
                        {
                            u  = pSrc[0];
                            y1 = pSrc[1];
                            y2 = pSrc[2];
                            v  = pSrc[3];
                            y3 = pSrc[4];
                            y4 = pSrc[5];
                            pSrc+=6;

                            if(lDest < lDestEnd)
                            {
                                YUV2RGB(y1,u,v,r,g,b);
                                lDest[2] = (unsigned char)b;
                                lDest[1] = (unsigned char)g;
                                lDest[0] = (unsigned char)r;
                                lDest += 3;
                                
                                if(lDest < lDestEnd)
                                {
                                    YUV2RGB(y2,u,v,r,g,b);
                                    lDest[2] = (unsigned char)b;
                                    lDest[1] = (unsigned char)g;
                                    lDest[0] = (unsigned char)r;
                                    lDest += 3;
                                    if(lDest < lDestEnd)
                                    {
                                        YUV2RGB(y3,u,v,r,g,b);
                                        lDest[2] = (unsigned char)b;
                                        lDest[1] = (unsigned char)g;
                                        lDest[0] = (unsigned char)r;
                                        lDest += 3;
                                        if(lDest < lDestEnd)
                                        {
                                            YUV2RGB(y4,u,v,r,g,b);
                                            lDest[2] = (unsigned char)b;
                                            lDest[1] = (unsigned char)g;
                                            lDest[0] = (unsigned char)r;
                                            lDest += 3;
                                        }
                                    }
                                }
                            }
                        }

                        if(lRemainder)
                            lDest+=lRemainder;
                    } 
                }
                else
                {
                    int y1,y2,y3,y4;

                    while (pSrc < pSrcEnd)
                    {
                        for(unsigned long i = 0;i<iWidth;i++)
                        {                         
                            y1 = pSrc[1];
                            y2 = pSrc[2];
                            y3 = pSrc[4];
                            y4 = pSrc[5];
                            pSrc+=6;

                            if(lDest < lDestEnd)
                            {
                                lDest[2] = lDest[1] = lDest[0] = (unsigned char)max(0,min(y1,255));
                                lDest += 3;
                                
                                if(lDest < lDestEnd)
                                {
                                    lDest[2] = lDest[1] = lDest[0] = (unsigned char)max(0,min(y2,255));
                                    lDest += 3;
                                    
                                    if(lDest < lDestEnd)
                                    {
                                        lDest[2] = lDest[1] = lDest[0] = (unsigned char)max(0,min(y3,255));
                                        lDest += 3;
                                        
                                        if(lDest < lDestEnd)
                                        {
                                            lDest[2] = lDest[1] = lDest[0] = (unsigned char)max(0,min(y4,255));
                                            lDest += 3;
                                        }
                                    }
                                }
                            }
                        }

                        if(lRemainder)
                            lDest+=lRemainder;
                    }                 
                }
#else
                const unsigned char* pSrc     = (unsigned char*) aFrame->ImageBuffer;
                const unsigned char* pSrcEnd  = pSrc + (unsigned int)(iWidth * iHeight * 1.5);
                unsigned char*       lDest    = iImage->GetData();
                unsigned char*       lDestEnd = lDest +  (iWidth * iHeight * 3);
                
                int y1,y2,y3,y4,u,v;
                int r,g,b;
    
                while (pSrc < pSrcEnd)
                {
                    u  = pSrc[0];
                    y1 = pSrc[1];
                    y2 = pSrc[2];
                    v  = pSrc[3];
                    y3 = pSrc[4];
                    y4 = pSrc[5];
                    pSrc+=6;

                    if(lDest < lDestEnd)
                    {
                        YUV2RGB(y1,u,v,r,g,b);
                        lDest[2] = (unsigned char)b;
                        lDest[1] = (unsigned char)g;
                        lDest[0] = (unsigned char)r;
                        lDest += 3;

                        if(lDest < lDestEnd)
                        {
                            YUV2RGB(y2,u,v,r,g,b);
                            lDest[2] = (unsigned char)b;
                            lDest[1] = (unsigned char)g;
                            lDest[0] = (unsigned char)r;
                            lDest += 3;
                            if(lDest < lDestEnd)
                            {
                                YUV2RGB(y3,u,v,r,g,b);
                                lDest[2] = (unsigned char)b;
                                lDest[1] = (unsigned char)g;
                                lDest[0] = (unsigned char)r;
                                lDest += 3;
                                if(lDest < lDestEnd)
                                {
                                    YUV2RGB(y4,u,v,r,g,b);
                                    lDest[2] = (unsigned char)b;
                                    lDest[1] = (unsigned char)g;
                                    lDest[0] = (unsigned char)r;
                                    lDest += 3;
                                }
                            }
                        }
                     }
                                    
                }  
#endif
   
                break;
            }
            case ePvFmtYuv422:
            {
#ifdef _USE_BITMAP
                unsigned char*       lDest    = (unsigned char*)&lData.Data();
                unsigned char*       lDestEnd = lDest +  ((iWidth + lRemainder) * iHeight * 3);
                const unsigned char* pSrc    = (unsigned char*) aFrame->ImageBuffer;
                const unsigned char* pSrcEnd = pSrc + (iWidth * iHeight * 2);            
            
                if(iColorInterpolate)
                {
                    int y1,y2,u,v;
                    int r,g,b;
                                
                    while (pSrc < pSrcEnd)
                    {
                        for(unsigned long i = 0;i<iWidth;i++)
                        {
                            u  = pSrc[0];
                            y1 = pSrc[1];
                            v  = pSrc[2];
                            y2 = pSrc[3];
                            pSrc+=4;

                            if(lDest < lDestEnd)
                            {
                                YUV2RGB(y1,u,v,r,g,b);
                                lDest[2] = (unsigned char)b;
                                lDest[1] = (unsigned char)g;
                                lDest[0] = (unsigned char)r;
                                lDest += 3;
                                if(lDest < lDestEnd)
                                {
                                    YUV2RGB(y2,u,v,r,g,b);
                                    lDest[2] = (unsigned char)b;
                                    lDest[1] = (unsigned char)g;
                                    lDest[0] = (unsigned char)r;
                                    lDest += 3;
                                }
                            }
                        }

                        if(lRemainder)
                            lDest+=lRemainder;
                    }
                }
                else
                {
                    int y1,y2;
                                
                    while (pSrc < pSrcEnd)
                    {
                        for(unsigned long i = 0;i<iWidth;i++)
                        {
                            y1 = pSrc[1];
                            y2 = pSrc[3];
                            pSrc+=4;

                            if(lDest < lDestEnd)
                            {
                                lDest[2] = lDest[1] = lDest[0] = (unsigned char)max(0,min(y1,255));
                                lDest += 3;
                                
                                if(lDest < lDestEnd)
                                {
                                    lDest[2] = lDest[1] = lDest[0] = (unsigned char)max(0,min(y2,255));
                                    lDest += 3;
                                }
                            }
                        }
                        
                        if(lRemainder)
                            lDest += lRemainder;
                    }
                }
#else
                const unsigned char* pSrc     = (unsigned char*) aFrame->ImageBuffer;
                const unsigned char* pSrcEnd  = pSrc + (iWidth * iHeight * 2);
                unsigned char*       lDest    = iImage->GetData();
                unsigned char*       lDestEnd = lDest +  (iWidth * iHeight * 3);
                
                int y1,y2,u,v;
                int r,g,b;
                            
                while (pSrc < pSrcEnd)
                {
                    u  = pSrc[0];
                    y1 = pSrc[1];
                    v  = pSrc[2];
                    y2 = pSrc[3];
                    pSrc+=4;

                    if(lDest < lDestEnd)
                    {
                        YUV2RGB(y1,u,v,r,g,b);
                        lDest[2] = (unsigned char)b;
                        lDest[1] = (unsigned char)g;
                        lDest[0] = (unsigned char)r;
                        lDest += 3;
                        if(lDest < lDestEnd)
                        {
                            YUV2RGB(y2,u,v,r,g,b);
                            lDest[2] = (unsigned char)b;
                            lDest[1] = (unsigned char)g;
                            lDest[0] = (unsigned char)r;
                            lDest += 3;
                        }
                    }
                }
#endif
            
                break;                                                
            }
            case ePvFmtYuv444:
            {
#ifdef _USE_BITMAP
                unsigned char*       lDest    = (unsigned char*)&lData.Data();
                unsigned char*       lDestEnd = lDest +  ((iWidth + lRemainder) * iHeight * 3);
                const unsigned char* pSrc     = (unsigned char*) aFrame->ImageBuffer;
                const unsigned char* pSrcEnd  = pSrc + (iWidth * iHeight * 3);            
            
                if(iColorInterpolate)
                {
                    int y2,y1,u,v;
                    int r,g,b;

                    r = b = g = 0;

                    while (pSrc < pSrcEnd)
                    {
                        for(unsigned long i = 0;i<iWidth;i++)
                        {
                            u  = pSrc[0];
                            y1 = pSrc[1];
                            v  = pSrc[2];
                            y2 = pSrc[4];
                            pSrc+=6;

                            if(lDest < lDestEnd)
                            {
                                YUV2RGB(y1,u,v,r,g,b);
                                lDest[2] = (unsigned char)b;
                                lDest[1] = (unsigned char)g;
                                lDest[0] = (unsigned char)r;
                                lDest += 3;
                                
                                if(lDest < lDestEnd)
                                {
                                    YUV2RGB(y2,u,v,r,g,b);
                                    lDest[2] = (unsigned char)b;
                                    lDest[1] = (unsigned char)g;
                                    lDest[0] = (unsigned char)r;
                                    lDest += 3;
                                }
                            }
                        }

                        if(lRemainder)
                            lDest+=lRemainder;

                    }
                }
                else
                {
                    int y2,y1;

                    while (pSrc < pSrcEnd)
                    {
                        for(unsigned long i = 0;i<iWidth;i++)
                        {
                            y1 = pSrc[1];
                            y2 = pSrc[4];
                            pSrc+=6;

                            if(lDest < lDestEnd)
                            {
                                lDest[2] = lDest[1] = lDest[0] = (unsigned char)max(0,min(y1,255));
                                lDest += 3;
                                
                                if(lDest < lDestEnd)
                                {
                                    lDest[2] = lDest[1] = lDest[0] = (unsigned char)max(0,min(y2,255));
                                    lDest += 3;
                                }
                            }
                        }

                        if(lRemainder)
                            lDest+=lRemainder;

                    }                    
                }
#else
                const unsigned char* pSrc     = (unsigned char*) aFrame->ImageBuffer;
                const unsigned char* pSrcEnd  = pSrc + (iWidth * iHeight * 3);
                unsigned char*       lDest    = iImage->GetData();
                unsigned char*       lDestEnd = lDest +  (iWidth * iHeight * 3);
                int y2,y1,u,v;
                int r,g,b;

                r = b = g = 0;

                while (pSrc < pSrcEnd)
                {
                    u  = pSrc[0];
                    y1 = pSrc[1];
                    v  = pSrc[2];
                    y2 = pSrc[4];
                    pSrc+=6;

                    if(lDest < lDestEnd)
                    {
                        YUV2RGB(y1,u,v,r,g,b);
                        lDest[2] = (unsigned char)b;
                        lDest[1] = (unsigned char)g;
                        lDest[0] = (unsigned char)r;
                        lDest += 3;
                        if(lDest < lDestEnd)
                        {
                            YUV2RGB(y2,u,v,r,g,b);
                            lDest[2] = (unsigned char)b;
                            lDest[1] = (unsigned char)g;
                            lDest[0] = (unsigned char)r;
                            lDest += 3;
                        }
                    }
                }
#endif
            
                break;
            }
		    case ePvFmtMono12Packed:
            {
#ifdef _USE_BITMAP
                unsigned char*              lDest    = (unsigned char*)&lData.Data();
     		    const Packed12BitsPixel_t*  pSrc     = (const Packed12BitsPixel_t*)aFrame->ImageBuffer;
                const Packed12BitsPixel_t*  pSrcEnd  = (const Packed12BitsPixel_t*)((unsigned char*)aFrame->ImageBuffer
                                                        + aFrame->ImageSize);		    
		        const unsigned char			bitshift = (unsigned char)aFrame->BitDepth - 8;
                unsigned short              pixel;                

		        while (pSrc < pSrcEnd)
		        {
			        for (unsigned long i = 0; i < iWidth; i+=2)
                    {
                        pixel = (unsigned short)pSrc->LByte << 4;
                        pixel += ((unsigned short)pSrc->MByte & 0xF0) >> 4;
                        lDest[0] = lDest[1] = lDest[2] = pixel >> bitshift;
                        lDest+=3;                     
                        pixel = (unsigned short)pSrc->UByte << 4;
                        pixel += ((unsigned short)pSrc->MByte & 0x0F) >> 4;
                        lDest[0] = lDest[1] = lDest[2] = pixel >> bitshift;
                        lDest+=3;
                        
                        pSrc++;
                    }

                    if(lRemainder)
                        lDest+=lRemainder;
		        } 
#else
     		    const Packed12BitsPixel_t*  pSrc     = (const Packed12BitsPixel_t*)aFrame->ImageBuffer;
                const Packed12BitsPixel_t*  pSrcEnd  = (const Packed12BitsPixel_t*)((unsigned char*)aFrame->ImageBuffer + aFrame->ImageSize);
		        unsigned char*				pDest    = iImage->GetData();		    
		        const unsigned char			bitshift = (unsigned char)aFrame->BitDepth - 8;
                unsigned short              pixel;

		        while (pSrc < pSrcEnd)
		        {
			        for (unsigned long i = 0; i < iWidth; i+=2)
                    {
                        pixel = (unsigned short)pSrc->LByte << 4;
                        pixel += ((unsigned short)pSrc->MByte & 0xF0) >> 4;
                        pDest[0] = pDest[1] = pDest[2] = pixel >> bitshift;
                        pDest += 3;
                        pixel = (unsigned short)pSrc->UByte << 4;
                        pixel += ((unsigned short)pSrc->MByte & 0x0F) >> 4;
                        pDest[0] = pDest[1] = pDest[2] = pixel >> bitshift;
                        pDest += 3;

                        pSrc++;
                    }
		        }     
#endif       

                break;
            }
            case ePvFmtBayer12Packed:
            {        
#ifdef _USE_BITMAP   
	            const Packed12BitsPixel_t*  pSrc     = (const Packed12BitsPixel_t*)aFrame->ImageBuffer;
                const Packed12BitsPixel_t*  pSrcEnd  = (const Packed12BitsPixel_t*)((unsigned char*)aFrame->ImageBuffer + aFrame->ImageSize);
	            unsigned char*				pDest    = (unsigned char*)aFrame->ImageBuffer;	    
	            const unsigned char			bitshift = (unsigned char)aFrame->BitDepth - 8;
                unsigned short              pixel1,pixel2;
                unsigned char*              lDest    = (unsigned char*)&lData.Data();

	            while (pSrc < pSrcEnd)
	            {
		            for (unsigned long i = 0; i < iWidth; i+=2)
                    {
                        pixel1 = (unsigned short)pSrc->LByte << 4;
                        pixel1 += ((unsigned short)pSrc->MByte & 0xF0) >> 4;
                        
                        pixel2 = (unsigned short)pSrc->UByte << 4;
                        pixel2 += ((unsigned short)pSrc->MByte & 0x0F) >> 4;

                        *(pDest++) = pixel1 >> bitshift;
                        *(pDest++) = pixel2 >> bitshift;

                        pSrc++;
                    }
	            }

	            aFrame->Format = ePvFmtBayer8;

	            PvUtilityColorInterpolate(aFrame,&lDest[0],&lDest[1],&lDest[2],2,lRemainder);
#else
	            const Packed12BitsPixel_t*  pSrc     = (const Packed12BitsPixel_t*)aFrame->ImageBuffer;
                const Packed12BitsPixel_t*  pSrcEnd  = (const Packed12BitsPixel_t*)((unsigned char*)aFrame->ImageBuffer + aFrame->ImageSize);
	            unsigned char*				pDest    = (unsigned char*)aFrame->ImageBuffer;	    
	            const unsigned char			bitshift = (unsigned char)aFrame->BitDepth - 8;
                unsigned short              pixel1,pixel2;
                unsigned char*              lDest = iImage->GetData();

	            while (pSrc < pSrcEnd)
	            {
		            for (unsigned long i = 0; i < iWidth; i+=2)
                    {
                        pixel1 = (unsigned short)pSrc->LByte << 4;
                        pixel1 += ((unsigned short)pSrc->MByte & 0xF0) >> 4;
                        
                        pixel2 = (unsigned short)pSrc->UByte << 4;
                        pixel2 += ((unsigned short)pSrc->MByte & 0x0F) >> 4;

                        *(pDest++) = pixel1 >> bitshift;
                        *(pDest++) = pixel2 >> bitshift;

                        pSrc++;
                    }
	            }

	            aFrame->Format = ePvFmtBayer8;

	            PvUtilityColorInterpolate(aFrame,&lDest[0],&lDest[1],&lDest[2],2,0); 
#endif

                break;
            }
            default:
                break;
        }
              
    }
}

/*
 * Method:    AdaptToSize()
 * Purpose:   adapt the view to the image size
 * Comments:  none
 */
void CImageView::AdaptToSize()
{
    #if defined(__WXMSW__) || defined(__WXMAC__)
    wxRect lView(GetClientSize());
    #else
    wxRect lView(GetSize());
    #endif

    if(!iScale)
    {
        wxRect lImage(wxSize(iWidth,iHeight));
        wxPoint lCimage(lImage.GetWidth() / 2 - 1,lImage.GetHeight() / 2 - 1);
        wxPoint lCview(lView.GetWidth() / 2 - 1,lView.GetHeight() / 2 - 1);
        int lX,lY;
        int lXU,lYU;

        // get the current position of the left/top corner so that we can
        // set the scrollbar to the same position once they are reset
        GetViewStart(&lX,&lY);
        GetScrollPixelsPerUnit(&lXU,&lYU);
         
        if(lView.GetWidth() > iWidth)
            iLeft = lCview.x - lCimage.x;
        else
            iLeft = 0;
        if(lView.GetHeight() > iHeight)
            iTop   = lCview.y - lCimage.y;
        else
            iTop   = 0;

        int lW = max(lView.GetWidth(),iWidth);
        int lH = max(lView.GetHeight(),iHeight);

        if(lW != lView.GetWidth() && lH != lView.GetHeight())
            SetScrollbars(1,1,max(0,lW),max(0,lH),lX * lXU,lY * lYU,true);
        else
        if(lW != lView.GetWidth())
            SetScrollbars(1,1,max(0,lW),0,lX * lXU,lY * lYU,true);
        else
        if(lH != lView.GetHeight())
            SetScrollbars(1,1,0,max(0,lH),lX * lXU,lY * lYU,true);
        else
            SetScrollbars(1,1,0,0,lX * lXU,lY * lYU,true);
    }
    else
    {
        iLeft = 0;
        iTop  = 0;

        iWRatio = (float)lView.GetWidth() / (float)iWidth;
        iHRatio = (float)lView.GetHeight() / (float)iHeight;

        SetScrollbars(1,1,0,0,0,0,true);
    }    
}

/*
 * Method:    OnDraw()
 * Purpose:   called when the view need to be redraw
 * Comments:  none
 */
void CImageView::OnDraw(wxDC& aDC)
{    
     if(iScale)
     {
         #ifdef __WXMSW__
         SetStretchBltMode((HDC)aDC.GetHDC(),COLORONCOLOR);
         #endif
         aDC.SetUserScale(iWRatio,iHRatio);
     }
    
#ifdef _USE_BITMAP
     if(iBitmap)
        aDC.DrawBitmap(*iBitmap,iLeft,iTop,false);
#else
     // blit the image
     if(iImage)
     {
         if(iFreshData)
         {
             delete iBitmap;
             iBitmap = new wxBitmap(*iImage);
         }
    
         if(iBitmap)
            aDC.DrawBitmap(*iBitmap,iLeft,iTop,false);
     }
#endif      
    
     // reset the fresh data flag
     iFreshData = false; 
}

/*
 * Method:    OnSize()
 * Purpose:   called when the window size is been changed
 * Comments:  none
 */
void CImageView::OnSize(wxSizeEvent& aEvent)
{
    AdaptToSize();    
    Refresh();
}

/*
 * Method:    OnAdapt()
 * Purpose:   called when the view need to be adapted due to
 *            a change in the image size
 * Comments:  none
 */
void CImageView::OnAdapt(wxCommandEvent& aEvent)
{
    AdaptToSize();
    Refresh();
}

/*
 * Method:    OnRightClick()
 * Purpose:   called when the right button of the mouse
 *            is been pressed
 * Comments:  none
 */
void CImageView::OnRightClick(wxMouseEvent& aEvent)
{
    // forward the event to the parent
    GetParent()->GetEventHandler()->ProcessEvent(aEvent);
}

/*
 * Method:    OnEraseBackground()
 * Purpose:   called when the background of the frame should be
 *            erased
 * Comments:  none
 */ 
void CImageView::OnEraseBackground(wxEraseEvent& aEvent)
{
    wxClientDC* lDC = NULL;
    wxSize lSize    = GetClientSize();
    wxColour lColor = GetBackgroundColour();
    wxRect lRect(iLeft,iTop,iWidth,iHeight);
    wxRegion lRegion(0,0,lSize.GetWidth(),lSize.GetHeight());
    
    // get or create DC
    if (!(lDC = (wxClientDC*)aEvent.GetDC()))
        lDC = new wxClientDC(this);

    // substract with the area occupied by the image
    lRegion.Subtract(lRect);
    // set the clipping to be applied
    lDC->SetClippingRegion(lRegion);
    // set the brush
    lDC->SetBrush(wxBrush(lColor));
    // draw the rectangle
    lDC->DrawRectangle(0,0,lSize.GetWidth(),lSize.GetHeight());
    // then destroy the clipping
    lDC->DestroyClippingRegion();

    // delete DC if created
    if (!aEvent.GetDC())
        delete lDC;
}

