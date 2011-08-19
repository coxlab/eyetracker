/*
| ==============================================================================
| Copyright (C) 2008 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code, continuously get the list of cameras and display it within
| a Window.
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
import java.awt.event.*;
import javax.swing.*;

public class JListCameras {

	// Window class
	private static class Window extends JFrame implements WindowListener, ActionListener {
			
		// constructor
		public Window()
		{
			JScrollPane scrollPane = new JScrollPane();
			
			iModel = new CameraListModel();
			iTimer = new Timer(1000,this);
			iList  = new JList(iModel);
			
			scrollPane.getViewport().setView(iList);
			
			setTitle("JListCameras");
			setSize(250,250);
			setLocation(100,100);
			setDefaultCloseOperation(Window.EXIT_ON_CLOSE);
			
			add(scrollPane);
			
			addWindowListener(this);
		}
		
		// called when the window is opened
		public void windowOpened(WindowEvent e)
		{
			iError = Pv.Initialize();
			
			if(iError == Pv.tError.eSuccess)
			{
				iTimer.start();
				iModel.Refresh();
			}
		}
		
		// called when the window is closing 
		public void windowClosing(WindowEvent e)
		{
			iTimer.stop();			
			Pv.UnInitialize();
		}
		
		// called when an action is performed (e.g timer event)
		public void actionPerformed(ActionEvent e)
		{
			if(e.getSource() == iTimer)
			{
				iModel.Refresh();
			}
		}
		
		// un-used callbacks
		public void windowClosed(WindowEvent e) {}
		public void windowActivated(WindowEvent e) {}
		public void windowDeactivated(WindowEvent e) {}
		public void windowDeiconified(WindowEvent e) {}
		public void windowIconified(WindowEvent e) {}
       	
		// camera model class
		private static class CameraListModel extends AbstractListModel {
			
			CameraListModel()
			{
				iCameras = new Pv.tCameraInfoEx[10];
			}
			
			public int getSize()
			{ 
				return iCount;
			}
			
		    public Object getElementAt(int index)
		    { 
		    	return iCameras[index].SerialNumber + " - " + iCameras[index].CameraName;
		    }		
		     
		    public void Refresh()
		    {
		    	int lBefore = iCount;
		    	
		    	iCount = Pv.CameraListEx(iCameras,10);
		    	
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
		    		fireIntervalRemoved(this,0,lBefore - 1);	
		    }
		     
		    private int 				iCount = 0;
		    private Pv.tCameraInfoEx[] 	iCameras;
		}
		
		// data
		private Pv.tError 		iError; // PvAPI init. error
		private Timer     		iTimer; // timer used for refreshing the camera list
		private JList	  		iList;  // list
		private CameraListModel iModel;	// list of camera
	}
	
	/**
	 * @param args
	 */
	public static void main(String[] args) {
	
		Window window = new Window();
		
		window.setVisible(true);
	}

}
