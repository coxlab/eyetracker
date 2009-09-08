# makefile of GigE SDK Sample code
#

include ../ARCH

## Executable
EXE	= ListAttributes

## shared libs
SOLIB	= -L$(BIN_DIR) -lPvAPI
LIB	    = -Bdynamic $(SOLIB) 

## final compilation flags
CFLAGS	= $(OPT) $(FLAGS) -Wall -I$(INC_DIR) -D_REENTRANT $(EXTRA)

$(OBJ_DIR)/%.o : %.cpp
	$(CC) $(CFLAGS) $(VERSION) -c $< -o $@

clean: 
	rm $(EXE)

sample : $(EXE).cpp
	$(CC) $(RPATH) $(TARGET) $(CFLAGS) $(EXE).cpp -o $(EXE) $(LIB)

install:
	strip $(EXE)
	cp -f $(EXE) $(BIN_DIR)
