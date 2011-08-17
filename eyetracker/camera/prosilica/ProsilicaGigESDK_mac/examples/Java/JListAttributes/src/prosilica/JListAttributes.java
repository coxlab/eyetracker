/*
| ==============================================================================
| Copyright (C) 2008 Prosilica.  All Rights Reserved.
|
| Redistribution of this header file, in original or modified form, without
| prior written consent of Prosilica is prohibited.
|
|==============================================================================
|
| This sample code, lists all the attributes available for the selected camera
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

import javax.swing.ComboBoxModel;
import javax.swing.AbstractListModel;
import javax.swing.JFrame;
import javax.swing.JComboBox;
import javax.swing.JList;
import javax.swing.JScrollPane;
import javax.swing.Timer;
import javax.swing.JPanel;
import java.awt.BorderLayout;

public class JListAttributes {

	// Window class
	private static class Window extends JFrame implements WindowListener, ActionListener {
			
		// constructor
		public Window()
		{
			JScrollPane scrollPane = new JScrollPane();
			JPanel content 		   = new JPanel();
			
			content.setLayout(new BorderLayout());
						
			iCModel = new CameraListModel();
			iAModel = new AttributeListModel();
			iTimer = new Timer(1000,this);
			iCombo = new JComboBox();
			iList  = new JList(iAModel);
			
			iCombo.setModel(iCModel);
			scrollPane.getViewport().setView(iList);
			
			content.add(iCombo,BorderLayout.NORTH);
			content.add(scrollPane,BorderLayout.CENTER);			
			
			setTitle("JListAttributes");
			setContentPane(content);
			setSize(250,350);
			setLocation(100,100);
			setDefaultCloseOperation(Window.EXIT_ON_CLOSE);
						
			iCombo.addActionListener(this);
			addWindowListener(this);
		}
		
		// called when the window is opened
		public void windowOpened(WindowEvent e)
		{
			iError = Pv.Initialize();
			
			if(iError == Pv.tError.eSuccess)
			{
				iTimer.start();
				iCModel.Refresh();
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
					iAModel.Fill(UID);
				else
					iAModel.Empty();
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
		
		// attribute model class
		private static class AttributeListModel extends AbstractListModel {
			
			AttributeListModel()
			{
				iStrings = new Pv.tStringsList();
			}
			
			public int getSize()
			{ 
				return iStrings.Count;
			}
			
		    public Object getElementAt(int index)
		    { 
		    	return iStrings.Array[index];
		    }		
		     
		    public void Fill(long UID)
		    {
		    	Pv.tHandle Handle = new Pv.tHandle();
		    	
		    	if(iStrings.Count != 0)
		    		fireIntervalRemoved(this,0,iStrings.Count - 1);	
		    	
		    	if(Pv.CameraOpen(UID,Pv.tAccessFlags.eMonitor,Handle) == Pv.tError.eSuccess)
		    	{
		    		if(Pv.AttrList(Handle,iStrings) == Pv.tError.eSuccess)
		    			fireIntervalAdded(this,0,iStrings.Count - 1);	
		    		
		    		Pv.CameraClose(Handle);
		    	}
		    }
		    
		    public void Empty()
		    {
		    	if(iStrings.Count > 0)
		    	{
		    		fireIntervalRemoved(this,0,iStrings.Count - 1);
		    		iStrings.Count = 0;
		    	}
		    }
		 
		    private Pv.tStringsList 	iStrings;
		}	
		
		// data
		private Pv.tError 			iError;  // PvAPI init. error
		private Timer     			iTimer;  // timer used for refreshing the camera list
		private JComboBox	  		iCombo;  // cameras combobox
		private JList				iList;	 // list of attributes
		private CameraListModel 	iCModel; // list of camera model
		private AttributeListModel 	iAModel; // list of attribute model
	}
	
	/**
	 * @param args
	 */
	public static void main(String[] args) {
	
		Window window = new Window();
		
		window.setVisible(true);
	}

}
