# makefile of GigE SDK Sample code
#

include ../ARCH

## Executable
EXE	= BatchStream

$(OBJ_DIR)/%.o : %.cpp
	$(CC) $(CFLAGS) $(VERSION) -c $< -o $@

clean: 
	rm $(EXE)

sample : $(EXE).cpp
	$(CC) $(RPATH) $(TARGET) $(CFLAGS) $(EXE).cpp -o $(EXE) $(SOLIB) $(PVLIB)

sample-static : $(EXE).cpp
	$(CC) $(RPATH) $(TARGET) $(CFLAGS) $(EXE).cpp $(SALIB) -o $(EXE) $(SOLIB)
	
install:
	$(SP) $(EXE)
	cp -f $(EXE) $(BIN_DIR)
