# makefile of GigE SDK Sample code
#

include ../../ARCH

## Executable
EXE	= PvJNI

## Java JDK location
JDK_DIR	= /usr/lib/jvm/java-6-openjdk

## path where to look for PvAPI shared lib
RPATH	= -Wl,--rpath -Wl,./ 

## shared libs
SOLIB	= -L ../$(BIN_DIR) -lPvAPI
LIB	= -Bdynamic $(SOLIB) 

## final compilation flags
CFLAGS	= $(OPT) $(FLAGS) -Wall -I../$(INC_DIR) -I$(EXE)/ -I$(JDK_DIR)/include -I$(JDK_DIR)/include/linux -D_REENTRANT $(EXTRA)

$(OBJ_DIR)/%.o : %.cpp
	$(CC) $(CFLAGS) $(VERSION) -c $< -o $@

clean: 
	rm lib$(EXE).so

lib : $(EXE)/$(EXE).cpp $(EXE)/$(EXE).h
	$(CC) $(RPATH) $(TARGET) $(CFLAGS) -fPIC -shared -Wl,-soname,lib$(EXE).so $(EXE)/$(EXE).cpp -o lib$(EXE).so $(LIB)
#	$(CC) $(RPATH) $(TARGET) $(CFLAGS) $(EXE).cpp -o $(EXE) $(LIB)

install:
	strip lib$(EXE).so
	cp -f lib$(EXE).so ../$(BIN_DIR)
