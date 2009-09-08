#
#  cocoa_backend.py
#  EyeTracker
#
#  Created by David Cox on 3/12/09.
#  Copyright (c) 2009 Harvard University. All rights reserved.
#
""" 
The Cocoa backend is a Quartz-native backend for Matplotlib for using 
Matplotlib from *within* a Cocoa application (one that already has an 
NSRunLoop). 

""" 
from __future__ import division 

__docformat__ = "restructuredtext en" 

# Cocoa specific 
from Foundation import * 
from AppKit import * 
                
import objc

# matplotlib 
import matplotlib 
from matplotlib._pylab_helpers import Gcf 
from matplotlib.figure import Figure 
from matplotlib.backend_bases import RendererBase, GraphicsContextBase, FigureCanvasBase, FigureManagerBase 
from matplotlib.path import Path 
from matplotlib.transforms import Bbox, Affine2D 

import numpy as np 

# Testing 
import unittest 
import nose 




POINTS_PER_INCH = 72.0 

# Memoize (from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496879). 
# Modified to skip first arg (self, since it'll be an NSObject) 
import cPickle 

def memoize(function, limit=None): 
    if isinstance(function, int): 
        def memoize_wrapper(f): 
            return memoize(f, function) 
        
        return memoize_wrapper 
    
    dict = {} 
    list = [] 
    def memoize_wrapper(*args, **kwargs): 
        key = cPickle.dumps((args[1:], kwargs)) 
        try: 
            list.append(list.pop(list.index(key))) 
        except ValueError: 
            dict[key] = function(*args, **kwargs) 
            list.append(key) 
            if limit is not None and len(list) > limit: 
                del dict[list.pop(0)] 
        
        return dict[key] 
    
    memoize_wrapper._memoize_dict = dict 
    memoize_wrapper._memoize_list = list 
    memoize_wrapper._memoize_limit = limit 
    memoize_wrapper._memoize_origfunc = function 
    memoize_wrapper.func_name = function.func_name 
    return memoize_wrapper 




class RendererCocoa(RendererBase): 
    """ 
    The renderer handles drawing/rendering operations. 
    
    RendererCocoa renders into an NSView instance 
    """ 
    
    fontWeights = { 
        100          : u'', 
        200          : u'', 
        300          : u'', 
        400          : u'', 
        500          : u'', 
        600          : u'Bold', 
        700          : u'Bold', 
        800          : u'Bold', 
        900          : u'Bold', 
        'ultralight' : u'', 
        'light'      : u'', 
        'normal'     : u'', 
        'medium'     : u'', 
        'semibold'   : u'Bold', 
        'bold'       : u'Bold', 
        'heavy'      : u'Bold', 
        'ultrabold'  : u'Bold', 
        'black'      : u'Bold', 
                   } 
    
    
    fontAngles = { 
        'italic'  : u'Italic', 
        'normal'  : u'', 
        'oblique' : u'Oblique', 
        } 
    
    lineJoinStyle = { 
        'miter' : NSMiterLineJoinStyle, 
        'round' : NSRoundLineJoinStyle, 
        'bevel' : NSBevelLineJoinStyle 
    } 
    
    lineCapStyle = { 
        'butt'          :   NSButtLineCapStyle, 
        'round'         :   NSRoundLineCapStyle, 
        'projecting'    :   NSSquareLineCapStyle, 
    } 
    
    def get_dpi(self): 
        """current nsview's device dpi""" 
        
        return self.points_to_pixels(POINTS_PER_INCH) 
    
    dpi = property(fget=get_dpi, doc="Current NSView's device DPI") 
    
    def __init__(self, view): 
        """ 
        * Parameters * 
            view : {NSView} 
            dpi : {float?} 
        """ 
        self.nsview = view 
        self.pathCache = {} 
    
    
    def draw_path(self, gc, path, transform, rgbFace=None): 
        
        path = transform.transform_path(path) 
        
        path = self.mpl_to_bezier_path(path) 
        
        path.setLineJoinStyle_(self.lineJoinStyle[gc.get_joinstyle()]) 
        path.setLineWidth_(gc.get_linewidth()) 
        path.setLineCapStyle_(self.lineCapStyle[gc.get_capstyle()]) 
        #path.setLineDash_count_phase_() #todo 
        
        
        NSGraphicsContext.saveGraphicsState() 
        try: 
            #set up clipping rect as intersection of current clipping path and 
            # gc's clipping path 
            clipPath,clipPathTransform = gc.get_clip_path() 
            if(clipPathTransform != None): 
                clipPath = clipPathTransform.transform_path(clipPath) 
        
            if(clipPath != None): 
                self.mpl_to_bezier_path(clipPath).addClip() 
        
            self.set_color_from_gc(gc, rgbFace=rgbFace) 
        
            #draw 
            path.stroke() 
            if(rgbFace != None): #undocumented -- only fill if rgbFace non-nil 
                path.fill() 
        finally: 
            NSGraphicsContext.restoreGraphicsState() 
    
    
    def draw_markers(self, gc, marker_path, marker_trans, path, trans, 
                    rgbFace=None): 
        """ 
        Draws a marker at each of the vertices in path.  This includes 
        all vertices, including control points on curves.  To avoid 
        that behavior, those vertices should be removed before calling 
        this function. 
        
        marker_trans is an affine transform applied to the marker. 
        trans is an affine transform applied to the path. 
        
        Overrides base implementation to convert paths only onse. 
        """ 
        tpath = trans.transform_path(path) 
        if(marker_trans != None): 
            marker_trans.transform_path(marker_path) 
        
        mpath = self.mpl_to_bezier_path(marker_path) 
        mpath.setLineJoinStyle_(self.lineJoinStyle[gc.get_joinstyle()]) 
        mpath.setLineWidth_(gc.get_linewidth()) 
        mpath.setLineCapStyle_(self.lineCapStyle[gc.get_capstyle()]) 
        #mpath.setLineDash_count_phase_() #todo 
        
        NSGraphicsContext.saveGraphicsState() 
        try: 
            self.set_color_from_gc(gc, rgbFace=rgbFace) 
            for (pts,code) in tpath.iter_segments(): 
                if(code != Path.STOP and 
                    code != Path.CLOSEPOLY): 
                    t = NSAffineTransform.alloc().init() 
                    t.translateXBy_yBy_(pts[0], pts[1]) 
                    p = t.transformBezierPath_(mpath) 
                    p.stroke() 
                    if(rgbFace != None): 
                        p.fill() 
        finally: 
            NSGraphicsContext.restoreGraphicsState() 
    
    
    def set_color_from_gc(self,gc, rgbFace=None): 
        """ 
        * Parameters * 
            gc : {matplotlib.backend_bases.GraphicsContextBase} 
        """ 
        assert(gc != None) 
        
        color_tuple = gc.get_rgb() 
        
        if(len(color_tuple) == 4):
            (r,g,b,a) = color_tuple
        else:
            (r,g,b) = color_tuple
            a = gc.get_alpha() 
        color = NSColor.colorWithCalibratedRed_green_blue_alpha_(r,g,b,a) 
        color.set() 
        
        if(rgbFace != None): 
            r,g,b = rgbFace 
            NSColor.colorWithCalibratedRed_green_blue_alpha_(r,g, 
                                                            b,a).setFill() 
    
    
    @memoize(10) 
    def mpl_to_affine_transform(self, trans): 
        """ 
        Converts mpl transforms.Affine2D to NSAffineTransform. 
        
        Caches 100 previous calls. 
        
        * Parameters * 
        trans : {matplotlib.transforms.Affine2D} 
        
        * Results * 
        t : {NSAffineTransform} 
        Equivalent transform to trans. 
        
        * Raises * 
        AssertionError if trans is not of type matplotlib.transforms.Affine2D 
        """ 
        
        assert(isinstance(trans, Affine2D)) 
        m = trans.get_matrix() 
        t = NSAffineTransform.transform() 
        
        t.setTransformStruct_(NSAffineTransformStruct(m[0,0], m[0,1], 
                                                      m[1,0], m[1,1], 
                                                      m[0,2], m[1,2])) 
        
        return t 
    
    
    @memoize(5) 
    def mpl_to_bezier_path(self, path): 
        """ 
        Convert an mpl path.Path object to an NSBezierPath. 
        
        This call should be in compiled code...it's very slow in python. 
        
        * Parameters * 
            path : {matplotlib.path.Path} 
            
        * Returns * 
            bezierPath : {NSBezierPath} 
        
        matplotlib.path.Path.iter_segments returns (pts,code) where pts is 
        a 2*n x 1 numpy list where n is the number of vertices for the given 
         code. 
        
        from the matplotlib.path.Path doc string: 
            The code types are: 
            
               STOP   :  1 vertex (ignored) 
                  A marker for the end of the entire path (currently not 
                  required and ignored) 
                  
               MOVETO :  1 vertex 
                  Pick up the pen and move to the given vertex. 
                  
               LINETO :  1 vertex 
                  Draw a line from the current position to the given vertex. 
                  
               CURVE3 :  1 control point, 1 endpoint 
                  Draw a quadratic Bezier curve from the current position, 
                  with the given control point, to the given end point. 
                  
               CURVE4 :  2 control points, 1 endpoint 
                  Draw a cubic Bezier curve from the current position, with 
                  the given control points, to the given end point. 
                  
               CLOSEPOLY : 1 vertex (ignored) 
                  Draw a line segment to the start point of the current 
                  polyline. 
        """ 
        
        b = NSBezierPath.bezierPath() 
        for (pts,code) in path.iter_segments(): 
            if(code == Path.STOP): 
                continue 
            elif(code == Path.MOVETO): 
                b.moveToPoint_(NSMakePoint(pts[0],pts[1])) 
            elif(code == Path.LINETO): 
                b.lineToPoint_(NSMakePoint(pts[0],pts[1])) 
            elif(code == Path.CURVE3): 
                b.curveToPoint_controlPoint1_controlPoint2_( 
                        NSMakePoint(pts[2],pts[3]), 
                        NSMakePoint(pts[0],pts[1]), 
                        NSMakePoint(pts[0],pts[1])) 
            elif(code == Path.CURVE4): 
                b.curveToPoint_controlPoint1_controlPoint2_( 
                        NSMakePoint(pts[4],pts[5]), 
                        NSMakePoint(pts[0],pts[1]), 
                        NSMakePoint(pts[2],pts[3])) 
            elif(code == Path.CLOSEPOLY): 
                b.closePath() 
            else: 
                raise Exception( 
                    'Unexpected matplotlib.path.Path vertex code (' + 
                    str(code) + 
                    ')') 
        
        return b 
    
    
    def draw_image(self, x, y, im, bbox, clippath=None, clippath_trans=None): 
        if(clippath != None and clippath_trans != None): 
            clippath = clippath_trans.transform_path(clippath) 
        
        NSGraphicsContext.saveGraphicsState() 
        try: 
            if(clippath != None): 
                self.mpl_to_bezier_path(clippath).addClip() 
        
            # TODO how do we get an NSImage from im? 
        
            raise NotImplementedError 
        finally: 
            NSGraphicsContext.restoreGraphicsState() 
    
    
    def draw_text(self, gc, x, y, s, prop, angle, ismath=False): 
        if(ismath): 
            raise NotImplementedError 
        
        NSGraphicsContext.saveGraphicsState() 
        try: 
            self.set_color_from_gc(gc) 
        
            f = self.font_for_font_properties(prop) 
            if(f == None): 
                #f = NSFont.systemFontOfSize_(prop.get_size()) 
                f = NSFont.systemFontOfSize_(20.0) # DDC: hacked 
        
            f.set() 
        
            t = NSAffineTransform.transform() 
        
            if(angle != 0): 
                t.translateXBy_yBy_(-x,-y) 
                t.rotateByDegrees_(angle) 
                t.concat() 
        
            t.invert() 
        
            pt = t.transformPoint_(NSMakePoint(x,y)) 
            NSString.stringWithString_(s).drawAtPoint_withAttributes_(pt, {}) 
        
            t.concat() 
        finally: 
            NSGraphicsContext.restoreGraphicsState() 
    
    
    def flipy(self): 
        return self.nsview.isFlipped() 
    
    
    def get_image_magnification(self): 
        """Proxy Quartz's user space scale factor""" 
        return self.nsview.window().userSpaceScaleFactor() 
    
    
    def get_canvas_width_height(self): 
        return (self.nsview.bounds().size.width, 
                self.nsview.bounds().size.height) 
    
    
    def get_text_width_height_descent(self, s, prop, ismath): 
        if(ismath): 
            raise NotImplementedError 
        
        #get the font matching prop 
        f = self.font_for_font_properties(prop) 
        if(f == None): 
            # print 'Unable to find font for %s' % str(prop) 
            # print 'Substituting system font of same size'
            f = NSFont.systemFontOfSize_(20.0) # DDC: hacked 
        # get width and height from NSString's convenience method 
        attr = dict(NSFontAttributeName = f) 
        s = NSString.stringWithString_(s) 
        (w,h) = s.sizeWithAttributes_(attr) 
        
        # get baseline from the retrieved font 
        baseline = f.descender() 
        
        return (w,h,baseline) 
    
    
    def font_for_font_properties(self, prop): 
        """Converts prop to the associated NSFont""" 
        
        fontDescriptor = self.font_descriptor_for_font_properties(prop) 
        return NSFont.fontWithDescriptor_size_(fontDescriptor, 
                        fontDescriptor.pointSize()) 
    
    
    def font_descriptor_for_font_properties(self, prop): 
        """ 
        Attempts to convert prop into an NSFontDescriptor 
        """ 
        
        fontName = prop.get_name() 
        style = u'' 
        style += self.fontWeights[prop.get_weight()] 
        style += self.fontAngles[prop.get_style()] 
        if(style != u''): 
            fontName += style 
        
        
        d = dict(NSFontNameAttribute =   fontName, 
                    NSFontSizeAttribute =   prop.get_size(), 
                    ) 
                    
        return NSFontDescriptor.fontDescriptorWithFontAttributes_(d) 
    
    
    def new_gc(self): #done 
        return GraphicsContextCocoa() 
    
    
    def points_to_pixels(self, points): #done 
        """ 
        Quartz may render to devices which have high dpi. To maintain 
        resolution independence, we have to take into account 
        self.view's window's userSpaceScaleFactor or NSScreen's 
        userSpaceScaleFactor 
        """ 
        
        if (self.nsview.window() == None): 
            scaleFactor = NSScreen.mainScreen().userSpaceScaleFactor() 
        else: 
            scaleFactor = self.nsview.window().userSpaceScaleFactor() 
        
        return points * scaleFactor 
    



class GraphicsContextCocoa(GraphicsContextBase): 
    """ 
    The Cocoa backend does mapping from context values to native graphics 
    commands in the renderer. There is a natural mapping to the Quartz 
    graphics context, however. The possibility of doing the mapping 
    in the GraphicsContextCocoa should be explored 
    """ 
    
    pass 
    



class FigureCanvasView(NSView, FigureCanvasBase): 
    """ 
    NSView and FigureCanvasBase subclass that can render Matplotlib canvas 
    to the Cocoa NSView hierarchy. 
    """ 
    
    def initWithFrame_(self, frame): 
        """Convenience constructor""" 
        
        w,h = frame.size 
        w /= POINTS_PER_INCH 
        h /= POINTS_PER_INCH 
        fig = Figure(figsize=(w, h)) 
        return self.initWithFrame_figure_(frame, fig) 
    
    
    def initWithFrame_figure_(self, frame, fig): 
        """ 
        Designated initializer. 
        
        * Parameters * 
            frame : NSRect 
            fig : matplotlib.figure.Figure 
        """ 
        
        self = super(FigureCanvasView, self).initWithFrame_(frame) 
        if(self != None): 
            FigureCanvasBase.__init__(self, fig) 
            self.renderer = RendererCocoa(self) 
            self.manager = None 
            
            #several methods can change the frame, 
            #so we'll just observe the common notification 
            nc =  NSNotificationCenter.defaultCenter() 
            nc.addObserver_selector_name_object_( 
                self, 
                'frameChanged:', 
                NSViewFrameDidChangeNotification, 
                self, 
                ) 
                
            self.updateFigureSize() 
        
        return self 
    
    
    def frameChanged_(self, notification): 
        assert(notification.object() == self) 
        self.updateFigureSize() 
        
    
    
    def updateFigureSize(self): 
        """set self.figure's size in inches according to current self.frame""" 
        
        w,h = self.frame().size #Cocoa units in points 
        self.figure.set_size_inches(w / POINTS_PER_INCH, h / POINTS_PER_INCH) 
        self.draw() 
    
    
    def draw(self, *args, **kwargs): 
        """ 
        Render the figure at the next screen update 
        """ 
        
        self.setNeedsDisplay_(True) 
    
    
    def drawRect_(self, rect): 
        """Cocoa draw command""" 
        
        self.figure.dpi = self.renderer.dpi 
        self.figure.draw(self.renderer) 
    
    
    def get_default_filetype(self): 
        return 'pdf' 
    
    
    def resize(self, w, h): 
        """set canvas size in pixels""" 
        
        raise NotImplementedError 
    
    
    # TODO override all cocoa event handlers and pass mpl events to figure 
    # TODO override print_* 



class FigureManagerCocoa(NSWindowController, FigureManagerBase): 
    """ 
    Wrap everything up into a window for the pylab interface. 
    """ 
    
    def initWithFigure_number_(self, fig, num): 
        """__init__""" 
        
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_( 
                                        NSMakeRect(100,100,640,480), 
                                        NSBorderlessWindowMask | \
                                        NSTitledWindowMask | \
                                        NSClosableWindowMask | \
                                        NSMiniaturizableWindowMask | \
                                        NSResizableWindowMask, 
                                        NSBackingStoreBuffered, 
                                        True 
                                        ) 
        self = super(FigureManagerCocoa, self).initWithWindow_(win) 
        if(self != None): 
            cViewBounds = self.window().contentView().bounds() 
            plotViewFrame = NSMakeRect(0,0, 
                            cViewBounds.size.width, 
                            cViewBounds.size.height) 
            plotView = FigureCanvasView.alloc().initWithFrame_figure_( 
                                                        plotViewFrame, fig) 
            plotView.setAutoresizingMask_(NSViewWidthSizable | \
                                            NSViewHeightSizable) 
                                            
            FigureManagerBase.__init__(self, plotView, num) 
            
            self.window().contentView().addSubview_(plotView) 
            self.window().setTitle_('Figure %d' % num) 
            
            self.show_window() 
        return self 
    
    
    def set_window_title(self, title): 
        """ 
        Set the title text of the window containing the figure.  Note that 
        this has no effect if there is no window (eg, a PS backend). 
        """ 
        
        if(self.window != None): 
            self.window().setTitle_(title) 
        
    
    
    def show_window(self): 
        """Move window to the screen""" 
        if(NSApp() == None): 
            raise Exception('The Cocoa backend must be run from within \
                            a Cocoa application') 
        
        self.performSelectorOnMainThread_withObject_waitUntilDone_( 
                                                                'showWindow:', 
                                                                self, 
                                                                objc.NO) 
            
    

      

######################################################################## 
# 
# The following functions and classes are for pylab and implement 
# window/figure managers, etc... 
# 
######################################################################## 

def draw_if_interactive(): 
    """ 
    For image backends - is not required 
    For GUI backends - this should be overriden if drawing should be done in 
    interactive python mode 
    """ 
    for manager in Gcf.get_all_fig_managers(): 
        # draw figure managers' views 
        manager.canvas.draw() 


def show(): 
    """ 
    For image backends - is not required 
    For GUI backends - show() is usually the last line of a pylab script and 
    tells the backend that it is time to draw.  In interactive mode, this may 
    be a do nothing func.  See the GTK backend for an example of how to handle 
    interactive versus batch mode 
    """ 
    for manager in Gcf.get_all_fig_managers(): 
        # do something to display the GUI 
        manager.show_window() 


def new_figure_manager(num, *args, **kwargs): 
    """ 
    Create a new figure manager instance 
    """ 
    # if a main-level app must be created, this is the usual place to 
    # do it -- see backend_wx, backend_wxagg and backend_tkagg for 
    # examples.  Not all GUIs require explicit instantiation of a 
    # main-level app (egg backend_gtk, backend_gtkagg) for pylab 
    
    pool = NSAutoreleasePool.alloc().init() 
    
    FigureClass = kwargs.pop('FigureClass', Figure) 
    thisFig = FigureClass(*args, **kwargs) 
    manager = FigureManagerCocoa.alloc().initWithFigure_number_(thisFig, num) 
    return manager 


######################################################################## 
# 
# Now just provide the standard names that backend.__init__ is expecting 
# 
######################################################################## 


FigureManager = FigureManagerCocoa 

class RendererCocoaTests(unittest.TestCase): 
    """Unit tests for RendererCocoa""" 
    
    def test_init_sets_properties(self): 
        """test_init""" 
        
        v = NSView.alloc().initWithFrame_(NSMakeRect(0,0,1,1)) 
        r = RendererCocoa(v) 
        
        self.assertEqual(r.nsview, v) 
    
    def test_mpl_to_affine_transform(self): 
        """test_mpl_to_affine_transform""" 
        import matplotlib.transforms as transforms 
        m = transforms.Affine2D.identity() 
        pass 
    
    
    def test_mpl_to_bezier_path(self): 
        """test_mpl_to_bezier_path""" 
        
        star_path = Path.unit_regular_star(10) 
        r = RendererCocoa(None, None) 
        bpath = r.mpl_to_bezier_path(star_path) 
        
        yield self.assert_paths_equal, star_path, bpath 
        
        wedge_path = Path.wedge(10,25) 
        bpath = r.mpl_to_bezier_path(wedge_path) 
        
        yield self.assert_paths_equal, wedge_path, bpath 
    
    
    def assert_paths_equal(self, mpl, bpath): 
        """asserts that mpl path and nsbezier path are equal""" 
        
        codes = { 
            NSMoveToBezierPathElement       :   Path.MOVETO, 
            NSLineToBezierPathElement       :   Path.LINETO, 
            NSCurveToBezierPathElement      :   Path.CURVE4, 
            NSClosePathBezierPathElement    :   Path.STOP 
        } 
        
        for (i,(pts,code)) in enumerate(mpl.iter_segments()): 
            npts = len(pts)/2 
            if(npts > 1): 
                pts = np.reshape(pts,(2,npts)) 
            else: 
                pts = [pts] 
            elementCode,ptsArray = bpath.elementAtIndex_associatedPoints_(i) #why doesn't this take 2 arguments? 
            
            assert(codes[elementCode] == code or (codes[elementCode]==Path.CURVE4 and code==Path.CURVE3)) 
            assert(npts == len(ptsArray)) 
            for (mplPoint,nsPoint) in zip(pts, ptsArray): 
                self.assertAlmostEqual(mplPoint[0], nsPoint.x) 
                self.assertAlmostEqual(mplPoint[1], nsPoint.y) 
            
    
    


if __name__ == '__main__': 
    matplotlib.use('Cocoa') 
    nose.run(argv=[__file__,__file__]) 
    
    from  matplotlib.pyplot import plot,show,xlabel,ylabel 
    plot(np.random.rand(1000)) 
    xlabel('Test X') 
    ylabel('Test Y') 
    
    show()