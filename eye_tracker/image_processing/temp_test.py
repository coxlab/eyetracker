from numpy import *

def _get_image_values_interp(im, x,y):
    print "x = ", x
    vals = zeros(x.shape)
    floor_x = floor(x).astype(int)
    floor_y = floor(y).astype(int)
    ceil_x = ceil(x).astype(int)
    ceil_y = ceil(y).astype(int)
    #print 'x= ', x
    #print 'floor_x = ', floor_x
    x_frac = 1 - (x - floor_x)
    y_frac = 1 - (y - floor_y)
    print "x_frac: ", x_frac
    
    for i in range(0,x.shape[0]):
        for j in range(0, x.shape[1]):
            a = im[floor_x[i,j], floor_y[i,j]]
            b = im[ceil_x[i,j], floor_y[i,j]]
            c = im[floor_x[i,j], ceil_y[i,j]]
            d = im[ceil_x[i,j], ceil_y[i,j]]
            #print x_frac[i,j]
            #print a
            val = 0.25 * ((x_frac[i,j] + y_frac[i,j]) * a + ((1-x_frac[i,j]) + y_frac[i,j]) * b + \
                      (x_frac[i,j] + (1 - y_frac[i,j])) * c + ((1-x_frac[i,j])+(1-y_frac[i,j]))*d)
            #print val
            vals[i,j] = val
    return vals


im = array([[0, 0.5], [0.5, 1]])

vals = _get_image_values_interp(im, array([[0.5, 1]]), array([[0.5,1]]))
print vals
