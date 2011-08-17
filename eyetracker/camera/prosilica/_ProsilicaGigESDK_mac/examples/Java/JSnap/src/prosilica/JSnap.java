/*
| ==============================================================================
| Copyright (C) 2008 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code, use the camera software trigger to "snap" image from the
| selected camera. It also allow to save the image to disk or to print it.
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

import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.WindowEvent;
import java.awt.event.WindowListener;
import java.awt.event.MouseListener;
import java.awt.event.MouseEvent;

import javax.swing.JOptionPane;
import javax.swing.ComboBoxModel;
import javax.swing.AbstractListModel;
import javax.swing.JFrame;
import javax.swing.JComboBox;
import javax.swing.JScrollPane;
import javax.swing.JButton;
import javax.swing.Timer;
import javax.swing.JPanel;
import javax.swing.JPopupMenu;
import javax.swing.JMenuItem;
import javax.swing.JFileChooser;
//import javax.swing.filechooser.FileNameExtensionFilter;
import java.awt.*;
import java.awt.geom.*;
import java.awt.image.*;
import java.awt.print.*;
import javax.imageio.ImageIO;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;

public class JSnap {

	// Component used to render the frame (as a BufferedImage)
	private static class Display extends JPanel implements ActionListener , MouseListener, Printable{
		
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
		}
		
		// set the BufferedImage to be rendered
		public void setBitmap(BufferedImage Bitmap) {
			
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
				
				graphics.drawImage(	iBitmap,
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
		public void paintComponent(Graphics g) {
			
			Rectangle Rect = getBounds();
			Rectangle Img = new Rectangle();
			
			if(iBitmap != null)
			{
				Shape Original = (Rectangle)g.getClip();	
				Area  Clipping = new Area(Original);
				
				Img.width = iBitmap.getWidth();
				Img.height = iBitmap.getHeight();	
				Img.x = Rect.x + Rect.width / 2 - Img.width / 2;
				Img.y = Rect.y + Rect.height / 2 - Img.height / 2;
				
				Clipping.subtract(new Area(Img));
				
				g.setClip(Clipping);
				g.fillRect(0,0,Rect.width,Rect.height);
				g.setClip(Original);
						
				g.drawImage(iBitmap,Img.x,Img.y,null);	
			}
			else
				g.fillRect(Rect.x,Rect.y,Rect.width,Rect.height);	
		}
	
		// called when a PopupMenu's item have been selected
		public void actionPerformed(ActionEvent e)
		{
			if(e.getActionCommand() == "save") // save to disk
			{
			    JFileChooser chooser = new JFileChooser();
			    chooser.setDialogTitle("Select the file and location in which to save the image ...");
			    //chooser.setFileFilter(new FileNameExtensionFilter("BMP Images", "bmp"));
			    
			    if(chooser.showSaveDialog(this) == JFileChooser.APPROVE_OPTION)
			    {
			    	String Path = chooser.getSelectedFile().toString();
			    	
			    	if(Path.endsWith(".bmp") == false)
			    		Path = Path + ".bmp";
			    	
			    	if(SaveImage2Disk(iBitmap,Path) == false)
			    		JOptionPane.showMessageDialog(this,"Sorry, failed to save the image");	
			    }				
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
		
	}
	
	// Window class
	private static class Window extends JFrame implements WindowListener, ActionListener {
					
		// constructor
		public Window()
		{
			JPanel content = new JPanel();
			
			content.setLayout(new BorderLayout());
						
			iCModel = new CameraListModel();
			iTimer = new Timer(750,this);
			iCombo = new JComboBox(iCModel);
			iBSnap = new JButton("Snap");
			iPanel = new Display();
			iSPane = new JScrollPane(iPanel);
						
			iSPane.setPreferredSize(new Dimension(200,200));
			content.add(iCombo,BorderLayout.NORTH);
			content.add(iSPane,BorderLayout.CENTER);
			content.add(iBSnap,BorderLayout.SOUTH);
			
			setTitle("JSnap");
			setContentPane(content);
			setSize(800,600);
			setLocation(100,100);
			setDefaultCloseOperation(Window.EXIT_ON_CLOSE);
						
			iBSnap.setEnabled(false);
			iCombo.addActionListener(this);
			iBSnap.addActionListener(this);
			addWindowListener(this);
			
			iHandle = null;
			iImage  = null;
		}
		
		// called when the window is opened
		public void windowOpened(WindowEvent e)
		{
			if(Pv.Initialize() == Pv.tError.eSuccess)
			{
				iTimer.start();
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
			CameraClose();
			iTimer.stop();			
			Pv.UnInitialize();
		}
		
		// called when an action is performed (e.g timer event, widget events)
		public void actionPerformed(ActionEvent e)
		{
			if(e.getSource() == iTimer)
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
					CameraClose();
					iBSnap.setEnabled(false);
				}
			}	
			else
			if(e.getSource() == iBSnap)
			{
				if(CameraSetup())
				{
					if(CameraGrab())
					{
						Dimension Size = new Dimension((int)iFrame.Width,(int)iFrame.Height);
						
						FrameToImage(iFrame,iImage);
						iPanel.setBitmap(iImage);
												
						if(iPanel.getPreferredSize() != Size)
						{
							iPanel.setPreferredSize(Size);
							iPanel.revalidate();
						}
						
						iPanel.repaint();
					}
					else
						JOptionPane.showMessageDialog(this,"Sorry, failed to grab a frame");	
				}
				else
					JOptionPane.showMessageDialog(this,"Sorry, the camera couldn't be setup");	
			}
		}
		
		// un-used callbacks
		public void windowClosed(WindowEvent e) {}
		public void windowActivated(WindowEvent e) {}
		public void windowDeactivated(WindowEvent e) {}
		public void windowDeiconified(WindowEvent e) {}
		public void windowIconified(WindowEvent e) {}
       	
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
		
		protected boolean CameraSetup()
		{
			// setup the streaming parameters
			if(Pv.AttrEnumSet(iHandle,"AcquisitionMode","Continuous") == Pv.tError.eSuccess &&
			   Pv.AttrEnumSet(iHandle,"FrameStartTriggerMode","Software") == Pv.tError.eSuccess)
			{
				Pv.tUint32  Width  = new Pv.tUint32();
				Pv.tUint32  Height = new Pv.tUint32();
				Pv.tUint32  Length = new Pv.tUint32();
				
				// get the bytes length and allocate the frame if necessary
				if(Pv.AttrUint32Get(iHandle,"TotalBytesPerFrame",Length) == Pv.tError.eSuccess &&
				   Pv.AttrUint32Get(iHandle,"Width",Width) == Pv.tError.eSuccess &&
				   Pv.AttrUint32Get(iHandle,"Height",Height) == Pv.tError.eSuccess)
				{
					if(iFrame == null)
					{
						iFrame = new Pv.tFrame();
						iFrame.ImageBuffer = ByteBuffer.allocateDirect((int)Length.Value);
					}
					else
					{
						if(iFrame.ImageBuffer.capacity() < (int)Length.Value)
							iFrame.ImageBuffer = ByteBuffer.allocateDirect((int)Length.Value);
					}
					
					if(iImage == null)
					{
						iImage = new BufferedImage((int)Width.Value,(int)Height.Value,BufferedImage.TYPE_3BYTE_BGR);
						iBuffer = ByteBuffer.allocateDirect((int)(Width.Value * Height.Value * 3));
					}
					else
						if(iImage.getWidth() != Width.Value || iImage.getHeight() != Height.Value)
						{
							iImage = new BufferedImage((int)Width.Value,(int)Height.Value,BufferedImage.TYPE_3BYTE_BGR);
							iBuffer = ByteBuffer.allocateDirect((int)(Width.Value * Height.Value * 3));
						}
					
					return true;
				}
				else
					return false;
			}
			else
				return false;
		}
		
		protected boolean CameraGrab()
		{
			if(Pv.CaptureStart(iHandle) == Pv.tError.eSuccess)
			{
				boolean Aok = false;
				
				if(Pv.CommandRun(iHandle,"AcquisitionStart") == Pv.tError.eSuccess)
				{
					try {Thread.sleep(500); } catch (InterruptedException e) {}
					
					if(Pv.CaptureQueueFrame(iHandle,iFrame, null) == Pv.tError.eSuccess)
					{						
						if(Pv.CommandRun(iHandle,"FrameStartTriggerSoftware") == Pv.tError.eSuccess)
						{
							if(Pv.CaptureWaitForFrameDone(iHandle,iFrame,Pv.Infinite) == Pv.tError.eSuccess)
								Aok = true;
						}
					}				
				}
								
				Pv.CommandRun(iHandle,"AcquisitionStop");
				Pv.CaptureEnd(iHandle);
				
				return Aok;
			}
			else
				return false;			
		}
		
		// Write a frame into a buffered image
		protected boolean FrameToImage(Pv.tFrame Frame,BufferedImage Image)
		{
			DataBufferByte Buffer = (DataBufferByte)Image.getRaster().getDataBuffer();
			byte[] Data = Buffer.getData();
						
			if(Pv.FrameToBGRBuffer(Frame,iBuffer) == Pv.tError.eSuccess)
			{
				iBuffer.get(Data,0,Data.length);
				iBuffer.rewind();				
				return true;
			}
			else
				return false;
		}		    
		   		
		// data
		private Timer     			iTimer;  // timer used for refreshing the camera list
		private JComboBox	  		iCombo;  // cameras combo box
		private JButton				iBSnap;	 // Snap! button
		private CameraListModel 	iCModel; // list of camera model	
		private Pv.tHandle			iHandle; // camera handle
		private Pv.tFrame			iFrame;	 // frame
		private BufferedImage		iImage;  // image
		private ByteBuffer			iBuffer; // direct byte buffer used to convert the raw data into RGB
		private Display				iPanel;	 // rendering panel
		private JScrollPane			iSPane;	 // scroll pane
	}
	
	/**
	 * @param args
	 */
	public static void main(String[] args) {
	
		Window window = new Window();
		
		window.setVisible(true);
	}

}
