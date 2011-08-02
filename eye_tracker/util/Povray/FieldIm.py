

######################################################
# PIL stuff

class Im:
  def __init__(self,x,xx=None):
    self.filename = None
    if xx is not None:
      w,h = x,xx
      im = Image.new("I",(w,h))
    elif type(x)==str:
      filename = x
      im = Image.open(filename)
      self.filename = filename
    elif isinstance(x,Image.Image):
      im = x
    else:
      raise TypeError, ("what's this?", (x,xx))
    self.im = im
    self.w,self.h=self.im.size
    #print "Im mode", self.im.mode
    #self.im.convert("I")
    #print "Im mode now ",self.im.mode
    self.scale,self.offset = 1.0,0.0
    if self.im.mode == "RGBA":
      im = Im(self.w,self.h)
      self.scale *= (1<<16-1)/(3.0*255)
      im.scan(self)
      self.im = im.im
      self.normalize()
  def __str__(self):
    return str( (self.im.mode,self.w,self.h,self.scale,self.offset) )
  def clone(self):
    im = Im(self.im.copy())
    im.offset = self.offset
    im.scale = self.scale
    return im
  def getextrema(self):
    #inf,sup = self.im.getextrema()
    inf=self.im.getpixel((0,0))
    sup=inf
    for x in range(len(self)):
      z = self.im.getpixel( (x%self.w,x/self.w) )
      inf=min(inf,z)
      sup=max(sup,z)
    return inf,sup
  def normalize(self):
    assert self.im.mode == "I"
    inf,sup=self.getextrema()
    self.scale = (1<<16-1)/(sup-inf)
    self.offset = - inf * self.scale
  def __call__(self,x,y):
    w,h=self.im.size
    x*=w; y*=h
    z = self.im.getpixel((x,y))
    #print "z=",repr(z)
    if type(z)==tuple:
      z = z[0]+z[1]+z[2]
    return self.offset+self.scale*float(z)/(1<<16-1)
  def __len__(self):
    return self.w*self.h
  def __getitem__(self,i):
    return self.im.getpixel((i%self.w,i/self.w))*self.scale+self.offset
  def __setitem__(self,i,val):
    self.im.putpixel((i%self.w,i/self.w),(val-self.offset)/self.scale)
  def __add__(self,other):
    if type(other) in (float,int):
      im = self.clone()
      im.offset = self.offset + other
    elif isinstance(other,Im):
      if len(self)!=len(other):
        raise TypeError, ("len mismatch", other)
      im = Im(self.w,self.h)
      for i in range(len(self)):
        im[i] = self[i]+other[i]
    else:
      raise TypeError, ("what's this?", other)
    return im
  def __radd__(self,other):
    return self.__add__(other)
  def __mul__(self,other):
    if type(other) in (float,int):
      im = self.clone()
      im.scale = self.scale * other
      im.offset = self.offset * other
    #elif isinstance(other,Im):
      #data1 = self.im.getdata()
      #data2 = other.im.getdata()
      #if len(data1)!=len(data2):
        #raise TypeError, "what's this?", other
      #im = Im(self.w,self.h)
      #im.im.putdata([ int(
          #(data1[i]*self.scale+self.offset)\
        #* (data2[i]*other.scale+other.offset))
        #for i in range(len(data1)) ])
    else:
      raise TypeError, "what's this?", other
    return im
  #def __rmul__(self,other):
    #return self.__mul__(other)
  #def __getattr__(self,name):
    #if name.startswith("__"):
      #raise AttributeError
    #def f(*args,**kwargs):
      #x=getattr(self.im,name)(*args,**kwargs)
      #if isinstance(x,Image.Image):
        #return Im(x)
      #else:
        #return x
    #return f
  def scan(self,field):
    " field: [0,1]*[0,1] -> [0,1] "
    w,h=self.im.size
    scale = 1<<16-1
    for x in range(w):
      for y in range(h):
        z = int(scale*field(float(x)/w,float(y)/h))
        z = min(scale,max(0,z))
        self.im.putpixel((x,y),z)
    #self.field = field
  def save(self,filename = None):
    if filename is None:
      filename=self.filename
    if filename is None:
      filename = tempfile.mktemp(".png")
    self.im.save( filename, quality=1, optimize=None )
    self.filename=filename
  def blend(self,other,alpha):
    #print "blend",self.im.mode,other.im.mode
    if len(self)!=len(other):
      raise TypeError, ("len mismatch", other)
    im = Im(self.w,self.h)
    for i in range(len(self)):
      #im[i] = self[i]+other[i]
      im[i] = self[i] * (1.0-alpha) + other[i] * alpha
    return im
    #return self * (1.0-alpha) + other * alpha
    #return Im( Image.blend( self.im, other.im, alpha ))

class FieldIm(Im):
  def __init__(self,filename,w,h,field):
    #self.im=im.new("RGB",(w,h))
    #self.im=im.new("L",(w,h))
    Im.__init__(self,w,h)
    self.scan(field)
    self.save(filename)

try:
  # do we have PIL ?
  from PIL import Image
  import tempfile
except ImportError:
  print "Could not import PIL library; FieldIm disabled "
  del FieldIm
  del ImField

