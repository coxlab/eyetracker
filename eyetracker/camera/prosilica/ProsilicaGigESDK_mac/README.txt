### AVT GigE SDK 1.24 for Mac OS X
###
### 05/04/11
###

Notes:

* This distribution support x86, PPC,x64 for OS X 10.4 to 10.6. Modify the "ARCH" file located in the Examples directory before building the samples to select the proper architecture: x86, ppc or x64.

* A compiled version of the SampleViewer is provided for convenience. It is statically linked with wxWidgets (installing/compiling wxMac isn't required) and with PvAPI. Since wxMac is built on top of Carbon, there is NO 64-bit viewer.

* The shared library in ./bin-pc is usable with software compiled with either GCC 4.0 or GCC 4.2

* Static libraries are provides for GCC 4.0 and 4.2, they can be found in ./lib-pc

* Each of the sample code can be build as follow:

  > make sample ; make install

The executables will be copied into the ./bin-pc folder.

* The provided viewer require wxMAC (>= 2.6, unicode). The makefile can be modified to use the version you have installed on your system.

* A route for 255.255.255.255 may need to be added to point to the adapter on which the camera will be plugged (or to the switch on which the camera will be). This can be done with the following command:

  > sudo route -n add 255.255.255.255 169.254.42.97

where 169.254.42.97 is the IP (self-assigned or assigned by you) of the adapter

* The MTU of the GigE adapter should be changed to accommodate for Jumbo frames using the command line tool "ifconfig". If the MTU is set to a lower value, the camera's settings ("PacketSize") should be adjusted.

* In order to use multicasting, you may have to add manually a route. The syntax is as follow:

  > sudo route -n add -net 224.0.0.0 netmask 240.0.0.0 dev en3

where en3 is the adapter name (replace by yours).

* The Java folders contains an JNI interface to PvAPI, plus a set of sample code. You will need to use the build.xml file located in each subdirectory to import the project with Eclipse. Each of the following samples: JListAttributes, JListCameras, JSnap, JStream, JThread, JThread3 need to have PvJPI in its build path. For convenience, the JNI dynamic library has been built and placed in the bin-pc folder. Each of the Java samples need in its Run/debug settings the following added to its VM argument: -Djava.library.path=/path/to/the/SDK/bin-pc/x86. The working directory will also have to be /path/to/the/SDK/bin-pc/x86.
