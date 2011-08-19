# makefile of GigE SDK Sample code
#

include ../ARCH

## Executable
EXE	= AAViewer

## shared libs
AALIB = -L/usr/lib -laa

$(OBJ_DIR)/%.o : %.cpp
	$(CC) $(CFLAGS) $(VERSION) -c $< -o $@

clean: 
	rm $(EXE)

sample : $(EXE).cpp
	$(CC) $(RPATH) $(TARGET) $(CFLAGS) $(EXE).cpp -o $(EXE) $(SOLIB) $(PVLIB) $(AALIB)

sample-static : $(EXE).cpp
	$(CC) $(RPATH) $(TARGET) $(CFLAGS) $(EXE).cpp $(SALIB) -o $(EXE) $(SOLIB) $(AALIB)
	
install:
	$(SP) $(EXE)
	cp -f $(EXE) $(BIN_DIR)
