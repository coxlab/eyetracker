#
#  EyeFeatureFinder.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 7/29/08.
#  Copyright (c) 2008 __MyCompanyName__. All rights reserved.
#


#from CobraEyeTrackerCpp import *
from numpy import *
import scipy
from scipy.weave import inline
from scipy.weave import converters
#from handythread import *
from scipy import signal
from EdgeDetection import *
from EyeFeatureFinder import *
from stopwatch import *

class FastRadialFeatureFinder (EyeFeatureFinder):
	
    
    def __init__(self):
        
        # reusable storage
        self.cached_shape = None
        self.cached_gauss2d_fft = None
        self.M = None
        self.O = None
        self.F = None
        self.S = None
        self.sepfir_firstpass = None
        
        # parameters
        self.reuse_storage = 0
        self.use_sse3 = 0
        self.c_typestring = "double"
        self.filter = "sepfir"
        self.target_kpixels = 43.0 #8.0
        self.max_target_kpixels = 50.0
        self.min_target_kpixels = 1.0
        self.parameters_updated = 1
        self.gaussian_kernel_cheat = 1.0
        self.alpha = 10.
        self.min_radius_fraction = 0.0226 #1./2000.
        self.max_radius_fraction = 0.0956 #1./8.
        self.min_fraction = 1./1000.
        self.max_fraction = 0.35
        self.radius_steps = 6
        self.radiuses_to_try = [1]
        self.ds_factor = 1
        
        self.correct_downsampling = False
        
        self.do_refinement_phase = 0
        
        self.shortcut_at_sobel = 0
        
        self.cache_sobel = True
        self.cached_sobel = None
        self.compute_sobel_avg = True # for autofocus
        self.sobel_avg = None
        
        # Voting
        self.outlier_cutoff = 1.
        self.maxmin_consensus_votes = 1
        
        self.image_contribution = 1
        
        self.last_positions = []
        
        self.available_filters = [u"sepfir", u"spline", u"fft", u"convolve2d"]
        
        self.result = None
    
    # analyze the image and return dictionary of features gleaned
    # from it
    #@clockit
    def analyze_image(self, image, guess = None, **kwargs):
    
        im_array = image.astype(double)
        im_array = im_array[::self.ds_factor, ::self.ds_factor]
        
        if(guess != None):
            features = guess
        else:
            features = {'pupil_size' : None,
                        'cr_size' : None }	
		
        if(kwargs.has_key("filter")):
            self.filter = kwargs["filter"]
		
        
        if(self.parameters_updated or self.cached_shape != im_array.shape):
            print "Recaching..."
            print "Target kPixels: ", self.target_kpixels
            print "Max Radius Fraction: ", self.max_radius_fraction
            print "Radius steps: ", self.radius_steps
            im_pixels = image.shape[0] * image.shape[1]
            self.ds_factor = int(sqrt(im_pixels / int(self.target_kpixels*1000)))
            if(self.ds_factor <= 0):
                self.ds_factor = 1
            im_array = image[::self.ds_factor, ::self.ds_factor]
            
            self._init_reusable_storage(im_array)
            self.parameters_updated = 0
            
            self.radiuses_to_try = linspace(ceil(self.min_radius_fraction*im_array.shape[0]), ceil(self.max_radius_fraction*im_array.shape[0]), self.radius_steps)
            self.radiuses_to_try = unique(self.radiuses_to_try.astype(int))
            print "Radiuses to try: ", self.radiuses_to_try
            print "Downsampling factor: ", self.ds_factor
			
        ds = self.ds_factor;
        
        
        S = self._fastradial(im_array, self.radiuses_to_try, self.alpha, weave=1, filter=self.filter)
		
        if(self.maxmin_consensus_votes == 1):
            (min_coords, max_coords) = self._find_image_minmax(S)
        else:
            (min_coords, max_coords) = self._findConsensusMinMax(S, self.maxmin_consensus_votes, self.outlier_cutoff)
        
        if(self.shortcut_at_sobel or not self.do_refinement_phase): 
            if(self.correct_downsampling):
                features['pupil_position'] = array([min_coords[0], min_coords[1]]) * ds
                features['cr_position'] = array([max_coords[0], max_coords[1]]) * ds 
                features['dwnsmp_factor_coord'] = 1           
            else:
                features['pupil_position'] = array([min_coords[0], min_coords[1]])
                features['cr_position'] = array([max_coords[0], max_coords[1]])      
                features['dwnsmp_factor_coord'] = ds      

            features['transform'] = S
            features['im_array'] = im_array
            features['im_shape'] = im_array.shape
            
            self.result = features
        else:
            # do a second "refinement" pass
            halfwidth = round(sqrt(1000. * self.target_kpixels)/2.)
            min_coords *= ds
            max_coords *= ds
            leftedge = round(min(min_coords[1], max_coords[1]) - halfwidth)
            rightedge = round(max(min_coords[1], max_coords[1]) + halfwidth)
            topedge = round(min(min_coords[0], max_coords[0]) - halfwidth)
            bottomedge = round(max(min_coords[0], max_coords[0]) + halfwidth)
            
            print "[", topedge, ",", bottomedge, ",", leftedge, ",", rightedge, "]"
            
            im_array2 = (image[topedge:bottomedge, leftedge:rightedge]).astype(double)
            print im_array2.shape
            print halfwidth
            
            size_ratio = max(im_array2.shape) / max(im_array.shape)
            
            refinement_radiuses = unique((self.radiuses_to_try * ds).astype(int))
            
            self.cached_sobel = None
            S2 = self._fastradial(im_array2, refinement_radiuses, self.alpha, weave=1, filter=self.filter)
            
            (min_coords2, max_coords2) = self._find_consensus_minmax(S2, self.maxmin_consensus_votes*ds**2, self.outlier_cutoff*ds)
            #features['pupil_position'] = array([max_coords2[0], max_coords2[1]]) #* ds
            #features['cr_position'] = array([min_coords2[0], min_coords2[1]]) #*ds            
            features['pupil_position'] = array([min_coords2[0], min_coords2[1]]) #* ds
            features['cr_position'] = array([max_coords2[0], max_coords2[1]]) #*ds
            features['im_array'] = im_array2
            features['transform'] = S2
            features['dwnsmp_factor_coord'] = ds
            features['im_shape'] = im_array2.shape
            
        if(self.cache_sobel):
            features['cached_sobel'] = self.cached_sobel
        
        if(self.compute_sobel_avg):
            self.sobel_avg = sum(sum(self.cached_sobel))
            features['sobel_avg'] = self.sobel_avg / (self.cached_sobel.shape[0] * self.cached_sobel.shape[1])
        
        self.result = features
            
    def update_parameters(self):
        self.parameters_updated = 1
        
    def get_result(self):
        return self.result


    def _init_reusable_storage(self, image):
        self.dtype = image.dtype
        if(dtype == float32):
            self.c_typestring = 'float'
        else:
            self.c_typestring = 'double'
			
        self.cached_shape = image.shape
        self.cached_gauss2d_fft = None
        self.M = zeros_like(image)
        self.O = zeros_like(image)
        self.F = zeros_like(image)
        self.S = zeros_like(image)
        self.sepfir_firstpass = zeros_like(image)
        self.sepfir_result = zeros_like(image)
        return
	
    # borrowed with some translation from Peter Kovesi's fastradial.m
    def _fastradial(self, image, radii, alpha, **kwargs):
		
                	
        if(kwargs.has_key("weave")):
            use_weave = kwargs["weave"]
        else:
            use_weave = 0
		
        use_spline_approximation = 0
        use_sep_fir = 0
        use_fft_filter = 0
		
        if(kwargs.has_key("filter")):
            if(kwargs["filter"] == "spline"):
                use_spline_approximation = 1
            elif(kwargs["filter"] == "sepfir"):
                use_sep_fir = 1
            elif(kwargs["filter"] == "fft"):
                use_fft_filter = 1
                if(self.cached_gauss2d_fft == None):
                    self.cached_gauss2d_fft = {}
                    for r in radii:
                        gauss1d_x = signal.gaussian(self.cached_shape[0], 0.25 * r)
                        gauss1d_x.shape = (1,gauss1d_x.shape[0])
                        
                        gauss1d_y = signal.gaussian(self.cached_shape[1], 0.25 * r)
                        gauss1d_y.shape = (1,gauss1d_y.shape[0])
                        
                        gauss2d_fft = signal.ifft2(dot(gauss1d_x.T, gauss1d_y))
                    
                        self.cached_gauss2d_fft[r] = sqrt(real(gauss2d_fft)**2 + imag(gauss2d_fft)**2)
				
		
        (rows, cols) = image.shape
        
        #(mag, imgx, imgy) = self._sobel3x3separable(image)
        (mag, imgx, imgy) = sobel3x3_separable(image, self.use_sse3)
        
        if(self.cache_sobel):
            self.cached_sobel = mag
        
        #(mag, imgx, imgy) = Sobel3x3(image)
        #(mag, imgx, imgy) = self._sobel3x3(image)
        if(self.shortcut_at_sobel):
            return mag
		
        # Normalise gradient values so that [imgx imgy] form unit
        # direction vectors.
        imgx = imgx / mag
        imgy = imgy / mag
		
        Ss = list(radii)
        
        (y,x) = mgrid[0:rows, 0:cols]  #meshgrid(1:cols, 1:rows);
        
        #S_sub = zeros((rows,cols))
		
        if(self.reuse_storage):
		
            M = self.M  # Magnitude projection image
            O = self.O  # Orientation projection image
            F = self.F # the result, prior to accumulation
            S = self.S # the accumulated result
            self._fast_clear_array2d(S)    
        else:
            M = zeros_like(image)
            O = zeros_like(image)
            F = zeros_like(image)
            S = zeros_like(image)
        
        for r in range(0, len(radii)):
            
            n = radii[r]
		    
            if(1 or self.reuse_storage):
                self._fast_clear_array2d(M)
                self._fast_clear_array2d(O)
                self._fast_clear_array2d(F)
            else:
                M = zeros_like(image)
                O = zeros_like(image)
                F = zeros_like(image)
	        
            # Coordinates of 'positively' and 'negatively' affected pixels
            posx = x + (n*imgx);
            posy = y + (n*imgy);
			
            negx = x - (n*imgx);
            negy = y - (n*imgy);
		
            # Clamp Orientation projection matrix values to a maximum of
            # +/-kappa,  but first set the normalization parameter kappa to the
            # values suggested by Loy and Zelinski
            kappa = 9.9
            if(n == 1):
                kappa = 8
                            
            # Form the orientation and magnitude projection matrices
            if(use_weave):
                code = """
				Py_BEGIN_ALLOW_THREADS
				
				int rows = Nmag[0];
				//int rstart = 0;
				//int rend = rows;
				int tile_size = rows / n_tiles;
				int rstart = (tile) * tile_size;
				int rend;
				if(tile == n_tiles-1){
					rend = rows;
				} else {
					rend = (tile+1) * tile_size - 1; 
				} 
				
				int cols = Nmag[1];
				int cstart = 0;
				int cend = cols;
				
				for(int r = rstart; r < rend; r++){
					for(int c = cstart; c < cend; c++){
						int index = r*cols + c;
						
						int posx_ = round(posx[index]);
						int posy_ = round(posy[index]);
						int negx_ = round(negx[index]);
						int negy_ = round(negy[index]);
						
						if(posx_ < 0 || posx_ > cols-1 ||
						   posy_ < 0 || posy_ > rows-1 ||
						   negx_ < 0 || negx_ > cols-1 ||
						   negy_ < 0 || negy_ > rows-1){
							continue;
						}
						
						if(posx_ < 0) posx_ = 0;
						if(posx_ > cols-1) posx_ = cols-1;
						if(posy_ < 0) posy_ = 0;
						if(posy_ > rows-1) posy_ = rows-1;
						
						if(negx_ < 0) negx_ = 0;
						if(negx_ > cols-1) negx_ = cols-1;
						if(negy_ < 0) negy_ = 0;
						if(negy_ > rows-1) negy_ = rows-1;
						
						int pos_index = (int)posy_*cols + (int)posx_;
						int neg_index = (int)negy_*cols + (int)negx_;
						
						O[pos_index] += 1.0;
						O[neg_index] -= 1.0;
						
						M[pos_index] += mag[index];
						M[neg_index] -= mag[index];
					}
				}
				
				for(int r = rstart; r < rend; r++){
					for(int c=cstart; c < cend; c++){
						int index = r*cols + c;
						double O_ = abs(O[index]);
						if(O_ > kappa) O_ = kappa;
						
						F[index] = M[index]/kappa * pow(O_/kappa, alpha);
					}
				}
				
				
				Py_END_ALLOW_THREADS
				"""
				
                multithreaded_weave = 0
				
                def run_inline(tile, O,M,mag,posx,posy,negx,negy,kappa,F,alpha,n_tiles):	
                    inline(code, ['O','M', 'mag','posx','posy','negx','negy','kappa', 'F', 'alpha', 'n_tiles', 'tile'], verbose=2)#, type_converters=converters.blitz)
                
                if(multithreaded_weave):
                    n_tiles = 2
                    foreach(lambda t: run_inline(t,O,M,mag,posx,posy,negx,negy,kappa,F,alpha,n_tiles), range(0,n_tiles), 2)
                else:
                    n_tiles = 1
                    tile = 0
                    inline(code, ['O','M', 'mag','posx','posy','negx','negy','kappa', 'F', 'alpha', 'n_tiles', 'tile'], verbose=2)
            else:
                
                posx = posx.round()
                posy = posy.round()
                negx = negx.round()
                negy = negy.round()
                
                # Clamp coordinate values to range [1 rows 1 cols]
                posx[ where(posx<0) ]    = 0;
                posx[ where(posx>cols-1) ] = cols-1;
                posy[ where(posy<0) ]    = 0;
                posy[ where(posy>rows-1) ] = rows-1;
                
                negx[ where(negx<0) ]    = 0;
                negx[ where(negx>cols-1) ] = cols-1;
                negy[ where(negy<0) ]    = 0;
                negy[ where(negy>rows-1) ] = rows-1;
                
                for r in range(0,rows):
                    for c in range(0,cols):
                        O[posy[r,c],posx[r,c]] += 1;
                        O[negy[r,c],negx[r,c]] -= 1;
                        
                        M[posy[r,c],posx[r,c]] += mag[r,c];
                        M[negy[r,c],negx[r,c]] -= mag[r,c];
                
                O[where(O >  kappa)] =  kappa
                O[where(O < -kappa)] = -kappa
                
                # Unsmoothed symmetry measure at this radius value
                F = M / kappa * (abs(O)/kappa)**alpha;
            
            
            # Generate a Gaussian of size proportional to n to smooth and spread
            # the symmetry measure.  The Gaussian is also scaled in magnitude
            # by n so that large scales do not lose their relative weighting.
            #A = fspecial('gaussian',[n n], 0.25*n) * n;
            #S = S + filter2(A,F);
            gauss1d = scipy.signal.gaussian(round(self.gaussian_kernel_cheat * n), 0.25*n)
                    
            if(use_spline_approximation):
                S += signal.spline_filter(F, 0.25*n)
            elif(use_sep_fir):
                #S += signal.sepfir2d(F, gauss1d, gauss1d)
                #S += self._manualSepFir2d(F, gauss1d, gauss1d)
                
                #S += self._wovenSepFir2d(F, gauss1d, gauss1d)
                S += woven_sepfir2d(F, gauss1d, gauss1d)
            elif(use_fft_filter):
                fft_kernel = self.cached_gauss2d_fft[n]
                complex_result = signal.ifft2(signal.fft2(F) * fft_kernel)
                S += sqrt(real(complex_result)**2 + imag(complex_result)**2)
            else:
                gauss1d.shape = (1, gauss1d.shape[0])
                gauss2d = dot(gauss1d.T, gauss1d)
                S += signal.convolve2d(F, gauss2d, mode='same', boundary='symm')
            
            #Ss[r] = S_sub
        
        #S = sum(Ss,0)		
        
        S = S/len(radii);  # Average
        
        return S
            
    
    def _fast_clear_array2d(self, arr):
        
        code = """
			Py_BEGIN_ALLOW_THREADS
			
			int rows = Narr[0];
			int cols = Narr[1];
			
			for(int r=0; r < rows; r++){
				for(int c=0; c < cols; c++){
					double *arr_ptr = (double *)((char *)arr_array->data + r*arr_array->strides[0] + c*arr_array->strides[1]);
					*arr_ptr = 0.0;
				}
			}
			
			Py_END_ALLOW_THREADS
			"""
            
        inline(code, ['arr'])
        
        return
        
    def _manual_sepfir2d(self, image, row, col):
        
        row.shape = (row.shape[0], 1)
        firstpass = signal.convolve2d(image, row, mode='same', boundary='symm')
        col.shape = (1,col.shape[0])
        result = signal.convolve2d(firstpass, col, mode='same', boundary='symm')
        return result
		
        
    def _find_consensus_minmax(self, transform_image, n, outlier_cutoff):
        code = """
			Py_BEGIN_ALLOW_THREADS
			#define TYPE	double
			#define BIG  9999999
            #define SMALL -BIG
            
			int rows = Ntransform_image[0];
			int cols = Ntransform_image[1];
			
			double most_max = SMALL; // the true max
            double least_max = SMALL; // the last value that makes "the cut"
            int most_max_index = -1;
            int least_max_index = 0;
            int max_fill_level = 0;
            
            double most_min = BIG;  // the true min
			double least_min = BIG;  // the last value making "the cut"
			int most_min_index = -1;
            int least_min_index = 0;
            int min_fill_level = 0;
            
            int n = Nmax_values[0];
            
            double *max_values_ptr;
            double *max_coordinates_x_ptr;
            double *max_coordinates_y_ptr;
            
            double *min_values_ptr;
            double *min_coordinates_x_ptr;
            double *min_coordinates_y_ptr;
            
            //printf("%d\\n", n);
			for(int r = 0; r < rows; r++){
				for(int c = 0; c < cols; c++){
					
					double *pixel_ptr = (double *)((char *)transform_image_array->data + r * transform_image_array->strides[0] + c * transform_image_array->strides[1]);
					
					
                    
                    double value = *pixel_ptr;
                    
                    // Buffer not full yet
					if(max_fill_level < n && value > least_max){
						
                        // add this pixel to the current winner's circle
                        max_values_ptr = (double *)((char *)max_values_array->data + max_values_array->strides[0]*max_fill_level);
                        max_coordinates_x_ptr = (double *)((char *)max_coordinates_x_array->data + max_coordinates_x_array->strides[0]*max_fill_level);
                        max_coordinates_y_ptr = (double *)((char *)max_coordinates_y_array->data + max_coordinates_y_array->strides[0]*max_fill_level);
                        
                        *max_values_ptr = value;
                        *max_coordinates_x_ptr = (double)r;
                        *max_coordinates_y_ptr = (double)c;
                        
                        if(value > most_max){
                            most_max = value;
                            
                            most_max_index = max_fill_level;
                        }
                        
                        max_fill_level++;
                        //printf("max fill: %d\\n", max_fill_level); 
                        
                        
                        // find out who's on the edge now
                        least_max = most_max;
                        for(int i = 0; i < max_fill_level; i++){
                            max_values_ptr = (double *)((char *)max_values_array->data + max_values_array->strides[0]*i);
                        
                            if(*max_values_ptr < least_max){
                                least_max_index = i;
                                least_max = *max_values_ptr;
                            }
                        }
                            
					} else if(value > least_max){
                        // No matter what, this entry displaces the "least max" entry
                        max_values_ptr = (double *)((char *)max_values_array->data + max_values_array->strides[0]*least_max_index);
                        max_coordinates_x_ptr = (double *)((char *)max_coordinates_x_array->data + max_coordinates_x_array->strides[0]*least_max_index);
                        max_coordinates_y_ptr = (double *)((char *)max_coordinates_y_array->data + max_coordinates_y_array->strides[0]*least_max_index);
                        
                        *max_values_ptr = value;
                        *max_coordinates_x_ptr = (double)r;
                        *max_coordinates_y_ptr = (double)c;
                                                
                        // if it happens to be the biggest, reset the "most max" index and value
                        if(value > most_max){
                            most_max = value;
                            most_max_index = least_max_index;
                        }
                        
                        // find out who's on the edge now
                        least_max = most_max;
                        for(int i = 0; i < max_fill_level; i++){
                            max_values_ptr = (double *)((char *)max_values_array->data + max_values_array->strides[0]*i);
                        
                            if(*max_values_ptr < least_max){
                                least_max_index = i;
                                least_max = *max_values_ptr;
                            }
                        }
                    }
                        
                    
                    // ===================
                    // MIN
                    // ===================
                    
                    
                    // Buffer not full yet
					if(min_fill_level < n && value < least_min){
						
                        // add this pixel to the current winner's circle
                        min_values_ptr = (double *)((char *)min_values_array->data + min_values_array->strides[0]*min_fill_level);
                        min_coordinates_x_ptr = (double *)((char *)min_coordinates_x_array->data + min_coordinates_x_array->strides[0]*min_fill_level);
                        min_coordinates_y_ptr = (double *)((char *)min_coordinates_y_array->data + min_coordinates_y_array->strides[0]*min_fill_level);
                        
                        *min_values_ptr = value;
                        *min_coordinates_x_ptr = (double)r;
                        *min_coordinates_y_ptr = (double)c;
                        
                        if(value < most_min){
                            most_min = value;
                            most_min_index = min_fill_level;
                        }
                        
                        min_fill_level++;
                        
                        
                        // find out who's on the edge now
                        least_min = most_min;
                        for(int i = 0; i < min_fill_level; i++){
                            min_values_ptr = (double *)((char *)min_values_array->data + min_values_array->strides[0]*i);
                        
                            if(*min_values_ptr > least_min){
                                least_min_index = i;
                                least_min = *min_values_ptr;
                            }
                        }
                            
					} else if(value < least_min){
                        // No matter what, this entry displaces the "least min" entry
                        min_values_ptr = (double *)((char *)min_values_array->data + min_values_array->strides[0]*least_min_index);
                        min_coordinates_x_ptr = (double *)((char *)min_coordinates_x_array->data + min_coordinates_x_array->strides[0]*least_min_index);
                        min_coordinates_y_ptr = (double *)((char *)min_coordinates_y_array->data + min_coordinates_y_array->strides[0]*least_min_index);
                        
                        *min_values_ptr = value;
                        *min_coordinates_x_ptr = (double)r;
                        *min_coordinates_y_ptr = (double)c;
                        
                        
                        // if it happens to be the biggest, reset the "most min" index and value
                        if(value < most_min){
                            most_min = value;
                            most_min_index = least_min_index;
                        }
                        
                        // find out who's on the edge now
                        least_min = most_min;
                        for(int i = 0; i < min_fill_level; i++){
                            min_values_ptr = (double *)((char *)min_values_array->data + min_values_array->strides[0]*i);
                        
                            if(*min_values_ptr > least_min){
                                least_min_index = i;
                                least_min = *min_values_ptr;
                            }
                        }
                    }
					
				}
			}
            
            
            //printf("most max: %g\\n", most_max);
//            printf("least max: %g\\n", least_max);
//            printf("most min: %g\\n", most_min);
//            printf("least min: %g\\n", least_min);
//            printf("max_values[0]: %g\\n", max_values[0]);
			Py_END_ALLOW_THREADS
		""" #% self.c_typestring
		
        max_values = zeros(n, dtype='double')
        max_coordinates_x = zeros(n, dtype='double')
        max_coordinates_y = zeros(n, dtype='double')
        
        min_values = zeros(n, dtype='double')
        min_coordinates_x = zeros(n, dtype='double')
        min_coordinates_y = zeros(n, dtype='double')
        
        inline(code, ['transform_image', 'max_values', 'max_coordinates_x', 'max_coordinates_y', 'min_values', 'min_coordinates_x','min_coordinates_y'], verbose=2)
        
                    
        max_values = max_values / sum(max_values)
        min_values = min_values / sum(min_values)
        
        cluster_limit = outlier_cutoff
        
        max_sorted_indexes = list(argsort(max_values))
        max_sorted_indexes.reverse()
        min_sorted_indexes = list(argsort(min_values))
        min_sorted_indexes.reverse()
        
        # the max will seed the first cluster
        max_index = max_sorted_indexes[0]
        clusters = [[max_index]]
        cluster_means = [ array([ max_coordinates_x[max_index], max_coordinates_y[max_index]])]
        cluster_members = [1]
        cluster_values = [max_values[max_index]]
        
        # for each additional data point
        for i in range(1, len(max_sorted_indexes)):
            coord = array([max_coordinates_x[i], max_coordinates_y[i]])
            
            # for each cluster
            for c in range(0, len(clusters)):
                cm = cluster_means[c]
                d = cm - coord
                if(sqrt(d[0]**2+d[1]**2) < cluster_limit):
                    # agglomerate
                    clusters[c].append(i)
                    members = ix_(clusters[c])
                    max_values_normed = max_values[members] / sum(max_values[members])
                    cluster_means[c] = array([sum(max_values_normed * max_coordinates_x[members]),
                                              sum(max_values_normed * max_coordinates_y[members])])
                    #cluster_means[c] = ( cluster_means[c] * cluster_members[c] + coord) / (cluster_members[c]+1)
                    cluster_members[c] += 1
                    cluster_values[c] += max_values[i]
                    break
                else:
                    clusters.append([i])
                    cluster_means.append(coord)
                    cluster_members.append(1)
                    cluster_values.append(max_values[i])
                    break
        
        sorted_values = list(argsort(cluster_values))
        sorted_values.reverse()
        winner = sorted_values[0]
        max_coords = cluster_means[winner]


        
        # the max will seed the first cluster
        min_index = min_sorted_indexes[0]
        clusters = [[min_index]]
        cluster_means = [ array([ min_coordinates_x[max_index], min_coordinates_y[max_index]])]
        cluster_members = [1]
        cluster_values = [min_values[min_index]]
        
        # for each additional data point
        for i in range(1, len(min_sorted_indexes)):
            coord = array([min_coordinates_x[i], min_coordinates_y[i]])
            
            # for each cluster
            for c in range(0, len(clusters)):
                cm = cluster_means[c]
                d = cm - coord
                if(sqrt(d[0]**2+d[1]**2) < cluster_limit):
                    # agglomerate
                    clusters[c].append(i)
                    members = ix_(clusters[c])
                    min_values_normed = min_values[members] / sum(min_values[members])
                    cluster_means[c] = array([sum(min_values_normed * min_coordinates_x[members]),
                                              sum(min_values_normed * min_coordinates_y[members])])
                    #cluster_means[c] = ( cluster_means[c] * cluster_members[c] + coord) / (cluster_members[c]+1)
                    cluster_members[c] += 1
                    cluster_values[c] += min_values[i]
                    break
                else:
                    clusters.append([i])
                    cluster_means.append(coord)
                    cluster_members.append(1)
                    cluster_values.append(max_values[i])
                    break
        
        sorted_values = list(argsort(cluster_values))
        sorted_values.reverse()
        winner = sorted_values[0]
        min_coords = cluster_means[winner]



        #print "N clusters: ", len(clusters)
        #print "Cluster means: ", cluster_means

        
    #    min_coords = array([sum(min_values * min_coordinates_x), sum(min_values*min_coordinates_y)]) 
#        max_coords = array([sum(max_values * max_coordinates_x), sum(max_values*max_coordinates_y)])
        
        # remove outliers
 #       max_values_final = max_values
    #    min_values_final = min_values
        
     #   factor = outlier_cutoff
  #      max_distances = sqrt( (max_coordinates_x - max_coords[0])**2 + (max_coordinates_y - max_coords[1])**2)
  #      max_values_final[ where(max_distances > factor * std(max_distances))] = 0.
  #      if(prod(max_values_final) == 0.):
  #          max_values_final = max_values

      #  min_distances = sqrt( (min_coordinates_x - min_coords[0])**2 + (min_coordinates_y - min_coords[1])**2)
      #  min_values_final[ where(min_distances > factor * std(min_distances))] = 0
      #  if(prod(min_values_final) == 0.):
      #      min_values_final = min_values


        # recompute
  #      max_values_final = max_values_final / sum(max_values)
        #min_values_final = min_values_final / sum(min_values_final)
        
        #min_coords = array([sum(min_values_final * min_coordinates_x), sum(min_values_final*min_coordinates_y)]) 
  #      max_coords = array([sum(max_values_final * max_coordinates_x), sum(max_values_final*max_coordinates_y)])
        
        
        
        return (min_coords, max_coords) 
                
    
    def _find_image_minmax(self, image):
        code = """
			Py_BEGIN_ALLOW_THREADS
			#define TYPE	%s
			
			int rows = Nimage[0];
			int cols = Nimage[1];
			
			double themax = -999999;
			double themin = 999999;
			
			for(int r = 0; r < rows; r++){
				for(int c = 0; c < cols; c++){
					
					double *pixel_ptr = (TYPE *)((char *)image_array->data + r * image_array->strides[0] + c * image_array->strides[1]);
					
					
					if(*pixel_ptr > themax){
						
						themax = *pixel_ptr;
						coordinates[2] = (double)r;
						coordinates[3] = (double)c;
					}
					
					if(*pixel_ptr < themin){
						
						themin = *pixel_ptr;
						coordinates[0] = (double)r;
						coordinates[1] = (double)c;
					}
				}
			}
		
			Py_END_ALLOW_THREADS
		""" % self.c_typestring
		
        coordinates = array([0.,0., 0., 0.])
        themax = 0.
        themin = 0.
        
        inline(code, ['image', 'coordinates'])
        
        #print coordinates
        
        return (coordinates[0:2], coordinates[2:4])


if __name__ == "__main__":
    import pylab
    import numpy
    import PIL.Image
    import time
    
    pil_im = pil_im = PIL.Image.open("/Users/davidcox/Development/svn.coxlab.org/eyetracking/code/EyeTrackerStageDriver/example_eyes/RatEye_snap20_zoom.jpg")
    im = asarray(pil_im).astype(numpy.float64)
    
    noplot = 1
    
    f = FastRadialFeatureFinder()
    trials = 50
    
    if(0):
        tic = time.time()
        for i in range(0,trials):
            test = f.analyze_image(im, filter='fft')
    
        print 'FFT: ', (time.time() - tic)/trials

        pylab.figure()
        pylab.imshow(test['transform'])
        pylab.title('FFT')
        
    if(1):
        
        f.reuse_storage = 0
        f.use_sse3 = 0
        f.filter = 'sepfir'
        tic = time.time()
        for i in range(0,trials):
            f.analyze_image(im, filter='sepfir')
            test = f.get_result()
        seconds_per_frame = (time.time() - tic)/trials
        print 'Sep FIR: ', seconds_per_frame
        print '\t ', 1. / seconds_per_frame, ' FPS' 

        if(not noplot):
            pylab.figure()
            pylab.imshow(test['transform'])
            
            pylab.figure()
            #pylab.imshow(im, cmap=pylab.cm.gray)
            pylab.imshow(test['im_array'], cmap=pylab.cm.gray)
            pylab.hold('on')
            cr = test['cr_position']
            pupil = test['pupil_position']
            pylab.plot([cr[1]], [cr[0]], 'r+')
            pylab.plot([pupil[1]], [pupil[0]], 'b+')
            pylab.title('Sep FIR')
        
    if(0):
        tic = time.time()
        for i in range(0,trials):
            test = f.analyze_image(im, filter='spline')
        print 'SPLINE: ', (time.time() - tic)/trials
        
        pylab.figure()
        pylab.imshow(test['transform'])
        pylab.title('SPLINE')

    if(0):
        tic = time.time()
        for i in range(0,trials):
            test = f.analyze_image(im)
        print 'Convolve2d: ', (time.time() - tic)/trials
        
        pylab.figure()
        pylab.imshow(test['transform'])
        pylab.title('Convolve2d')
	
    if(0):
        f.reuse_storage = 1	
        tic = time.time()
        def sepfir_multithread_test(i, f, im):	
            test = f.analyze_image(im, filter='sepfir')
        foreach(lambda t: sepfir_multithread_test(t,f, im), range(0,trials), 3)
        print 'Sep FIR (multithreaded): ', (time.time() - tic)/trials	
	
    pylab.show()
	
