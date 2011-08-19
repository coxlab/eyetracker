# makefile of GigE SDK Sample code
#

include ../ARCH

## Executable
EXE	= SampleViewer

## location of the wxWidget library on your system
WX_DIR   = /Users/jlv/Desktop/wxMac-2.8.8/bstatic
#WX_DIR   = /Users/jlv/Desktop/wxMac-2.8.8/universal
## version of the wxWidget to use
WX_VER   = 2.8
## flags & libs for wxWidget
WX_FLAGS = `$(WX_DIR)/wx-config --version=$(WX_VER) --cxxflags` 
WX_LIBS  = `$(WX_DIR)/wx-config --version=$(WX_VER) --libs`

## static libs
PVLIB	 = $(LIB_DIR)/$(CVER)/libPvAPI.a

## shared libs
WXLIB	 = $(WX_LIBS)
LIB      = $(PVLIB) $(WXLIB) -Bdynamic $(EX_LIB)

## final compilation flags
CFLAGS	= $(OPT) $(FLAGS) -Wall $(WX_FLAGS) -I$(INC_DIR) -I./inc -I./rsc -D_REENTRANT $(EXTRA)

$(OBJ_DIR) :
	mkdir -p $(OBJ_DIR)

$(OBJ_DIR)/%.o : ./src/%.cpp ./inc/%.h
	$(CC) $(CFLAGS) $(VERSION) -c $< -o $@

OBJS = \
		$(OBJ_DIR)/mmMultiButton.o \
		$(OBJ_DIR)/treelistctrl.o  \
		$(OBJ_DIR)/Tools.o	   \
		$(OBJ_DIR)/Worker.o	   \
		$(OBJ_DIR)/Seeker.o	   \
		$(OBJ_DIR)/ImageView.o     \
		$(OBJ_DIR)/Application.o   \
		$(OBJ_DIR)/ChildWindow.o   \
		$(OBJ_DIR)/MainWindow.o    \
		$(OBJ_DIR)/InfoWindow.o    \
		$(OBJ_DIR)/FinderWindow.o  \
		$(OBJ_DIR)/CtrlWindow.o

clean: 
	rm $(OBJS)

sample : $(OBJ_DIR) $(OBJS)
	$(CC) $(RPATH) $(TARGET) $(CFLAGS) -o $(EXE) $(OBJS) $(LIB)

install:
	strip $(EXE)
	cp -f $(EXE) $(BIN_DIR)/SampleViewer.app/Contents/MacOS/
