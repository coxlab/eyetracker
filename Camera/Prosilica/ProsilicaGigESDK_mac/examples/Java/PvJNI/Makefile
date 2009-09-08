# makefile of GigE SDK Sample code
#

include ../../ARCH

## Executable
EXE	= PvJNI

## Java JDK location
JDK_DIR	= /System/Library/Frameworks/JavaVM.framework

## shared libs
SOLIB	= -L../$(BIN_DIR) -lPvAPI
LIB	= -Bdynamic $(SOLIB) 

## final compilation flags
CFLAGS	= $(OPT) $(FLAGS) -Wall -I../$(INC_DIR) -I$(EXE)/ -I$(JDK_DIR)/Headers -D_REENTRANT $(EXTRA)

$(OBJ_DIR)/%.o : %.cpp
	$(CC) $(CFLAGS) $(VERSION) -c $< -o $@

clean: 
	rm $(EXE)

lib : $(EXE)/$(EXE).cpp $(EXE)/$(EXE).h
	$(CC) $(RPATH) $(TARGET) $(CFLAGS) -dynamiclib -fPIC -shared -Wl,-dylib_install_name,lib$(EXE).dylib $(EXE)/$(EXE).cpp -o lib$(EXE).dylib $(LIB)

install:
	cp -f lib$(EXE).dylib ../$(BIN_DIR)
