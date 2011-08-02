# makefile of GigE SDK Sample code
#

include ../ARCH

## Executable
EXE	= StaticSnap

## shared libs & !shared libs
SOLIB	= $(EXTRA_LIB) -Bdynamic -lm -lc -lz -framework Foundation
SALIB	= -Bstatic $(LIB_DIR)/$(CVER)/libImagelib.a $(LIB_DIR)/$(CVER)/libPvAPI.a

## final compilation flags
CFLAGS	= $(OPT) $(FLAGS) -Wall -I$(INC_DIR) -D_REENTRANT $(EXTRA)

$(OBJ_DIR)/%.o : %.cpp
	$(CC) $(CFLAGS) $(VERSION) -c $< -o $@

clean: 
	rm $(EXE)

sample : $(EXE).cpp
	$(CC) $(RPATH) $(TARGET) $(CFLAGS) $(EXE).cpp $(SALIB) -o $(EXE) $(SOLIB)

install:
	strip $(EXE)
	cp -f $(EXE) $(BIN_DIR)
