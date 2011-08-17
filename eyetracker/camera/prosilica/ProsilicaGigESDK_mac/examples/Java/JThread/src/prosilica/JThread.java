/*
| ==============================================================================
| Copyright (C) 2008 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code, open the first camera found on the host computer and streams
| frames from it until the user terminate it, using a set of frames and a frame
| listener to re-enqueue the frames.
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

import prosilica.Pv;
import prosilica.Pv.tFrame;
import java.nio.ByteBuffer;

public class JThread {

	// number of frames to be used
	protected static final int FramesCount = 4;
	// number of frames to be acquired
	protected static final int FramesLoops = 5000;
	
	/**
	 * A simple thread class which loop the execution of a method until stopped
	 */	
	public static class Looper extends Thread {
		
		private boolean iStop;
		
		/**
		 * Method of the object that will be executed over and over (to be derived)
		 */			
		protected void Loop() {};
		
		/**
		 * start the thread
		 */		
		synchronized public void Start() {
			iStop = false;
			start();
		}
		
		/**
		 * stop the thread (request it to stop)
		 */		
		synchronized public void Stop() {
			iStop = true;
	
		}
		
		public void StopAndWait() {
			
			Stop();
			try {join();} catch (InterruptedException e) {}	
		}
		
		public void Wait()
		{
			try {join();} catch (InterruptedException e) {}		
		}
		
		/**
		 * stop the thread (request it to stop)
		 */	
		synchronized private boolean ShouldStop() {
			return iStop;
		}
		
		/**
		 * run method of the thread
		 */		
		public void run() {
			
			while(!ShouldStop()) Loop();
			
		}
	}
	
	/**
	 * Define a looper to pool some of the threading statistics
	 */	
	public static class MyLooper extends Looper {
		
		MyLooper(Pv.tHandle Camera)
		{
			Handle = Camera;
			Stats1 = new Pv.tUint32();
			Stats2 = new Pv.tUint32();
			Stats3 = new Pv.tFloat32();
			
			Done 	= 0;
			Before 	= 0;
			Total   = 0;
			Elapsed = 0;
			Fps 	= 0;
		}
		
		protected void Loop()
		{
			long Now;
			
			Pv.AttrUint32Get(Handle,"StatFramesCompleted",Stats1);
			Pv.AttrUint32Get(Handle,"StatFramesDropped",Stats2);
			Pv.AttrFloat32Get(Handle,"StatFrameRate",Stats3);
			
			if(Before == 0)
				Before = System.currentTimeMillis();
				
			Now = System.currentTimeMillis();
			Total += Stats1.Value - Done;
			Elapsed += Now - Before;
			
			if(Elapsed >= 500)
			{
				Fps = (float)Total * 1000.0F / (float)Elapsed;
				Elapsed = 0;
				Total = 0;
			}
			
			System.out.format("Completed = %d Dropped = %d Frame rate = %.1f Acquisition rate = %.1f\n",Stats1.Value,Stats2.Value,Stats3.Value,Fps);
			
			Before = System.currentTimeMillis();
			Done   = Stats1.Value;
			
			if(Done >= FramesLoops)
				Stop();
			else
				try { Thread.sleep(250); } catch (InterruptedException e) {}			
		}
		
		private Pv.tHandle  Handle;
		private Pv.tUint32  Stats1;
		private Pv.tUint32  Stats2;
		private Pv.tFloat32 Stats3;
		private long 		Done;
		private long		Before;
		private long 		Total;
		private long 		Elapsed;
		private float		Fps;
		
	}
	
	protected static class FrameCB implements Pv.FrameListener {
		
		public void onFrameEvent(tFrame Frame)
		{	
			if(Frame.Status != Pv.tError.eCancelled)
				Pv.CaptureQueueFrame((Pv.tHandle)Frame.Contexts[0],Frame,this);
		}
	}	

	protected static long WaitForOneCamera(int Timeout)
	{
		long Elapsed = 0;
		long T0;
		int Count = 0;
		
		while(Elapsed < Timeout && Count == 0)
		{
			T0 = System.currentTimeMillis();
			
			try {
				
				Thread.sleep(20);
				
			} catch (InterruptedException e) {}	
			
			Count = Pv.CameraCount();
			Elapsed += System.currentTimeMillis() - T0;
		}

		if(Count > 0)
		{
			Pv.tCameraInfo[] List = new Pv.tCameraInfo[1];
			
			if(Pv.CameraList(List,1) == 1)
				return List[0].UniqueId;
			else
				return 0;
		}
		else
			return 0;
	}
	
	protected static boolean OpenAndSetup(long UID,Pv.tHandle Handle)
	{
		if(Pv.CameraOpen(UID,Pv.tAccessFlags.eMaster,Handle) == Pv.tError.eSuccess)
		{
			return true;
		}
		else
			return false;
	}
	
	protected static boolean UnsetupAndClose(Pv.tHandle Handle)
	{
		if(Pv.CameraClose(Handle) == Pv.tError.eSuccess)
			return true;
		else
			return false;
	}	
	
	protected static boolean StreamStart(Pv.tHandle Handle)
	{
		if(Pv.AttrEnumSet(Handle,"AcquisitionMode","Continuous") == Pv.tError.eSuccess &&
		   Pv.AttrEnumSet(Handle,"FrameStartTriggerMode","Freerun") == Pv.tError.eSuccess)
		{
			if(Pv.CaptureStart(Handle) == Pv.tError.eSuccess)
			{
				if(Pv.CommandRun(Handle,"AcquisitionStart") == Pv.tError.eSuccess)
					return true;
				else
				{
					Pv.CaptureEnd(Handle);
					return false;
				}
			}
			else
				return false;
		}
		else
			return false;
	}	
	
	protected static boolean StreamStop(Pv.tHandle Handle)
	{
	    Pv.CommandRun(Handle,"AcquisitionStop");
	    Pv.CaptureQueueClear(Handle);
	    Pv.CaptureEnd(Handle);
	    return true;
	}	
	
	protected static boolean StreamCapture(Pv.tHandle Handle,Pv.FrameListener Listener)
	{
		Pv.tFrame[] Frames = new Pv.tFrame[FramesCount];
		Pv.tUint32  Length = new Pv.tUint32();
		
		// get the bytes length 
		if(Pv.AttrUint32Get(Handle,"TotalBytesPerFrame",Length) == Pv.tError.eSuccess)
		{
			int i;
			Pv.tError Error = Pv.tError.eSuccess;
			
			// allocate each frame and each corresponding image data buffer
			for(i=0;i<FramesCount;i++)
			{
				Frames[i] = new Pv.tFrame();
				Frames[i].ImageBuffer = ByteBuffer.allocateDirect((int)Length.Value);
				Frames[i].Contexts = new Object[1];
				Frames[i].Contexts[0] = Handle;
			}
			
			// enqueue all the frames now
			for(i=0;i<FramesCount && Error == Pv.tError.eSuccess ;i++)
				Pv.CaptureQueueFrame(Handle, Frames[i], Listener);	
			
			if(Error == Pv.tError.eSuccess)
				return true;
			else
				return false;
		}
		else
			return false;
	}		
	
	/**
	 * @param args
	 */
	public static void main(String[] args)
	{
		// initialize the PvAPI
		if(Pv.Initialize() == Pv.tError.eSuccess)	
		{
			long UID = 0;
			
			// wait until a camera is discovered
			UID = WaitForOneCamera(1500);
						
			if(UID > 0)
			{
				Pv.tHandle Handle = new Pv.tHandle();
				
				if(OpenAndSetup(UID,Handle))
				{
					System.out.println("camera opened");	
					
					if(StreamStart(Handle))
					{
						MyLooper Looper = new MyLooper(Handle);
						FrameCB  CB = new FrameCB();
						
						Looper.Start();
						
						System.out.println("camera is streaming now ...");
						
						if(StreamCapture(Handle,CB))
							Looper.Wait();
						else
						{
							System.out.println("sorry, failed to start the capture ...");
							Looper.StopAndWait();
						}
						
						StreamStop(Handle);
					}
					else
						System.out.println("sorry, failed to start streaming");		
					
					UnsetupAndClose(Handle);
					
					System.out.println("camera closed");	
				}
				else
					System.out.println("sorry, failed to open the camera");	
			}
			else
				System.out.println("no camera detected");
			
			Pv.UnInitialize();
		}
	}

}

