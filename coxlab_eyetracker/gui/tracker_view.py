#
#  TrackerCameraView.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 9/3/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#

import glumpy
from OpenGL.GL import *
from numpy import *

# for test purposes only
import PIL.Image
import numpy
import time

class TrackerView:

    im_array = None
    texture = None
	
    def __init__(self):
        self.stage1_pupil_position = None
        self.stage1_cr_position = None
        self.pupil_position = None
        self.cr_position = None
        self.pupil_radius = None
        self.cr_radius = None
        self.starburst = None
        self.restrict_top = None
        self.restrict_bottom= None
        self.restrict_left = None
        self.restrict_right = None
        self.is_calibrating = 0
        
        self.gl_inited = False
        
        self.toggle = False
    
    def prepare_opengl(self):
        
        #self.openGLContext().setValues_forParameter_([1], NSOpenGLCPSwapInterval)
        
        glEnable(GL_BLEND)
        glEnable(GL_TEXTURE_2D)
        glDisable(GL_LIGHTING)
        self.texture = glGenTextures(1)
        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        self.gl_inited = True
	
    def draw(self,frame):
        
        if not self.gl_inited:
            self.prepare_opengl()
                
        (self.frame_width, self.frame_height) = frame
        
        # if self.toggle:
        #     self.toggle = False
        #     glClearColor(1.0,1.0,1.0,1.0)
        # else:
        #     self.toggle = True
        #     glClearColor(0.0,1.0,0.0,1.0)
        
        glViewport(0, 0, int(self.frame_width), int(self.frame_height))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-1.0, 1.0, -1.0, 1.0, 0.0,1.0)
    
        glColor4f(1.0,1.0,1.0,1.0)
        glClear(GL_COLOR_BUFFER_BIT)
		
        if(self.im_array == None):
            print "No image"
            #glFlush()
            return
            
        self.render_image(frame)
        
        if(self.stage1_pupil_position != None):
            self.render_stage1_pupil_location()
        
        if(self.stage1_cr_position != None):
            self.render_stage1_CR_location()
            
        if(self.pupil_position != None):
            self.render_pupil_location()
            
        if(self.cr_position != None):
            self.render_CR_location()
        
        if(self.starburst != None):
            self.render_starburst(self.starburst)
            
        if(self.is_calibrating != None and self.is_calibrating):
            self.render_calibrating()
            
        #self.render_restriction_box()
        
        #self.openGLContext().flushBuffer()
        
        #glFlush()

    def render_image(self, frame):
        
        I = glumpy.Image(self.im_array, interpolation='bilinear',
                         cmap=glumpy.colormap.Grey)
        I.blit(-1,-1,2,2)
        
        return
        
        # old way...
        self.texture = glGenTextures(1)
    
        glColor4f(1.,1.,1.,1.)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.im_array.shape[1], 
                                                self.im_array.shape[0], 
                                                0, 
                                                GL_LUMINANCE, GL_UNSIGNED_BYTE, 
                                                self.im_array.astype(uint8))

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
        glDeleteTextures(self.texture)

    def render_stage1_pupil_location(self):
        self.render_crosshairs(self.__image_coords_to_texture_coords(self.stage1_pupil_position), (1.,0.,0.,0.5), 0.02, 0.002)
        return
        
    def render_stage1_CR_location(self):
        self.render_crosshairs(self.__image_coords_to_texture_coords(self.stage1_cr_position), (0.,0.,1.,0.5), 0.02, 0.002)
        return
        
    def render_pupil_location(self):
        if(self.pupil_radius != None):
            radius = self.pupil_radius
        else:
            radius = 10
        # print self.im_array.shape = 120, 160
        # print self.__image_length_to_texture_length(60.0) = 0.5, 0.375
        #self.render_circle(self.__image_coords_to_texture_coords((60.0,80.0)), self.__image_length_to_texture_length(60.0), (0., 1., 0.), 0.004)
        #self.render_crosshairs(self.__image_coords_to_texture_coords(self.pupil_position), (0.,1.,0.5), 0.06, 0.002)
        self.render_circle(self.__image_coords_to_texture_coords(self.pupil_position),  self.__image_length_to_texture_length(radius), (1.,0.,0.0), 0.004 )
        #self.render_crosshairs(self.__image_coords_to_texture_coords(self.pupil_position),  (1.,0.,0.0), self.__image_length_to_texture_length(radius), 0.002)
        
        return
        
    def render_CR_location(self):
        if(self.cr_radius != None):
            radius = self.cr_radius
        else:
            radius = 10
#        self.render_crosshairs(self.__image_coords_to_texture_coords(self.cr_position), (1.,1.,0.5), 0.06, 0.002)  
        self.render_circle(self.__image_coords_to_texture_coords(self.cr_position),self.__image_length_to_texture_length(radius),(0.,0.,1.), .004)
        #self.render_crosshairs(self.__image_coords_to_texture_coords(self.cr_position),(0.,0.,1.), self.__image_length_to_texture_length(radius), .002)
        
        return    
    
    def render_restriction_box(self):
    
        if (self.restrict_top is None) or (self.restrict_bottom is None) or (self.restrict_left is None) or (self.restrict_right is None):
           return
        
        (t,l) = self.__image_coords_to_texture_coords(array([self.im_array.shape[0] - self.restrict_left, self.im_array.shape[1] -self.restrict_top]))
        (b,r) = self.__image_coords_to_texture_coords(array([self.im_array.shape[0] - self.restrict_right, self.im_array.shape[1] -self.restrict_bottom]))
 
        
        a = 0.005
        
        blue_color = 1.0
        glBegin(GL_QUADS)
        glColor((0,0,blue_color))
        glVertex3f(l, t, 0.)
        glVertex3f(l+a, t, 0.)
        glVertex3f(l+a, b, 0.)
        glVertex3f(l, b, 0.)

        glVertex3f(r, t, 0.)
        glVertex3f(r-a, t, 0.)
        glVertex3f(r-a, b, 0.)
        glVertex3f(r, b, 0.)

        glVertex3f(l, t, 0.)
        glVertex3f(l, t+a, 0.)
        glVertex3f(r, t+a, 0.)
        glVertex3f(r, t, 0.)


        glVertex3f(l, b, 0.)
        glVertex3f(l, b-a, 0.)
        glVertex3f(r, b-a, 0.)
        glVertex3f(r, b, 0.)

        glEnd() 
        return

    
    def render_calibrating(self):
    
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
                
    def __image_length_to_texture_length(self, length):
        return array([2.0 * length/self.im_array.shape[0], 2.0 *length/self.im_array.shape[1]])
        
    def __image_coords_to_texture_coords(self, coords):
        return array([1., -1.]) *  (2.0 * (array([coords[1], coords[0]]) / array([self.im_array.shape[1], self.im_array.shape[0]])) - 1.0)
    
    def render_circle(self, location, radius, color, weight):
        glPushMatrix()
        #glTranslate(100., 100., 0)
        glTranslate(location[0], location[1], 0.0)
        
        # radius is a 2 long array, is this x and y length?
        # what is the 'weight' is this the thickness of the line?
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
                
    def render_crosshairs(self, location, color, width, weight):
        glPushMatrix()
        glTranslate(location[0], location[1], 0.0)
        
        aspect = float(self.frame_height) / self.frame_width
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
        
    def render_starburst(self, starburst):

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
        glColor((0.,0.8,0.,1.0))
        
            
        for i in range(0, len(pupil_rays_start)):
            #NSLog("pupil ray: %f, %f" % (pupil_rays_start[i][0], pupil_rays_start[i][1]))
            #NSLog("\t%f, %f" % (pupil_rays_end[i][0], pupil_rays_end[i][1]))
            ray_start = self.__image_coords_to_texture_coords(pupil_rays_start[i])
            ray_end = self.__image_coords_to_texture_coords(pupil_rays_end[i])
            glVertex3f( ray_start[0], ray_start[1], 0. )
            glVertex3f( ray_end[0], ray_end[1], 0. )
                
        for i in range(0, len(cr_rays_start)):
            #NSLog("cr ray: %f, %f" % (cr_rays_start[i][0], cr_rays_start[i][1]))
            #NSLog("\t%f, %f" % (cr_rays_end[i][0], cr_rays_end[i][1]))
            ray_start = self.__image_coords_to_texture_coords(cr_rays_start[i])
            ray_end = self.__image_coords_to_texture_coords(cr_rays_end[i])
            glVertex3f( ray_start[0], ray_start[1], 0. )
            glVertex3f( ray_end[0], ray_end[1], 0. )
        
        glEnd()
        
        #glPointSize(2.0)
        glBegin(GL_LINE_LOOP)
        #glBegin(GL_POINTS)
        glColor((1.,0.65,0.,1.))
        for i in range(0, len(pupil_boundary)):
            bound = self.__image_coords_to_texture_coords(pupil_boundary[i])
            glVertex3f( bound[0], bound[1], 0. )
        glEnd()
        
        glBegin(GL_LINE_LOOP)
        glColor((1.0, 0.65, 0.0, 1.0))
        for i in range(0, len(cr_boundary)):
            bound = self.__image_coords_to_texture_coords(cr_boundary[i])
            glVertex3f( bound[0], bound[1], 0. )
        glEnd()
    
