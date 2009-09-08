#
#  TrackerCameraView.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 9/3/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#

from AppKit import *
from OpenGL.GL import *
from numpy import *

# for test purposes only
import PIL.Image
import numpy
import time

class TrackerCameraView(NSOpenGLView):

    im_array = None
    texture = None
	
    def awakeFromNib(self):
        self.stage1_pupil_position = None
        self.stage1_cr_position = None
        self.pupil_position = None
        self.cr_position = None
        self.pupil_radius = None
        self.cr_radius = None
        self.starburst = None
        self.is_calibrating = 0
    
    def prepareOpenGL(self):
        
        self.openGLContext().setValues_forParameter_([1], NSOpenGLCPSwapInterval)
        
        glEnable(GL_BLEND)
        glEnable(GL_TEXTURE_2D)
        glDisable(GL_LIGHTING)
        #glBlendFunc(GL_ONE, GL_ZERO)
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        #glBlendFunc(GL_ONE_MINUS_DST_ALPHA, GL_DST_ALPHA)
        self.texture = glGenTextures(1)
        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
	
    def drawRect_(self,rect):
        frame = self.frame()
        self.frame_width = frame.size.width
        self.frame_height = frame.size.height
        
        glViewport(0, 0, int(self.frame_width), int(self.frame_height))
        #glOrtho(0, 1., 0, 1.,-1.,1.)
    
        glClear(GL_COLOR_BUFFER_BIT)
		
        if(self.im_array == None):
            print "No image"
            self.openGLContext().flushBuffer()
            return
            
        self.drawImage()
        
        if(self.stage1_pupil_position != None):
            self.renderStage1PupilLocation()
        
        if(self.stage1_cr_position != None):
            self.renderStage1CRLocation()
            pass
            
        if(self.pupil_position != None):
            self.renderPupilLocation()
            
        if(self.cr_position != None):
            self.renderCRLocation()
        
        if(self.starburst != None):
            self.renderStarburst(self.starburst)
            
        if(self.is_calibrating != None and self.is_calibrating):
            self.renderCalibrating()
            
    
        self.openGLContext().flushBuffer()
#        glFlush()

    def drawImage(self):
        glColor4f(1.,1.,1.,1.)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.im_array.shape[1], self.im_array.shape[0], 0, GL_LUMINANCE, GL_UNSIGNED_BYTE, self.im_array.astype(uint8))

        glBindTexture(GL_TEXTURE_2D, self.texture)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 0.0) 
        glVertex3f(-1., 1.,  0.0) # Bottom Left
        glTexCoord2f(1.0, 0.0)
        glVertex3f( 1., 1.,  0.0) # Bottom Right
        glTexCoord2f(1., 1.)
        glVertex3f( 1.0,  -1.0,  0.0) # Top Right
        glTexCoord2f(0.0, 1.0)
        glVertex3f(-1.0,  -1.0,  0.0) # Top Left
        glEnd()
        glBindTexture(GL_TEXTURE_2D, 0)

    def renderStage1PupilLocation(self):
        self.renderCrossHairs(self.__imageCoordsToTextureCoords(self.stage1_pupil_position), (1.,0.,0.,0.5), 0.02, 0.002)
        return
        
    def renderStage1CRLocation(self):
        self.renderCrossHairs(self.__imageCoordsToTextureCoords(self.stage1_cr_position), (0.,0.,1.,0.5), 0.02, 0.002)
        return
        
    def renderPupilLocation(self):
        if(self.pupil_radius != None):
            radius = self.pupil_radius
        else:
            radius = 10
        
        #self.renderCrossHairs(self.__imageCoordsToTextureCoords(self.pupil_position), (0.,1.,0.5), 0.06, 0.002)        
        self.renderCircle(self.__imageCoordsToTextureCoords(self.pupil_position),  self.__imageLengthToTextureLength(radius), (1.,0.,0.0), 0.004)
        #self.renderCrossHairs(self.__imageCoordsToTextureCoords(self.pupil_position),  (1.,0.,0.0), self.__imageLengthToTextureLength(radius), 0.002)
        
        return
        
    def renderCRLocation(self):
        if(self.cr_radius != None):
            radius = self.cr_radius
        else:
            radius = 10
#        self.renderCrossHairs(self.__imageCoordsToTextureCoords(self.cr_position), (1.,1.,0.5), 0.06, 0.002)  
        self.renderCircle(self.__imageCoordsToTextureCoords(self.cr_position),self.__imageLengthToTextureLength(radius),(0.,0.,1.), .004)
        #self.renderCrossHairs(self.__imageCoordsToTextureCoords(self.cr_position),(0.,0.,1.), self.__imageLengthToTextureLength(radius), .002)
        
        return    
    
    def renderCalibrating(self):
    
        a = .05
    
        rate = 500.
        blink_level = (int(rate * time.time()) % rate) / rate
        
        red_color = numpy.cos(2*numpy.pi*blink_level)/4. + 0.75
        glBegin(GL_QUADS)
        glColor((red_color,0,0))
        glVertex3f(-1., -1., 0.)
        glVertex3f(-1.+a, -1., 0.)
        glVertex3f(-1.+a, 1, 0.)
        glVertex3f(-1., 1, 0.)


        glVertex3f(1., -1., 0.)
        glVertex3f(1.-a, -1., 0.)
        glVertex3f(1.-a, 1, 0.)
        glVertex3f(1., 1, 0.)

        glVertex3f(-1., -1., 0.)
        glVertex3f(-1., -1.+a, 0.)
        glVertex3f(1., -1+a, 0.)
        glVertex3f(1., -1, 0.)


        glVertex3f(-1., 1., 0.)
        glVertex3f(-1., 1.-a, 0.)
        glVertex3f(1., 1.-a, 0.)
        glVertex3f(1., 1, 0.)

        glEnd() 
        return
                
    def __imageLengthToTextureLength(self, length):
        return array([2.0*length/self.im_array.shape[0], 2.0*length/self.im_array.shape[1]])
        
    def __imageCoordsToTextureCoords(self, coords):
        return array([1., -1.]) *  (2.0 * (array([coords[1], coords[0]]) / array([self.im_array.shape[1], self.im_array.shape[0]])) - 1.0)
    
    def renderCircle(self, location, radius, color, weight):
        glPushMatrix()
        #glTranslate(100., 100., 0)
        glTranslate(location[0], location[1], 0.0)
        
        r1 = radius + (weight / 2)
        r2 = radius - (weight / 2)
            
        n_segments = 200
        
        glBegin(GL_TRIANGLE_STRIP)
        glColor(color)
        for n in range(0, n_segments):
            a1 = n * 2 * numpy.pi / n_segments
            a2 = (n+1) * 2* numpy.pi / n_segments
            
            #print "================="
            #print "x:", r1 * cos(a1), " y:", r1 * sin(a1)
            #print "x:", r2 * cos(a2), " y:", r2 * sin(a2)
                        
            
            glVertex3f(r1[1] * cos(a1), r1[0] * sin(a1), 0.0)
            glVertex3f(r2[1] * cos(a2), r2[0] * sin(a2), 0.0)
        glEnd()
        
        glPopMatrix()
                
    def renderCrossHairs(self, location, color, width, weight):
        glPushMatrix()
        glTranslate(location[0], location[1], 0.0)
        
        
        aspect = self.frame_height / self.frame_width
        weightx = weight
        weighty = weight / aspect
        
        # horizontal part
        glBegin(GL_QUADS)
        glColor(color)
        glVertex3f(-width, -weighty, 0.)
        glVertex3f(width, -weighty, 0.)
        glVertex3f(width, weighty, 0.)
        glVertex3f(-width, weighty, 0.)
        glEnd()
        
        # vertical part
        glBegin(GL_QUADS)
        glVertex3f(-weightx, -width, 0.)
        glVertex3f(weightx, -width, 0.)
        glVertex3f(weightx, width, 0.)
        glVertex3f(-weightx, width, 0.)
        glEnd()
    
        glPopMatrix()
        
    def renderStarburst(self, starburst):

        # assume that the dictionary contains everything that it is supposed to
        pupil_rays_start = starburst['pupil_rays_start']
        pupil_rays_end = starburst['pupil_rays_end']
        pupil_boundary = starburst['pupil_boundary']
        cr_rays_start = starburst['cr_rays_start']
        cr_rays_end = starburst['cr_rays_end']
        cr_boundary = starburst['cr_boundary']

        if(pupil_rays_start == None or
           pupil_rays_end == None or
           pupil_boundary == None or
           cr_rays_start == None or
           cr_rays_end == None or
           cr_boundary == None):
            return

        if(len(pupil_rays_start) == 0 and
            len(pupil_rays_end) == 0 and
            len(pupil_boundary) == 0 and
            len(cr_rays_start) == 0 and
            len(cr_rays_end) == 0 and
            len(cr_boundary) == 0):
            return

        #NSLog("len(pupil_rays_start) == %d" % len(pupil_rays_start))
        
        
        glBegin(GL_LINES)
        glColor((0.,1.,0.,1.0))
        
            
        for i in range(0, len(pupil_rays_start)):
            #NSLog("pupil ray: %f, %f" % (pupil_rays_start[i][0], pupil_rays_start[i][1]))
            #NSLog("\t%f, %f" % (pupil_rays_end[i][0], pupil_rays_end[i][1]))
            ray_start = self.__imageCoordsToTextureCoords(pupil_rays_start[i])
            ray_end = self.__imageCoordsToTextureCoords(pupil_rays_end[i])
            glVertex3f( ray_start[0], ray_start[1], 0. )
            glVertex3f( ray_end[0], ray_end[1], 0. )
                
        for i in range(0, len(cr_rays_start)):
            #NSLog("cr ray: %f, %f" % (cr_rays_start[i][0], cr_rays_start[i][1]))
            #NSLog("\t%f, %f" % (cr_rays_end[i][0], cr_rays_end[i][1]))
            ray_start = self.__imageCoordsToTextureCoords(cr_rays_start[i])
            ray_end = self.__imageCoordsToTextureCoords(cr_rays_end[i])
            glVertex3f( ray_start[0], ray_start[1], 0. )
            glVertex3f( ray_end[0], ray_end[1], 0. )
        
        glEnd()
        
    
        glBegin(GL_POINTS)
        glColor((1.,0.,0.,1.))
        for i in range(0, len(pupil_boundary)):
            bound = self.__imageCoordsToTextureCoords(pupil_boundary[i])
            glVertex3f( bound[0], bound[1], 0. )
        
        for i in range(0, len(cr_boundary)):
            bound = self.__imageCoordsToTextureCoords(cr_boundary[i])
            glVertex3f( bound[0], bound[1], 0. )
        
        glEnd()
    