/*
| ==============================================================================
| Copyright (C) 2008-2010 Prosilica.  All Rights Reserved.
|
| Redistribution of this Java file, in original or modified form, without prior
| written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This package defines and implements a Java wrapper around PvAPI C interface,
| to be used with the native shared library "PvJNI".
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

package prosilica;

import java.nio.ByteBuffer;

public class Pv {
	
	/**
	 * Error codes, returned by most methods of the API.
	 */ 	
	public static enum tError {
	
		/** No error */
	    eSuccess,
	    /** Unexpected camera fault */
	    eCameraFault,
	    /** Unexpected fault in PvApi or driver */
	    eInternalFault,
	    /** Camera handle is invalid */
	    eBadHandle,
	    /** Bad parameter to API call */
	    eBadParameter,
	    /** Sequence of API calls is incorrect */
	    eBadSequence, 
	    /** Camera or attribute not found */
	    eNotFound,
	    /** Camera cannot be opened in the specified mode */
	    eAccessDenied, 
	    /** Camera was unplugged */
	    eUnplugged,
	    /** Setup is invalid (an attribute is invalid) */
	    eInvalidSetup,
	    /** System/network resources or memory not available */
	    eResources, 
	    /** 1394 bandwidth not available */
	    eBandwidth,
	    /** Too many frames on queue */
	    eQueueFull,
	    /** Frame buffer is too small */
	    eBufferTooSmall,    
	    /** Frame cancelled by user */
	    eCancelled,
	    /** The data for the frame was lost */
	    eDataLost, 
	    /** Some data in the frame is missing */
	    eDataMissing,
	    /** Timeout during wait */
	    eTimeout, 
	    /** Attribute value is out of the expected range */
	    eOutOfRange,
	    /** Attribute is not this type (wrong access function) */
	    eWrongType,  
	    /**  Attribute write forbidden at this time */
	    eForbidden,
	    /** Attribute is not available at this time */
	    eUnavailable, 
	    /** A firewall is blocking the traffic (Windows only) */
	    eFirewall   	
	}
	
	//----- Camera Enumeration & Information --------------------------------------	
	
	/**
	 * API version number (Major.Minor)
	 */ 	
	public static class tVersion {
		
		/**
		 * major version number
		 */ 
		public int Major;
		/**
		 * Minor version number
		 */ 	
		public int Minor;
		
		public tVersion() {Major = Minor = 0;}
	}
	
	/**
	 * Camera access mode. Used in tCameraInfo data, and as the access mode in OpenCamera().
	 */ 	
	public static class tAccessFlags {
	
		/**
		 * Monitor access: no control, read & listen only
		 */ 		
		public static final int eMonitor = 2;
		/**
		 * Master access: full control
		 */ 	
		public static final int eMaster  = 4;	
	
		public tAccessFlags() {}
	}
	
	public static class tCameraInfoEx {
		
		/** Unique value for each camera */
		public long		UniqueId;
		/** People-friendly camera name (usually part name) */
		public String   CameraName;      
		/**  Name of camera part */
		public String	ModelName;
		/** Manufacturer's part number */
		public String   PartNumber;
		/** Camera's serial number */
		public String   SerialNumber;
		/** Camera's firmware version */
		public String	FirmwareVersion;
		/** A combination of tAccessFlags */
	    public long     PermittedAccess;
	    /** Unique value for each interface */
	    public long     InterfaceId;
		
		public tCameraInfoEx() {}
	}
	
	/**
	 * Camera information (deprecated)
	 */	
	public static class tCameraInfo {
		
		/** Unique value for each camera */	
		public long   	  UniqueId;
		/** Camera's serial number */			
		public String 	  SerialString;
		/** Camera part number */
	    public long       PartNumber;
	    /** Camera part version */
	    public char       PartVersion; 
	    /** A combination of tAccessFlags */
	    public long       PermittedAccess;
	    /** Unique value for each interface */
	    public long       InterfaceId;
	    /** People-friendly camera name */
	    public String     DisplayName;		
		
	    public tCameraInfo() {}
	}
	
	/**
	 * Ethernet configuration modes
	 */		
	public static class tIpConfig {
		
		/** Use persistent IP settings */
	    public static final int ePersistent = 1; 
	    /** Use DHCP, fall-back to AutoIP */
	    public static final int eDhcp       = 2;
	    /** Use AutoIP only */
	    public static final int eAutoIp     = 4;		
		
	}
	
	/**
	 * Camera Ethernet settings
	 * All IP values are in network byte order (i.e. big endian).
	 */		
	public static class tIpSettings {
		
		/** IP configuration mode: persistent, DHCP & AutoIp, or AutoIp only. */
	    public int    ConfigMode			= 0;
	    /** IP configuration mode supported by the camera */
	    public int    ConfigModeSupport		= 0;

	    /** Current IP address */
	    public byte[] CurrentIpAddress 		= {0,0,0,0};
	    /** Current subnet */
	    public byte[] CurrentIpSubnet  		= {0,0,0,0};
	    /** Current gateway */
	    public byte[] CurrentIpGateway 		= {0,0,0,0};

	    /** Persistent IP address */
	    public byte[] PersistentIpAddr  	= {0,0,0,0};
	    /** Persistent subnet */
	    public byte[] PersistentIpSubnet  	= {0,0,0,0};
	    /** Persistent gateway */
	    public byte[] PersistentIpGateway   = {0,0,0,0};		
		
	    public tIpSettings() {}
	}
	
	// Handle to an open camera
	/**
	 * Handle to an open camera
	 */		
	public static class tHandle {
		
		protected long Handle; // Internal handle to the camera
		
		public tHandle() {Handle = 0;}
	}
	
	//----- Interface-Link Callback -----------------------------------------------
	
	/**
	 * Link (a.k.a interface) event type
	 */ 
	public static enum tLinkEvent
	{
		/** A camera was plugged in */ 	
	    eAdd,
		/** A camera was unplugged */  
	    eRemove,
	}
	
	/**
	 * Link (a.k.a interface) listener interface
	 */ 	
	public static interface LinkListener {
					
		/**
		 * The method is called by the API when an link event occurs. 
		 * 
		 * @param tLinkEvent Event, Event which occurred
		 * @param long UniqueId, 	Unique ID of the camera related to the event
		 */		
		public void onLinkEvent(tLinkEvent Event,long UniqueId);
		
	}
	
	//----- Image Capture ---------------------------------------------------------
	
	/**
	 * Supported image format
	 */ 	
	public enum tImageFormat {
	
		/** Monochrome, 8 bits */
	    eMono8,		 
	    /** Monochrome, 16 bits, data is LSB aligned */
	    eMono16,      
	    /** Bayer-color, 8 bits */
	    eBayer8,      
	    /** Bayer-color, 16 bits, data is LSB aligned */
	    eBayer16,     
	    /** RGB, 8 bits x 3 */
	    eRgb24,       
	    /** RGB, 16 bits x 3, data is LSB aligned */
	    eRgb48,       
	    /** YUV 411 */
	    eYuv411,      
	    /** YUV 422 */
	    eYuv422,      
	    /** YUV 444 */
	    eYuv444,      
	    /** BGR, 8 bits x 3 */
	    eBgr24,       
	    /** RGBA, 8 bits x 4 */
	    eRgba32,      
	    /** BGRA, 8 bits x 4 */
	    eBgra32,   
	    /** Monochrome, 12 bits */
	    eMono12Packed,
	    /** Bayer-color, 12 bits, packed */
	    eBayer12Packed
	}	
	
	/**
	 * Bayer pattern.  Applicable only when a Bayer-color camera is sending raw bayer data.
	 */ 	
	public enum tBayerPattern {

		/** First line RGRG, second line GBGB... */
	    eRGGB, // 
	    /** First line GBGB, second line RGRG... */
	    eGBRG, // 
	    /** First line GRGR, second line BGBG... */
	    eGRBG, // 
	    /** First line BGBG, second line GRGR.. */
	    eBGGR, // .		

	}
	
	/**
	 * Object passed to QueueFrame()
	 */ 	
	public static class tFrame {
		
		//----- In -----
		
		/** Your image buffer */
		public ByteBuffer 			ImageBuffer;
		/** Your buffer to capture associated header & trailer data for this image. */
		public ByteBuffer 			AncillaryBuffer;
		
		//----- In/Out -----
		
		/** Array of objects for your own usage */
		public Object[]			Contexts;
		
		//----- Out -----
		
		/** Status of this frame */
		public tError			Status;
		/** Image size, in bytes */
		public long       		ImageSize;
		/** Ancillary data size, in bytes */
		public long       		AncillarySize;
		/** Image width */
		public long       		Width;
		/** Image height */
		public long       		Height; 
		/** Start of readout region (left) */
		public long       		RegionX; 
		/** Start of readout region (top) */
		public long       		RegionY; 
		/** Image format */
		public tImageFormat		Format;
		/** Number of significant bits */
	    public int        		BitDepth;
	    /** Bayer pattern, if bayer format */
	    public tBayerPattern 	BayerPattern;
	    /** Rolling frame counter */
	    public long       		FrameCount;
	    /** Time stamp, lower 32-bits */
	    public long       		TimestampLo;
	    /** Time stamp, upper 32-bits */
	    public long       		TimestampHi;
		
	    private long			CachedFrame; // used internally, do NOT use  
	    
	    public tFrame() {ImageBuffer = null;AncillaryBuffer = null;CachedFrame = 0;}
	    
	}
		
	/**
	 * Frame listener interface
	 */
	public static interface FrameListener {
			
		/**
		 * The method is called by the API when a frame is been returned from the API
		 * 
		 * @param tFrame Frame, frame object
		 */			
		public void onFrameEvent(tFrame Frame);
		
	}
	
	/**
	 * Infinite time-out value
	 */	
	public static final long Infinite = 0xFFFFFFFF;
	
	//----- Attributes ------------------------------------------------------------
	
	/**
	 * Attribute data type supported
	 */	
	public static enum tDatatype {
		
	    eUnknown,
	    eCommand,
	    eRaw,
	    eString,
	    eEnum,
	    eUint32,
	    eFloat32,
	    eInt64,
	    eBoolean
		
	}
	
	/**
	 * Attribute flags type
	 */		
	public static class tAttributeFlags {
	
		/** Read access is permitted */
		public static final int eRead  		= 0x01;
		/** Write access is permitted */
		public static final int eWrite 		= 0x02;
		/** The camera may change the value any time */
		public static final int eVolatile	= 0x04; 
		/** Value is read only and never changes */
		public static final int eConst		= 0x08;	
		
	}
	
	/**
	 * Attribute information type
	 */	
	public static class tAttributeInfo {
		
		/** Data type */
	    public tDatatype Datatype; 
	    /** Combination of tAttributeFlags */
	    public int    	 Flags;
	    /** Advanced: see documentation */
	    public String 	 Category; 
	    /** Advanced: see documentation */
	    public String 	 Impact; 		
		
	    public tAttributeInfo() {}
	}
	 
	/**
	 * Structure holding a list of string
	 */		
	public static class tStringsList {
		
		/** Array of String object */
		public String Array[];
		/** Number of Object in the array */
		public int	  Count;
		
		public tStringsList() {Count = 0;}
	}
	
	/**
	 * Value range of an Uint32 attribute
	 */	
	public static class tRangeUint32 {
		
		/** Minimum value */
		public long Min;
		/** Maximum value */
		public long Max;
		
		public tRangeUint32() {Min = Max = 0;}
	}
	
	/**
	 * Value range of an Int64 attribute
	 */	
	public static class tRangeInt64 {
		
		/** Minimum value */
		public long Min;
		/** Maximum value */
		public long Max;
		
		public tRangeInt64() {Min = Max = 0;}
	}	
	
	/**
	 * Value range of an Float32 attribute
	 */
	public static class tRangeFloat32 {
		
		/** Minimum value */
		public float Min;
		/** Maximum value */
		public float Max;
		
		public tRangeFloat32() {Min = Max = 0;}
	}	
	
	/**
	 * Value of a Float32 attribute
	 */
	public static class tFloat32
	{
		/** Value */
		public float Value;
		
		public tFloat32() {Value = 0;}
		public tFloat32(float Number) {Value = Number;}

	}

	/**
	 * Value of a Uint32 attribute
	 */
	public static class tUint32
	{
		/** Value */
		public long Value;
		
		public tUint32() {Value = 0;}
		public tUint32(long Number) {Value = Number;}

	}	
	
	/**
	 * Value of a Int64 attribute
	 */
	public static class tInt64
	{
		/** Value */
		public long Value;
		
		public tInt64() {Value = 0;}
		public tInt64(long Number) {Value = Number;}

	}	
	
	/**
	 * Value of a Boolean attribute
	 */
	public static class tBoolean
	{
		/** Value */
		public boolean Value;
		
		public tBoolean() {Value = false;}
		public tBoolean(boolean Number) {Value = Number;}

	}	
	
	/**
	 * Value of a String attribute
	 */
	public static class tString
	{
		/** Value */
		public String Value;
			
		public tString() {};
	}
	
	
	//----- API Version -----------------------------------------------------------
		
	/**
	 * Retrieve the version number of PvAPI. This function can be called at any time,
	 * including before the API is initialised.
	 * 
	 * @param tVersion Version, version number (output)
	 */	
	public static native void Version(tVersion Version);
	
	//----- API Initialization ----------------------------------------------------
		
	/**
	 * Initialise the PvApi module.  This must be called before any other Pv method is run.
	 * 
	 * @return  eErrSuccess, no error<br>
	 *			eErrResources,  resources requested from the OS were not available<br>           
	 *         	eErrInternalFault, an internal fault occurred
	 */		
	public static native tError Initialize();
	
	/**
	 * Initialise the PvApi module but ask it to not send discovery broadcast.
	 * This must be called before any other Pv method is run.
	 * 
	 * @return  eErrSuccess, no error<br>
	 *			eErrResources,  resources requested from the OS were not available<br>           
	 *         	eErrInternalFault, an internal fault occurred
	 */		
	public static native tError InitializeNoDiscovery();	
	
	/**
	 * Uninitialise the API module.  This will free some resources, and shut down
	 * network activity if applicable.
	 *
	 */		
	public static native void UnInitialize();	
	
	//----- Interface-Link Listener -----------------------------------------------
	
	/**
	 * Register a listener object for notification of link events
	 * The oject's method is called from a thread within PvAPI.  The calls
	 * are sequenced; i.e. they will not be called simultaneously.
	 *
	 * Use LinkListenerUnRegister() to stop receiving callbacks.
	 * 
	 * @param LinkListener Listener, listener object
	 * 
	 * @return  eErrSuccess, no error<br>
	 *			eErrResources, resources requested from the OS were not available
	 *          eErrBadSequence, API isn't initialised
	 */			
	public static native tError LinkListenerRegister(LinkListener Listener);
	
	/**
	 * Unregister a listener object for link events notifications.
	 * 
	 * @param LinkListener Listener, listener object
	 * 
	 * @return  eErrSuccess, no error<br>
	 * 			eErrNotFound,  registered listener was not found<br>
	 *			eErrResources, resources requested from the OS were not available<br>
	 *          eErrBadSequence, API isn't initialised
	 */			
	public static native tError LinkListenerUnRegister(LinkListener Listener);	
	
	//----- Camera Enumeration & Information --------------------------------------
	
	/**
	 * List all the cameras currently visible to PvAPI
	 * 
	 * @param tCameraInfoEx[] List, an array of tCameraInfo to be filled
	 * @param int Length,	      	the maximum number of element the array can accept
	 * 
	 * @return  number of camera listed
	 */				
	public static native int CameraListEx(tCameraInfoEx[] List,int Length);		
	
	/**
	 * List all the cameras currently visible to PvAPI (deprecated)
	 * 
	 * @param tCameraInfo[] List, an array of tCameraInfo to be filled
	 * @param int Length,	      the maximum number of element the array can accept
	 * 
	 * @return  number of camera listed
	 */				
	public static native int CameraList(tCameraInfo[] List,int Length);	
	
	/**
	 *  List all the cameras currently inaccessable by PvAPI.  This lists
	 *  the Ethernet cameras which are connected to the local Ethernet
	 *  network, but are on a different subnet.
	 * 
	 * @param tCameraInfoEx[] List, an array of tCameraInfo to be filled
	 * @param int Length,	        the maximum number of element the array can accept
	 * 
	 * @return  number of camera listed
	 */		
	public static native int CameraListUnreachableEx(tCameraInfoEx[] List,int Length);		
	
	/**
	 *  List all the cameras currently inaccessable by PvAPI.  This lists
	 *  the Ethernet cameras which are connected to the local Ethernet
	 *  network, but are on a different subnet. (deprecated)
	 * 
	 * @param tCameraInfo[] List, an array of tCameraInfo to be filled
	 * @param int Length,	      the maximum number of element the array can accept
	 * 
	 * @return  number of camera listed
	 */		
	public static native int CameraListUnreachable(tCameraInfo[] List,int Length);	
	
	/**
	 * Number of cameras visible to PvAPI (at the time of the call).
	 * Does not include unreachable cameras.
	 * 
	 * @return  The number of cameras detected
	 */			
	public static native int CameraCount();	
		
	/**
	 * Retrieve information on a given camera
	 * 
	 * @param long UniqueId, 		Unique ID of the camera
	 * @param tCameraInfoEx Info,	Camera info will be copied in this object
	 * 
	 * @return  eErrSuccess, no error<br>
	 *          eErrNotFound, the camera was not found (unplugged)<br>
	 *          eErrUnplugged, the camera was found but unplugged during the function call<br>
	 *          eErrResources, resources requested from the OS were not available<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence, API isn't initialised
	 */			
	public static native tError CameraInfoEx(long UniqueId,tCameraInfoEx Info);		
	
	/**
	 * Retrieve information on a given camera (deprecated)
	 * 
	 * @param long UniqueId, 	Unique ID of the camera
	 * @param tCameraInfo Info,	Camera info will be copied in this object
	 * 
	 * @return  eErrSuccess, no error<br>
	 *          eErrNotFound, the camera was not found (unplugged)<br>
	 *          eErrUnplugged, the camera was found but unplugged during the function call<br>
	 *          eErrResources, resources requested from the OS were not available<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence, API isn't initialised
	 */			
	public static native tError CameraInfo(long UniqueId,tCameraInfo Info);	
		
	/**
	 * Retrieve information on a camera, by IP address.  This function is required
	 * if the Ethernet camera is not on the local Ethernet network.<br><p>
	 * The specified camera may not be visible to CameraList(), it might be on a
	 * different ethernet network.  In this case, communication with the camera is
	 * routed to the local gateway. 
	 * 
	 * @param byte[] Address, 		IP address of camera, in network byte order.
	 * @param tCameraInfoEx Info,	Camera info will be copied in this object
	 * 
	 * @return  eErrSuccess, no error<br>
	 *          eErrNotFound, the camera was not found<br>
	 *          eErrUnplugged, the camera was found but unplugged during the function call<br>
	 *          eErrResources, resources requested from the OS were not available<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence, API isn't initialised
	 */	
	public static native tError CameraInfoByAddrEx(byte[] Address,tCameraInfoEx Info);	
	
	/**
	 * Retrieve information on a camera, by IP address.  This function is required
	 * if the Ethernet camera is not on the local Ethernet network.<br><p>
	 * The specified camera may not be visible to CameraList(), it might be on a
	 * different ethernet network.  In this case, communication with the camera is
	 * routed to the local gateway. (deprecated)
	 * 
	 * @param byte[] Address, 	IP address of camera, in network byte order.
	 * @param tCameraInfo Info,	Camera info will be copied in this object
	 * 
	 * @return  eErrSuccess, no error<br>
	 *          eErrNotFound, the camera was not found<br>
	 *          eErrUnplugged, the camera was found but unplugged during the function call<br>
	 *          eErrResources, resources requested from the OS were not available<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence, API isn't initialised
	 */	
	public static native tError CameraInfoByAddr(byte[] Address,tCameraInfo Info);	
	
	/**
	 * Get the IP settings for an Ethernet camera.  This command will work
	 * for all cameras on the local Ethernet network, including "unreachable" cameras.
	 * 
	 * @param long UniqueId,		Unique ID of the camera
	 * @param tIpSettings Settings, IP settings will be copied in this object
	 * 
	 * @return  eErrSuccess, no error<br>
	 *          eErrNotFound, the camera was not found<br>
	 *          eErrResources, resources requested from the OS were not available<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence, API isn't initialised
	 */		
	public static native tError CameraIpSettingsGet(long UniqueId,tIpSettings Settings);
	
	
	/**
	 * Change the IP settings for an Ethernet camera.  This command will work for all
	 * cameras on the local Ethernet network, including "unreachable" cameras.<br><p>
	 * This method will fail if any application on any host has opened the camera. 
	 * 
	 * @param long UniqueId,		Unique ID of the camera
	 * @param tIpSettings Settings, IP settings will be copied from this object
	 * 
	 * @return  eErrSuccess, no error<br>
	 *          eErrNotFound, the camera was not found<br>
	 *          eErrResources, resources requested from the OS were not available<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence, API isn't initialised
	 */	
	public static native tError CameraIpSettingsChange(long UniqueId,tIpSettings Settings);
		
	//----- Opening & Closing -----------------------------------------------------
		
	/**
	 * Open the specified camera.  This method must be called before you can control the
	 * camera. If eErrSuccess is returned, you must eventually call CameraClose().<br><p>
	 *
	 * Alternatively, under special circumstances, you might open an Ethernet
	 * camera with CameraOpenByAddr().
	 * 
	 * @param long UniqueId,	Unique ID of the camera
	 * @param int AccessFlag,	Access flag {monitor, master}
	 * @param tHandle Handle,   Handle to the opened camera is returned here
	 * 
	 * @return  eErrSuccess, 		no error<br>
	 *          eErrAccessDenied, 	the camera couldn't be open in the requested mode<br>
	 *          eErrNotFound,       the camera was not found (unplugged)<br>
	 *          eErrUnplugged,      the camera was found but unplugged during the call<br>
	 *          eErrResources,      resources requested from the OS were not available<br>
	 *          eErrInternalFault,  an internal fault occurred<br>
	 *          eErrBadSequence,    API isn't initialised or camera is already open
	 */		
	public static native tError CameraOpen(long UniqueId,int AccessFlag,tHandle Handle);

	/**
	 * Open the specified camera, by IP address.  This function is required, in place
     * of PvCameraOpen(), if the ethernet camera is not on the local ethernet network.<br><p>
	 *
	 * 
	 * @param byte[] Address, 	IP address of camera, in network byte order.
	 * @param int AccessFlag,	Access flag {monitor, master}
	 * @param tHandle Handle,   Handle to the opened camera is returned here
	 * 
	 * @return  eErrSuccess, 		no error<br>
	 *          eErrAccessDenied, 	the camera couldn't be open in the requested mode<br>
	 *          eErrNotFound,       the camera was not found (unplugged)<br>
	 *          eErrUnplugged,      the camera was found but unplugged during the call<br>
	 *          eErrResources,      resources requested from the OS were not available<br>
	 *          eErrInternalFault,  an internal fault occurred<br>
	 *          eErrBadSequence,    API isn't initialised or camera is already open
	 */		
	public static native tError CameraOpenByAddr(byte[] Address,int AccessFlag,tHandle Handle);
	
	/**
	 * Close the specified camera.
	 * 
	 * @param tHandle Handle,   Handle to the opened camera
	 * 
	 * @return  eErrSuccess, 		no error<br>
	 * 			eErrBadHandle , 	handle is bad<br>
	 *          eErrBadSequence, 	API isn't initialised
	 */		
	public static native tError CameraClose(tHandle Handle);
	
	//----- Image Capture ---------------------------------------------------------
		
	/**
	 * Setup the camera interface for image transfer.  This does not necessarily
	 * start acquisition.<br><p>
	 * 
	 * CaptureStart() must be run before CaptureQueueFrame() is allowed.  But
	 * the camera will not acquire images before the "AcquisitionMode" attribute is
	 * set to a non-idle mode. 
	 * 
	 * @param tHandle Handle,   Handle to the opened camera
	 * 
	 * @return  eErrSuccess, 		no error<br>
	 * 			eErrBadHandle , 	handle is bad<br>
	 *          eErrUnplugged,     	the camera has been unplugged<br>
	 *          eErrResources,     	resources requested from the OS were not available<br>
	 *          eErrInternalFault, 	an internal fault occurred<br>
	 *          eErrBadSequence,   	API isn't initialised or capture already started
	 */		
	public static native tError CaptureStart(tHandle Camera);
		
	/**
	 * Disable the image transfer mechanism.<br><p>
	 * 
	 * This cannot be called until the frame queue is empty.
	 * 
	 * @param tHandle Handle,   Handle to the opened camera
	 * 
	 * @return  eErrSuccess, 		no error<br>
	 * 			eErrBadHandle , 	handle is bad<br>
	 *          eErrUnplugged,     	the camera has been unplugged<br>
	 *          eErrInternalFault, 	an internal fault occurred<br>
	 *          eErrBadSequence,   	API isn't initialised or capture already stopped
	 */		
	public static native tError CaptureEnd(tHandle Camera);
	
	/**
	 * Check to see if a camera interface is ready to transfer images. I.e. has
	 * CaptureStart() been called?
	 * 
	 * @param tHandle Handle,   Handle to the opened camera
	 * 
	 * @return  true if the camera interface is ready to transfer images, false otherwise
	 */		
	public static native boolean CaptureQuery(tHandle Camera);
		
	/**
	 * Queue a frame object for image capture.<br><p>
	 * 
	 * This function returns immediately.  If eErrSuccess is returned, the frame
	 * will remain in the queue until it is complete, or aborted due to an error or
	 * a call to CaptureQueueClear().
	 *
	 * Frames are completed (or aborted) in the order they are queued.
	 *
	 * You can specify a listener object to be notified when the frame is complete,
	 * or you can use CaptureWaitForFrameDone() to block until the frame is complete.
	 *
	 * When the frame listener is been notified, the tFrame object is no longer in
	 * use and you are free to do with it as you please (for example, reuse or
	 * deallocation.)
	 *
	 * Each frame on the queue must be a unique tFrame data structure.     
	 * 
	 * @param tHandle Camera, 			Handle to the camera 
	 * @param tFrame pFrame,  			Frame to queue
	 * @param FrameListener Listener, 	Listener object to be notified when the frame is done;
	 *                                  may be null if there is no listener
	 * 
	 * @return  eErrSuccess, 		no error<br>
	 *          eErrBadHandle,      the handle of the camera is invalid<br>
	 *          eErrUnplugged,      the camera has been unplugged<br> 
	 *          eErrQueueFull,      the frame queue is full<br>
	 *          eErrResources,      resources requested from the OS were not available<br>
	 *          eErrInternalFault,  an internal fault occurred<br>
	 *          eErrBadSequence,    API isn't initialised or capture not started          
	 */		
	public static native tError CaptureQueueFrame(tHandle Camera,tFrame Frame,FrameListener Listener);
	
	/**
	 * Wait for a queued frame to have been captured<br><p>
	 * 
	 * This function cannot be called from the frame listener.
	 * 
	 * When this function returns, the frame object is no longer in use and you
	 * are free to do with it as you please (for example, reuse or deallocation).
	 *
	 * If you are using the frame object notification: this method might return first,
	 * or the listener might be notified first.
	 *
	 * If the specified frame is not on the queue, this function returns
	 * eErrSuccess, since we do not know if the frame just left the queue.
	 * 
	 * @param tHandle Handle,   Handle to the opened camera
	 * @param  tFrame pFrame,   Frame to wait upon
	 * @param  long Timeout,    Wait timeout (in milliseconds); use Pv.Infinite for no timeout
	 * 
	 * @return  eErrSuccess, 	no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrTimeout,       timeout while waiting for the frame
	 *          eErrInternalFault, an internal fault occurred
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError CaptureWaitForFrameDone(tHandle Camera,tFrame Frame,long Timeout);
		
	/**
	 * Empty the frame queue.<br><p>
	 * 
	 * Queued frames are returned with status eErrCancelled.
	 *
	 * CaptureQueueClear() cannot be called from the frame listener.
	 *
	 * When this function returns, no more frames are left on the queue and you
	 * will not receive another listener notification.
	 * 
	 * @param tHandle Handle,   Handle to the opened camera
	 * 
	 * @return  eErrSuccess, 		no error<br>
	 * 			eErrBadHandle , 	handle is bad<br>
	 *          eErrInternalFault, 	an internal fault occurred<br>
	 *          eErrBadSequence,   	API isn't initialised or capture already stopped
	 */	
	public static native tError CaptureQueueClear(tHandle Camera);
	
	/**
	 * Determine the maximum packet size supported by the system.<br><p>
	 * 
	 * The maximum packet size can be limited by the camera, host adapter, and
	 * Ethernet switch.
	 *
	 * CaptureAdjustPacketSize() cannot be run when capture has started.
	 * 
	 * @param tHandle Handle,   		Handle to the opened camera
	 * @param long MaximumPacketSize,   Upper limit: the packet size will
	 *                                  not be set higher than this value.
	 * 
	 * @return  eErrSuccess, 		no error<br>
	 *          eErrBadHandle,      the handle of the camera is invalid<br>
	 *          eErrUnplugged,      the camera has been unplugged<br>
	 *          eErrResources,      resources requested from the OS were not available<br>
	 *          eErrInternalFault,  an internal fault occurred<br>
	 *          eErrBadSequence,    API isn't initialised or capture already started
	 */		
	public static native tError CaptureAdjustPacketSize(tHandle Camera,long MaximumPacketSize);
	
	//----- Attributes ------------------------------------------------------------
		
	/**
	 * List all the attributes for a given camera.
	 * 
	 * @param tHandle Handle,   Handle to the opened camera
	 * @param tStringList List, array of attribute label (object must be "allocated")
	 * 
	 * @return  eErrSuccess, 		no error<br>
	 *          eErrBadHandle,      the handle of the camera is invalid<br>
	 *          eErrUnplugged,      the camera has been unplugged<br>
	 *          eErrInternalFault,  an internal fault occurred<br>
	 *          eErrBadSequence,    API isn't initialised
	 */			
	public static native tError AttrList(tHandle Handle,tStringsList List);
		
	/**
	 * Retrieve information on an camera's attribute
	 * 
	 * @param tHandle Handle,   	Handle to the opened camera
	 * @param String Label,		  	label of the attribute
	 * @param tAttributeInfo Info, 	info are copied here (object must be allocated)
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */
	public static native tError AttrInfo(tHandle Handle,String Label,tAttributeInfo Info);
	
	/**
	 * Check if an attribute exists for the camera.
	 * 
	 * @param tHandle Handle,     Handle to the opened camera
	 * @param String Label,		  label of the attribute
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */	
	public static native tError AttrExists(tHandle Handle,String Label);	
	
	/**
	 * Check if an attribute is available.
	 * 
	 * @param tHandle Handle,     Handle to the opened camera
	 * @param String Label,		  label of the attribute
	 * 
	 * @return  eErrSuccess, 	   the attribute is available<br>
	 * 			eErrUnavailable,   the attribute is not available<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError AttrIsAvailable(tHandle Handle,String Label);	
	
	/**
	 * Check if an attribute's value is valid.
	 * 
	 * @param tHandle Handle,     Handle to the opened camera
	 * @param String Label,		  label of the attribute
	 * 
	 * @return  eErrSuccess, 	   the attribute is available<br>
	 *          eErrOutOfRange,    the attribute is not valid<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrOutOfRange,    the requested attribute is not valid<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */	
	public static native tError AttrIsValid(tHandle Handle,String Label);	
		
	/**
	 * Get the enumeration set for an enumerated attribute.  The set is returned
	 * in an array of strings
	 * 
	 * @param tHandle Handle,    Handle to the opened camera
	 * @param String Label,		 label of the attribute
	 * @param tStringList Range, range is copied here (object must be allocated)
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */	
	public static native tError AttrRangeEnum(tHandle Handle,String Label,tStringsList Range);
		
	/**
	 * Get the value range for a uint32 attribute.
	 * 
	 * @param tHandle Handle,   	Handle to the opened camera
	 * @param String Label,			label of the attribute
	 * @param tRangeUint32 Range,	range is copied here (object must be allocated)
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError AttrRangeUint32(tHandle Handle,String Label,tRangeUint32 Range);
	
	/**
	 * Get the value range for a int64 attribute.
	 * 
	 * @param tHandle Handle,   	Handle to the opened camera
	 * @param String Label,			label of the attribute
	 * @param tRangeInt64 Range,	range is copied here (object must be allocated)
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError AttrRangeInt64(tHandle Handle,String Label,tRangeInt64 Range);	
	
	/**
	 * Get the value range for a float32 attribute.
	 * 
	 * @param tHandle Handle,   	Handle to the opened camera
	 * @param String Label,			label of the attribute
	 * @param tRangeFloat32 Range,	range is copied here (object must be allocated)
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */			
	public static native tError AttrRangeFloat32(tHandle Handle,String Label,tRangeFloat32 Range);
		
	/**
	 * Run a specific command on the camera
	 * 
	 * @param tHandle Handle,   	Handle to the opened camera
	 * @param String Label,			label of the attribute
	 * @param tRangeFloat32 Range,	range is copied here (object must be allocated)
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */			
	public static native tError CommandRun(tHandle Handle,String Label);
		
	/**
	 * Get the value of a string attribute.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param tString Value,  Attribute's value copied here
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */	
	public static native tError AttrStringGet(tHandle Handle,String Label,tString Value);
	
	/**
	 *  Set the value of a string attribute.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param String Value,   Attribute's value
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrForbidden,     the requested attribute forbid this operation<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError AttrStringSet(tHandle Handle,String Label,String Value);
	
	/**
	 *  Set the value of a string attribute.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param tString Value,  Attribute's value
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrForbidden,     the requested attribute forbid this operation<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */
	public static tError AttrStringSet(tHandle Handle,String Label,tString Value)
	{
		return AttrStringSet(Handle,Label,Value.Value);
	}
		
	/**
	 * Get the value of an enumerated attribute.  The enumeration value is a string.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param tString Value,  Attribute's value copied here
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError AttrEnumGet(tHandle Handle,String Label,tString Value);
	
	/**
	 *  Set the value of an enumerated attribute.  The enumeration value is a string.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param String Value,   Attribute's value
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrOutOfRange,    the supplied value is out of range<br>          
	 *          eErrForbidden,     the requested attribute forbid this operation<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */			
	public static native tError AttrEnumSet(tHandle Handle,String Label,String Value);	
	
	/**
	 *  Set the value of an enumerated attribute.  The enumeration value is a string.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param tString Value,  Attribute's value
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrOutOfRange,    the supplied value is out of range          
	 *          eErrForbidden,     the requested attribute forbid this operation<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */	
	public static tError AttrEnumSet(tHandle Handle,String Label,tString Value)
	{
		return AttrEnumSet(Handle,Label,Value.Value);
	}
			
	/**
	 * Get the value of a uint32 attribute.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param tUint32 Value,  value is returned here (must be allocated before)
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError AttrUint32Get(tHandle Handle,String Label,tUint32 Value);
		
	/**
	 *  Set the value of a uint32 attribute.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param long Value,     Attribute's value
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrOutOfRange,    the supplied value is out of range<br>          
	 *          eErrForbidden,     the requested attribute forbid this operation<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError AttrUint32Set(tHandle Handle,String Label,long Value);
	
	/**
	 *  Set the value of a uint32 attribute.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param tUint32 Value,  Attribute's value
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrOutOfRange,    the supplied value is out of range<br>          
	 *          eErrForbidden,     the requested attribute forbid this operation<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */	
	public static tError AttrUint32Set(tHandle Handle,String Label,tUint32 Value)
	{		
		return AttrUint32Set(Handle,Label,Value.Value);
	}
	
	/**
	 * Get the value of a int64 attribute.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param tInt64 Value,   value is returned here (must be allocated before)
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError AttrInt64Get(tHandle Handle,String Label,tInt64 Value);
		
	/**
	 *  Set the value of a int64 attribute.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param long Value,     Attribute's value
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrOutOfRange,    the supplied value is out of range<br>          
	 *          eErrForbidden,     the requested attribute forbid this operation<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError AttrInt64Set(tHandle Handle,String Label,long Value);
	
	/**
	 *  Set the value of an int64 attribute.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param tUint32 Value,  Attribute's value
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrOutOfRange,    the supplied value is out of range<br>          
	 *          eErrForbidden,     the requested attribute forbid this operation<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */	
	public static tError AttrInt64Set(tHandle Handle,String Label,tInt64 Value)
	{		
		return AttrInt64Set(Handle,Label,Value.Value);
	}	
	
	/**
	 * Get the value of a float32 attribute.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param tFloat32 Value, value is returned here (must be allocated before)
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError AttrFloat32Get(tHandle Handle,String Label,tFloat32 Value);
	
	/**
	 *  Set the value of a float32 attribute.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param float Value,    Attribute's value
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrOutOfRange,    the supplied value is out of range<br>          
	 *          eErrForbidden,     the requested attribute forbid this operation<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */	
	public static native tError AttrFloat32Set(tHandle Handle,String Label,float Value);
	
	/**
	 *  Set the value of a float32 attribute.
	 * 
	 * @param tHandle Handle, 	   Handle to the opened camera
	 * @param String Label,	  	   label of the attribute
	 * @param tFloat32 Value, 	   Attribute's value
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrOutOfRange,    the supplied value is out of range<br>          
	 *          eErrForbidden,     the requested attribute forbid this operation<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */	
	public static tError AttrFloat32Set(tHandle Handle,String Label,tFloat32 Value)
	{	
		return AttrFloat32Set(Handle,Label,Value.Value);
	}	
	
	/**
	 * Get the value of a boolean attribute.
	 * 
	 * @param tHandle 	Handle, Handle to the opened camera
	 * @param String 	Label,	  label of the attribute
	 * @param tBoolean 	Value,   value is returned here (must be allocated before)
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError AttrBooleanGet(tHandle Handle,String Label,tBoolean Value);
		
	/**
	 *  Set the value of a boolean attribute.
	 * 
	 * @param tHandle Handle, Handle to the opened camera
	 * @param String Label,	  label of the attribute
	 * @param boolean Value,  Attribute's value
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrOutOfRange,    the supplied value is out of range<br>          
	 *          eErrForbidden,     the requested attribute forbid this operation<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */		
	public static native tError AttrBooleanSet(tHandle Handle,String Label,boolean Value);
	
	/**
	 *  Set the value of an boolean attribute.
	 * 
	 * @param tHandle Handle,  Handle to the opened camera
	 * @param String Label,	   label of the attribute
	 * @param tBoolean Value,  Attribute's value
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged<br>
	 *          eErrNotFound,      the requested attribute doesn't exist<br>
	 *          eErrWrongType,     the requested attribute is not of the correct type<br>
	 *          eErrOutOfRange,    the supplied value is out of range<br>          
	 *          eErrForbidden,     the requested attribute forbid this operation<br>
	 *          eErrInternalFault, an internal fault occurred<br>
	 *          eErrBadSequence,   API isn't initialised
	 */	
	public static tError AttrBooleanSet(tHandle Handle,String Label,tBoolean Value)
	{		
		return AttrBooleanSet(Handle,Label,Value.Value);
	}	
	
	//----- Register access -------------------------------------------------------
	
	/**
	 *  Read the values of a set of camera's registers
	 * 
	 * @param tHandle Handle, 		Handle to the opened camera
	 * @param long NumReads,		number of registers to be read
	 * @param long[] AddressArray,	array of register addresses
	 * @param long[] DataArray,		values are returned here (one per register, must be allocated before)
	 * @param tUint32 NumComplete,	number of registers actually read
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged <br>
	 *          eBadParameter,     NumReads is incorrect<br>
	 *          eAccessDenied,     read is not permitted (or register does not exist
	 */	
	public static native tError RegisterRead(tHandle Handle,long NumReads,long[] AddressArray,long[] DataArray,tUint32 NumComplete);
	
	/**
	 *  Write the values of a set of camera's registers
	 * 
	 * @param tHandle Handle, 		Handle to the opened camera
	 * @param long NumWrites,		number of registers to be wrote
	 * @param long[] AddressArray,	array of register addresses
	 * @param long[] DataArray,		values to be wrote (one per register)
	 * @param tUint32 NumComplete,	number of registers actually wrote
	 * 
	 * @return  eErrSuccess, 	   no error<br>
	 *          eErrBadHandle,     the handle of the camera is invalid<br>
	 *          eErrUnplugged,     the camera has been unplugged <br>
	 *          eBadParameter,     NumWrites is incorrect<br>
	 *          eAccessDenied,     write is not permitted (or register does not exist)
	 */		
	public static native tError RegisterWrite(tHandle Handle,long NumWrites,long[] AddressArray,long[] DataArray,tUint32 NumComplete);
	
	//----- Utility ---------------------------------------------------------------
	
	/**
	 * Convert a native frame into an existing BGR buffer (TYPE_3BYTE_BGR) 
	 * 
	 * @param tFrame Frame,  	 captured frame to be converted
	 * @param ByteBuffer Buffer, buffer to write in
	 * 
	 * @return  eErrSuccess, 		no error<br>
	 *          eBufferTooSmall, 	buffer is too small
	 */	
	public static native tError FrameToBGRBuffer(tFrame Frame,ByteBuffer Buffer);
	
	// load the Native library
	static {
		
		System.loadLibrary("PvJNI");
		
	}
	
}
