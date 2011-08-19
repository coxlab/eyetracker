/*
| ==============================================================================
| Copyright (C) 2008 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code, stream images from the selected camera. It also allow to save
| the image to disk or to print it.
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

import java.awt.BorderLayout;
import java.awt.Dimension;
import java.awt.Graphics;
import java.awt.Color;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.MouseEvent;
import java.awt.event.MouseListener;
import java.awt.event.WindowEvent;
import java.awt.event.WindowListener;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferByte;
import java.awt.image.DataBufferUShort;
import java.awt.print.PageFormat;
import java.awt.print.Printable;
import java.awt.print.PrinterJob;
import java.awt.Toolkit;

import java.io.File;
import java.io.FileOutputStream;
import javax.imageio.ImageIO;
import java.util.Stack;
import java.nio.ByteBuffer;

import javax.swing.AbstractListModel;
import javax.swing.ComboBoxModel;
import javax.swing.JButton;
import javax.swing.JComboBox;
import javax.swing.JFileChooser;
import javax.swing.JFrame;
import javax.swing.JMenuItem;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JPopupMenu;
import javax.swing.JScrollPane;
import javax.swing.Timer;
//import javax.swing.filechooser.FileNameExtensionFilter;
import javax.swing.SwingUtilities;

public class JStream {
	
	// number of frames to be used
	protected static final int FramesCount = 5;
	
	// Component used to render the frame (as a BufferedImage)
	private static class Display extends JPanel implements ActionListener , MouseListener, Printable {
		
		Display()
		{
			JMenuItem Item;
			
			iMenu = new JPopupMenu();
			Item = new JMenuItem("Save to disk");
			Item.setActionCommand("save");
			Item.addActionListener(this);
			iMenu.add(Item);
			Item = new JMenuItem("Print");
			Item.setActionCommand("print");
			Item.addActionListener(this);
			iMenu.add(Item);			
			
			addMouseListener(this);
			
			iColor = new Color(255,0,0);
			iStats = null;
		}
		
		// set the statistics string to be rendered
		public void SetStats(String Stats)
		{
			iStats = Stats;
		}
		
		// set the BufferedImage to be rendered
		public void setBitmap(BufferedImage Bitmap)
		{
			iBitmap = Bitmap;
		}
		
		// paint the image in the given graphic context (used when sending the image to a Printer)
		public int print(Graphics graphics, PageFormat pageFormat, int pageIndex)
		{
			if(pageIndex >= 1)
				return Printable.NO_SUCH_PAGE; 
			else
			{
				double W,H,L,T;
				double Scale = 0.8;
				
				W = (double)iBitmap.getWidth() * Scale;
				H = (double)iBitmap.getHeight() * Scale;
				L = pageFormat.getImageableX() + (pageFormat.getImageableWidth() / 2.0) - (W / 2.0);
				T = pageFormat.getImageableY() + (pageFormat.getImageableHeight() / 2.0) - (H / 2.0);
				
				graphics.drawImage(iBitmap,
						(int)L,
						(int)T,
						(int)(L + W),
						(int)(T + H),
						0,
						0,
						iBitmap.getWidth(),
						iBitmap.getHeight(),
						null);	
								
			    return Printable.PAGE_EXISTS;
			}
		}
		
		// draw the image on the component
		public void paintComponent(Graphics g)
		{
			if(iBitmap != null)
			{								
				g.drawImage(iBitmap,0,0,null);
				g.setColor(iColor);
				if(iStats != null)
					g.drawString(iStats,1,iBitmap.getHeight() - 1);
			}	
		}
	
		// called when a PopupMenu's item have been selected
		public void actionPerformed(ActionEvent e)
		{
			if(e.getActionCommand() == "save") // save to disk
			{
				File Temp = null;
				
				try {
					Temp = File.createTempFile("Snapshot",".bmp");
				} catch (Exception ex) {
					
				}
			    
			    if(Temp != null && SaveImage2Disk(iBitmap,Temp.toString()))
			    {
				    JFileChooser chooser = new JFileChooser();
				    chooser.setDialogTitle("Select the file and location in which to save the image ...");
				    //chooser.setFileFilter(new FileNameExtensionFilter("BMP Images", "bmp"));		    
			    	
				    if(chooser.showSaveDialog(this) == JFileChooser.APPROVE_OPTION)
				    {
				    	String Path = chooser.getSelectedFile().toString();
				    	
				    	if(Path.endsWith(".bmp") == false)
				    		Path = Path + ".bmp";
				    	
				    	if(Temp.renameTo(new File(Path)) == false)
				    		JOptionPane.showMessageDialog(this,"Sorry, failed to save the image");	
				    	else
				    		Temp.delete();
				    }	
				    else
				    	Temp.delete();
			    }
			    else
			    	JOptionPane.showMessageDialog(this,"Sorry, failed to save the image");	
			}
			else
			if(e.getActionCommand() == "print") // print
			{
				PrinterJob printJob = PrinterJob.getPrinterJob();
				PageFormat pg = printJob.defaultPage();

				pg.setOrientation(PageFormat.LANDSCAPE);
				printJob.setPrintable(this,pg); 

				if ( printJob.printDialog() )
				{
					try
					{
						printJob.print();
					}
					catch ( Exception ex )
					{
						JOptionPane.showMessageDialog(this,"Sorry, printing failed.");
						ex.printStackTrace();
					}
				}			
			}
		}
		
		public void mouseReleased(MouseEvent e)
		{
	        if (iBitmap != null && e.isPopupTrigger()) {
	            iMenu.show(this,e.getX(), e.getY());
	        }				
		}
		
		// save image to disk
		protected boolean SaveImage2Disk(BufferedImage Image,String Path)
		{
			boolean Aok = true;
			
		    try
		    {
		    	FileOutputStream File = new FileOutputStream(Path);
		    	ImageIO.write(Image,"bmp",File);
		    	File.close();
		    }
		    catch (Exception e)
		    {
		    	Aok = false;
		    }
		    
			return Aok;
		}	
		
		// un-used callbacks
		public void mouseClicked(MouseEvent e) {}
		public void mouseEntered(MouseEvent e) {}
		public void mouseExited(MouseEvent e) {}
		public void mousePressed(MouseEvent e) {}
        
		// data
		private BufferedImage iBitmap = null;
		private JPopupMenu	  iMenu;
		private Color		  iColor;
		private String		  iStats;
		
	}
	
	// Window class
	private static class Window extends JFrame implements WindowListener, ActionListener, Pv.FrameListener {
					
		// constructor
		public Window()
		{						
			JPanel content = new JPanel();
			
			content.setLayout(new BorderLayout());
						
			iCModel = new CameraListModel();
			iTList = new Timer(1000,this);
			iTStat = new Timer(250,this);
			iCombo = new JComboBox(iCModel);
			iBSnap = new JButton("Stream");
			iPanel = new Display();
			iSPane = new JScrollPane(iPanel);
						
			iSPane.setPreferredSize(new Dimension(200,200));
			content.add(iCombo,BorderLayout.NORTH);
			content.add(iSPane,BorderLayout.CENTER);
			content.add(iBSnap,BorderLayout.SOUTH);
			
			setTitle("JStream");
			setContentPane(content);
			setSize(800,600);
			setLocation(100,100);
			setDefaultCloseOperation(Window.EXIT_ON_CLOSE);
						
			iBSnap.setEnabled(false);
			iCombo.addActionListener(this);
			iBSnap.addActionListener(this);
			addWindowListener(this);
			
			iBuffer = null;
			iHandle = null;
			iImage  = null;
			iFrames = null;
			iDoneQ  = new FramesQueue();
			iTodoQ  = new FramesQueue();
			iSize   = new Dimension();
		}
		
		// called when the window is opened
		public void windowOpened(WindowEvent e)
		{
			// initialize the API
			if(Pv.Initialize() == Pv.tError.eSuccess)
			{
				// start the timer used to refresh the list of camera
				iTList.start();
				// refresh the cameras list
				iCModel.Refresh();
			}
			else
			{
				JOptionPane.showMessageDialog(this,"Sorry, there was an error during the initialisation");
				dispose();
			}
		}
		
		// called when the window is closing 
		public void windowClosing(WindowEvent e)
		{
			// stop the timer
			iTList.stop();	
			
			// stop and close the camera (if still open and still streaming)
			CameraStop();
			CameraClose();
					
			Pv.UnInitialize();
		}
		
		// called when an action is performed (e.g timer event, widget events)
		public void actionPerformed(ActionEvent e)
		{
			if(e.getSource() == iTStat)
			{				
				iPanel.SetStats(iCount + " " + (iCount - iLast) * 4 + "fps");	
				iLast = iCount;
			}
			else
			if(e.getSource() == iTList)
			{
				long UID;
				
				iCModel.Refresh();
				
				UID = iCModel.getUIDAt(iCombo.getSelectedIndex()); 
				
				if(UID == 0)
				{
					if(iCModel.getSize() > 0)
						iCombo.setSelectedIndex(0);
					else
						iCombo.setSelectedIndex(-1);
				}
			}
			else
			if(e.getSource() == iCombo)
			{
				long UID = iCModel.getUIDAt(iCombo.getSelectedIndex()); 
							
				if(UID > 0)
				{
					CameraClose();
					if(CameraOpen(UID))
						iBSnap.setEnabled(true);
					else
						iBSnap.setEnabled(false);
				}
				else
				{
					if(IsCameraStreaming())
					{
						CameraStop();
						iBSnap.setText("Start");
					}
					
					CameraClose();
					iBSnap.setEnabled(false);
				}
			}	
			else
			if(e.getSource() == iBSnap)
			{
				if(IsCameraStreaming())
				{
					if(CameraStop())
					{
						iTStat.stop();
						iBSnap.setText("Start");
					}
					else
						JOptionPane.showMessageDialog(this,"Sorry, failed to stop the streaming");	
				}
				else
				{
					if(CameraSetup(iSize))
					{
						// update the panel size if it have changed
						if(!iPanel.getPreferredSize().equals(iSize))
						{
							iPanel.setPreferredSize((Dimension)iSize.clone());
													
							if(getExtendedState() == JFrame.NORMAL)
							{
								Dimension Screen = Toolkit.getDefaultToolkit().getScreenSize();
								
								if(iSize.width >= Screen.width * 3 / 4)
									iSize.width -= Screen.width / 4;
								else
									iSize.width += 3;
								if(iSize.height >= Screen.height * 3 / 4)
									iSize.height -= Screen.height / 4;
								else
									iSize.height += 3;	
														
								iSPane.setPreferredSize(iSize);
							
								pack();
							}
							else
								iPanel.revalidate();
						}
						
						if(CameraStart())
						{
							iTStat.start();
							iBSnap.setText("Stop");
						}
						else
							JOptionPane.showMessageDialog(this,"Sorry, failed to start the streaming");
					}
					else
						JOptionPane.showMessageDialog(this,"Sorry, the camera couldn't be setup");
				}	
			}
		}
		
		// un-used callbacks
		public void windowClosed(WindowEvent e) {}
		public void windowActivated(WindowEvent e) {}
		public void windowDeactivated(WindowEvent e) {}
		public void windowDeiconified(WindowEvent e) {}
		public void windowIconified(WindowEvent e) {}
		
		protected synchronized boolean IsCancelled()
		{
			notifyAll();
			return iCancel;
		}
		
		protected synchronized void SetCancel()
		{
			iCancel = true;
			notifyAll();
		}
		
		public void Refresh()
		{
			Pv.tFrame Frame;
						
			// grab the more recently captured frame
			if((Frame = iDoneQ.grab()) != null)
			{	
				//System.out.println(Frame.FrameCount + " : handled in " + (System.currentTimeMillis() - Frame.iPooled));					
				
				iCount++;
				
				if(Frame.Status == Pv.tError.eSuccess)
				{
					FrameToImage(Frame,iImage);																
					iPanel.repaint(0);
				}	

				//long Now = System.currentTimeMillis();
				
				if(Pv.CaptureQueueFrame(iHandle,Frame,this) != Pv.tError.eSuccess)
					iTodoQ.bury(Frame);	
				
				//System.out.println(System.currentTimeMillis() - Now);
			}		
			
			// re-enqueue all the others
			synchronized (iDoneQ) {
				
				while((Frame = iDoneQ.grab()) != null)
					if(Pv.CaptureQueueFrame(iHandle,Frame,this) != Pv.tError.eSuccess)
						iTodoQ.bury(Frame);	
			}
			
		}
		
		public void onFrameEvent(Pv.tFrame Frame)
		{				
			if(!IsCancelled() && Frame.Status != Pv.tError.eCancelled)
			{
				Pv.tFrame Next;
								
				// pull a frame and enqueue it if possible
				if((Next = iTodoQ.pull()) != null)
					if(Pv.CaptureQueueFrame(iHandle,Next,this) != Pv.tError.eSuccess)
						iTodoQ.bury(Next);
				
				// then push the new frame
				iDoneQ.push(Frame);
				
				// trigger the handling of the frame
				SwingUtilities.invokeLater(iDelay);
			}
		}		
       	
		// camera model class
		private static class CameraListModel extends AbstractListModel implements ComboBoxModel {
			
			CameraListModel()
			{
				iCameras = new Pv.tCameraInfo[10];
			}
			
			public Object getSelectedItem()
			{
				return iSelected;
			}

			public void setSelectedItem(Object newValue) {
				iSelected = newValue;
			}
			
			public int getSize()
			{ 
				return iCount;
			}
			
		    public Object getElementAt(int index)
		    { 
		    	return iCameras[index].SerialString + " - " + iCameras[index].DisplayName;
		    }		
		     
		    public void Refresh()
		    {
		    	int lBefore = iCount;
		    	
		    	iCount = Pv.CameraList(iCameras,10);
		    	
		    	if(iCount > 0)
		    	{	
			    	if(iCount == lBefore || lBefore == 0)
			    		fireContentsChanged(this,0,iCount - 1);
			    	else
			    	{
			    		if(iCount < lBefore)
			    			fireIntervalRemoved(this,iCount - 1,iCount  + (lBefore - iCount) - 1);
			    		else
			    			fireIntervalAdded(this,lBefore - 1,iCount - 1);
			    	}
		    	}
		    	else
		    	if(lBefore > 0)
		    	{
		    		fireIntervalRemoved(this,0,lBefore - 1);	
		    	}
		    }
		    
		    public long getUIDAt(int index)
		    {
		    	if(index >= 0 && iCount > 0 && index < iCount)
		    		return iCameras[index].UniqueId;
		    	else
		    		return 0;
		    }
		     
		    private int 				iCount = 0;
		    private Pv.tCameraInfo[] 	iCameras;
		    private Object 				iSelected;
		}
		
		protected boolean CameraOpen(long UID)
		{
			if(iHandle == null)
				iHandle = new Pv.tHandle();
			
			if(Pv.CameraOpen(UID,Pv.tAccessFlags.eMaster,iHandle) == Pv.tError.eSuccess)
				return true;
			else
				return false;
		}
		
		protected boolean CameraClose()
		{
			if(iHandle != null)
			{
				if(Pv.CameraClose(iHandle) == Pv.tError.eSuccess)
					return true;
				else
					return false;
			}
			else
				return false;
		}
		
		protected boolean CameraSetup(Dimension Dim)
		{
			// setup the streaming parameters
			if(Pv.AttrEnumSet(iHandle,"AcquisitionMode","Continuous") == Pv.tError.eSuccess) // &&
			   //Pv.AttrEnumSet(iHandle,"FrameStartTriggerMode","Freerun") == Pv.tError.eSuccess)
			{
				Pv.tUint32  Width  = new Pv.tUint32();
				Pv.tUint32  Height = new Pv.tUint32();
				Pv.tUint32  Length = new Pv.tUint32();
				Pv.tString  Format = new Pv.tString();
				
				// get the bytes length and allocate the frame if necessary
				if(Pv.AttrUint32Get(iHandle,"TotalBytesPerFrame",Length) == Pv.tError.eSuccess &&
				   Pv.AttrUint32Get(iHandle,"Width",Width) == Pv.tError.eSuccess &&
				   Pv.AttrUint32Get(iHandle,"Height",Height) == Pv.tError.eSuccess &&
				   Pv.AttrEnumGet(iHandle,"PixelFormat", Format) == Pv.tError.eSuccess)
				{
					if(iFrames == null)
					{
						iFrames = new Pv.tFrame[FramesCount];
						
						for(int i=0;i<FramesCount;i++)
						{
							iFrames[i] = new Pv.tFrame();
							iFrames[i].ImageBuffer = ByteBuffer.allocateDirect((int)Length.Value);
						}
					}
					else
					{
						for(int i=0;i<FramesCount;i++)
						{						
							if(iFrames[i].ImageBuffer.capacity() < (int)Length.Value)
								iFrames[i].ImageBuffer = ByteBuffer.allocateDirect((int)Length.Value);
						}
					}
					
					if(Format.Value.equals("Mono8"))
						iImage = new BufferedImage((int)Width.Value,(int)Height.Value,BufferedImage.TYPE_BYTE_GRAY);
					else
					if(Format.Value.equals("Mono16")) 	
						iImage = new BufferedImage((int)Width.Value,(int)Height.Value,BufferedImage.TYPE_USHORT_GRAY);
					else
					{
						iImage = new BufferedImage((int)Width.Value,(int)Height.Value,BufferedImage.TYPE_3BYTE_BGR);	
						iBuffer = ByteBuffer.allocateDirect((int)(Width.Value * Height.Value * 3));
					}
									
					Dim.width  = (int)Width.Value;
					Dim.height = (int)Height.Value;
					
					iPanel.setBitmap(iImage);
						
					return true;
				}
				else
					return false;
			}
			else
				return false;
		}
		
		protected boolean CameraStart()
		{
			if(Pv.CaptureStart(iHandle) == Pv.tError.eSuccess)
			{
				boolean Aok = true;
				
				for(int i=0;i<FramesCount && Aok;i++)
					if(Pv.CaptureQueueFrame(iHandle,iFrames[i],this) != Pv.tError.eSuccess)	
						Aok = false;		
								
				iCount = 0;
				iLast  = 0;
				
				if(Aok && Pv.CommandRun(iHandle,"AcquisitionStart") == Pv.tError.eSuccess)
				{
					iCancel = false;	
					
					if(Aok == false)
						CameraStop();
				}
								
				return Aok;
			}
			else
				return false;	
		}
		
		protected boolean CameraStop()
		{			
			if(IsCameraStreaming())
			{
				// for now on any frame received is to be handled as "cancelled"
				SetCancel();
				// continue with the standard streaming shutdown procedure
				Pv.CommandRun(iHandle,"AcquisitionStop");
				//System.out.println("clearing");
				Pv.CaptureQueueClear(iHandle);
				//System.out.println("after");
				Pv.CaptureEnd(iHandle);	
				// clear the queue
				//System.out.println("there");
				iDoneQ.clear();
				iTodoQ.clear();
				//System.out.println("done");
			}
	
			return true;
		}
		
		protected boolean IsCameraStreaming()
		{
			if(iHandle != null)
				return Pv.CaptureQuery(iHandle);
			else
				return false;
		}
		
		// Write a frame into a buffered image
		protected boolean FrameToImage(Pv.tFrame Frame,BufferedImage Image)
		{
			boolean Aok = true;
			
			if(Frame.Format == Pv.tImageFormat.eMono8 || Frame.Format == Pv.tImageFormat.eBgr24)	
			{
				DataBufferByte Buffer = (DataBufferByte)Image.getRaster().getDataBuffer();
				byte[] Data = Buffer.getData();
				
				if(Frame.ImageBuffer.hasArray())
					System.arraycopy(Frame.ImageBuffer.array(),0,Data,0,(int)Frame.ImageSize);
				else
				{
					Frame.ImageBuffer.get(Data,0,(int)Frame.ImageSize);
					Frame.ImageBuffer.rewind();	
				}
			}
			else
			if(Frame.Format == Pv.tImageFormat.eMono16)	
			{
				DataBufferUShort Buffer = (DataBufferUShort)Image.getRaster().getDataBuffer();	
				short[] Data = Buffer.getData();		
				int Shift = Frame.BitDepth - 8;
				
				Frame.ImageBuffer.order(java.nio.ByteOrder.LITTLE_ENDIAN);
				
				for(int i=0,j=0;i<Frame.ImageSize;i+=2,j++)
					Data[j] = (short)(Frame.ImageBuffer.getShort(i) << Shift);
				
				Frame.ImageBuffer.rewind();
			}
			else
			{
				DataBufferByte Buffer = (DataBufferByte)Image.getRaster().getDataBuffer();
				byte[] Data = Buffer.getData();	
				
				Aok = Pv.FrameToBGRBuffer(Frame,iBuffer) == Pv.tError.eSuccess;
				if(Aok)
				{
					iBuffer.get(Data,0,Data.length);
					iBuffer.rewind();	
				}				
			}						
		
			return Aok;
		}	
				
		// Queue of frames
		static class FramesQueue {
			
			public FramesQueue()
			{
				iCount = 0;
				iStack = new Stack<Pv.tFrame>();
			}
			
			/** clear the queue */
			public synchronized void clear()
			{
				iStack.clear();
				iCount  = 0;
				
				notifyAll();
			}
			
			/** grab a frame from the top of the queue */
			public synchronized Pv.tFrame grab()
			{
				Pv.tFrame Frame = null;
				
				if(iCount > 0)
				{			
					Frame = iStack.firstElement();
				
					if(Frame != null)
					{
						iCount--;
						iStack.remove(Frame);
					}
				}
				
				notifyAll();
				
				return Frame;
			}
			
			/** pull a frame from the bottom of the queue */
			public synchronized Pv.tFrame pull()
			{
				Pv.tFrame Frame = null;
				
				if(iCount > 0)
				{			
					Frame = iStack.lastElement();
					
					if(Frame != null)
					{
						iCount--;
						iStack.remove(Frame);
					}
				}
				
				notifyAll();
				
				return Frame;
			}	
			
			/** push a frame on top of the queue */
			public synchronized void push(Pv.tFrame Frame)
			{
				iStack.add(0,Frame);
				iCount++;	
				
				notifyAll();
			}
			
			/** push a frame at the bottom of the queue */
			public synchronized void bury(Pv.tFrame Frame)
			{
				iStack.add(Frame);
				iCount++;
				
				notifyAll();
			}
			
			/** return the number of items on the queue */
			public synchronized int size()
			{
				return iCount;
			}
			
			private int   		  	 iCount = 0;
			private Stack<Pv.tFrame> iStack;
			
		}
						   		
		// data
		private Timer     			iTList;  // timer used for refreshing the camera list
		private Timer     			iTStat;  // timer used for refreshing the statistics
		private JComboBox	  		iCombo;  // cameras combobox
		private JButton				iBSnap;	 // Snap! button
		private CameraListModel 	iCModel; // list of camera model	
		private Pv.tHandle			iHandle; // camera handle
		private Pv.tFrame[]			iFrames; // frames
		private BufferedImage		iImage;	 // image
		private ByteBuffer			iBuffer; // direct byte buffer used to convert the raw data into RGB
		private Display				iPanel;	 // rendering panel
		private JScrollPane			iSPane;	 // scroll pane
		private FramesQueue			iDoneQ;	 // queue of captured frames
		private FramesQueue			iTodoQ;  // queue of handled frames
		private long				iCount;	 // Frame count (as handled)
		private long				iLast;	 // last Frame count
		private boolean				iCancel; // flag used to indicates when the stream is been stopped
		private Dimension 			iSize; 	 // size of the frame to be rendered 
		private Runnable			iDelay = new Runnable() { public void run() { try { Refresh(); } catch (Exception x) {x.printStackTrace();}}};
	}
	
	/**
	 * @param args
	 */
	public static void main(String[] args) {
			
		Window window = new Window();
		
		window.setVisible(true);
	}

}
