# makefile for eyetracker prosilica camera module

# EDIT HERE if you want to build against a different python distribution
PYTHON = python
#PYTHON = /Library/Frameworks/EPD64.framework/Versions/Current/bin/python

# Target CPU
CPU	 = x64

# Target OS
#OS      = LINUX
OS	= OSX

OS_DIR  = OSX

# OS-X version
OSXV	= -mmacosx-version-min=10.6


# Optimisation level
#OPT     = -O3
OPT	 = -O0 $(OSXV)

# compiler version
ifeq ($(OS), OSX)
	CVER    = 4.2
else
	CVER	= 4.2
endif

PYTHONVER	= 2.7

# compiler
CC      = g++-$(CVER)

# linker
LD      = ld
AR      = ar

# some flags
DFLAGS	= -D_$(CPU) -D_$(OS)
FLAGS   = -fno-strict-aliasing -fexceptions -I/usr/include $(DFLAGS)

## few locations
ifeq ($(OS), OSX)
     PROSILICA_BASE= ProsilicaGigESDK_mac
else
     PROSILICA_BASE= ProsilicaGigESDK
endif

PROSILICA_INC_DIR	  = $(PROSILICA_BASE)/inc-pc
PROSILICA_BIN_DIR   = $(PROSILICA_BASE)/bin-pc/$(CPU)/$(CVER)
PROSILICA_LIB_DIR   = $(PROSILICA_BASE)/lib-pc/$(CPU)/$(CVER)


OBJ_DIR ="./"

ifeq ($(OS), OSX)
	EXTRA_LIB = -lpthread -lpython$(PYTHONVER)
else
	EXTRA_LIB = -lpthread -lrt -lpython$(PYTHONVER)
endif


PYTHONHOME_ = `$(PYTHON) -c "import sys; print sys.prefix" `

ifeq ($(OS), OSX)
	PYTHON_INC=$(PYTHONHOME_)/include/python$(PYTHONVER)
	PYTHON_LIB=$(PYTHONHOME_)/lib
else
	PYTHON_INC=/usr/include/python$(PYTHONVER)
	PYTHON_LIB="/usr/lib"
endif


NUMPY_INC= $(PYTHONHOME_)/lib/python$(PYTHONVER)/site-packages/numpy/core/include

INC_DIR = "/usr/include"

## modules
PROSILICA_MODULE	= _prosilica_cpp.so

## Prosilica Sources
PROSILICA_SRCS	= Prosilica.cxx prosilica_cpp_wrap.cxx
PROSILICA_OBJS	= ${PROSILICA_SRCS:%.cxx=%.o}


## shared libs & !shared libs
ifeq ($(OS), OSX)
	SHARED_LIBS	= -L$(PYTHON_LIB) $(EXTRA_LIB) -Bdynamic  -lm -lc  -framework CoreFoundation
else
	SHARED_LIBS	= -L$(PYTHON_LIB) $(EXTRA_LIB) -Bdynamic  -lm -lc 
endif

PROSILICA_STATIC_LIBS	= -Bstatic $(PROSILICA_LIB_DIR)/libImagelib.a $(PROSILICA_LIB_DIR)/libPvAPI.a

## final compilation flags
CFLAGS	= $(OPT) $(FLAGS) -g -Wall -I$(PROSILICA_INC_DIR) -I$(INC_DIR)  -I$(NUMPY_INC) -I$(PYTHON_INC) -D_REENTRANT $(EXTRA)
#CFLAGS	= $(OPT) $(FLAGS) -g -Wall -I$(PROSILICA_INC_DIR) -I$(INC_DIR) -I$(PYTHON_INC) -D_REENTRANT $(EXTRA)

# ifeq ($(OS), OSX)
# 	LDFLAGS	= -g -shared -bundle
# else
LDFLAGS = -g -shared
# endif

all: prosilica_module


%.o:%.cxx
	$(CC) $(CFLAGS) -fPIC $(VERSION) -c $<

%.o:%.cpp
	$(CC) $(CFLAGS) -fPIC $(VERSION) -c $<


clean: 
	rm *.o	
	rm $(PROSILICA_MODULE)

prosilica_swig:
	swig -shadow -c++ -python -I$(PROSILICA_INC_DIR) prosilica_cpp.i

prosilica_module: prosilica_swig $(PROSILICA_OBJS)
	$(CC) $(LDFLAGS) $(PROSILICA_OBJS) $(PROSILICA_STATIC_LIBS) -o $(PROSILICA_MODULE) $(SHARED_LIBS)
