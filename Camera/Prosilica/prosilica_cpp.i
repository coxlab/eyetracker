%module prosilica_cpp

#define _LINUX 
#define _x86

%{
    #include "PvApi.h"
//    #include "PvRegIo.h"
    #include "Prosilica.h"
	#include "arrayobject.h"
%}

%include "typemaps.i"

%{
#define SWIG_FILE_WITH_INIT
#define PY_ARRAY_UNIQUE_SYMBOL PyArray_API
%}


%include "std_vector.i"
namespace std {
   %template(vector_pv_caminfo) vector<tPvCameraInfo>;
};



%include "PvApi.h"
//%include "PvRegIo.h"


%include "Prosilica.h"


%extend ProsilicaCamera {
    tPvFrame getAndLockCurrentFrame_NoGIL(){
    
        tPvFrame returnval;
        Py_BEGIN_ALLOW_THREADS
        returnval = self->getAndLockCurrentFrame();
        Py_END_ALLOW_THREADS
        
        return returnval;
    } 

}

%extend tPvFrame {

	PyObject* __get_array_struct(){
	PyArrayInterface *inter;

		inter = (PyArrayInterface *)malloc(sizeof(PyArrayInterface));

		inter->two = 2;
		inter->nd = 2;
		inter->typekind = 'u';
		inter->itemsize = sizeof(unsigned char);
		inter->flags = (NPY_CONTIGUOUS | NPY_OWNDATA | NPY_ALIGNED);// |  NPY_NOTSWAPPED);

		Py_intptr_t *shape = (Py_intptr_t *)malloc(2*sizeof(Py_intptr_t));
		shape[1] = self->Width;
		shape[0] = self->Height;
		inter->shape = shape;

		inter->strides = NULL;
		
		inter->data = (void *)(self->ImageBuffer);
		inter->descr = 0;
					
		return PyCObject_FromVoidPtr(inter,0);
	}
    
    int64_t __get_timestamp(){
        int64_t timestamp = 0;
        timestamp += self->TimestampLo;
        timestamp += self->TimestampHi << 32;
        
        return timestamp;
    }
	
	%pythoncode{
		__array_struct__ = property(__get_array_struct, doc="Array Protocol")
	}
}

