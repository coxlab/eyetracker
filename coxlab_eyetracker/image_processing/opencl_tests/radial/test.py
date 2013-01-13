#!/usr/bin/env python

import sys
import time

import pylab
import numpy as np

# try to import the 'old' image_processing module to compare
# the opencl results against
try:
    from coxlab_eyetracker import image_processing
except ImportError:
    sys.path.append('eyedata')
    import image_processing

from coxlab_eyetracker.image_processing.CythonBackend import CythonBackend

import radial2 as radial

nwarmups = 20
nruns = 200

#radii = pylab.arange(2, 20, 1)
radii = pylab.array([2,  4,  7,  9, 12, 15])
#radii = pylab.array([9, ])
alpha = 10

fn = 'test.png'
if len(sys.argv) > 1:
    fn = sys.argv[1]
im = pylab.imread(fn)[:, :, 0].astype(float)

biggerify = False

if biggerify:
    im = np.concatenate((im, im, im, im), 1)
#im = np.random.rand(640, 480)

print 'im shape'
print im.shape

#vb = image_processing.VanillaBackend()
#cb = radial.OpenCLBackend()
#m, x, y = b.sobel3x3(im.astype(float))
#cl = radial.setup(im)
true_backend = 'Woven'
backends = {
        # 'Vanilla': image_processing.VanillaBackend(),
        'Cython': CythonBackend(),
        'Woven': image_processing.WovenBackend(),
        'OpenCL': radial.OpenCLBackend()
        }

results = {}
times = {}
for (n, b) in backends.iteritems():
    # call once to 'cache' any source that is compiled
    for w in range(0, nwarmups):
        r = b.fast_radial_transform(im, radii, alpha)
    t0 = time.time()
    for w in range(0, nruns):
        r = b.find_minmax(b.fast_radial_transform(im, radii, alpha))
    t1 = time.time()
    results[n] = r
    times[n] = (t1 - t0) / nruns

truth = results[true_backend]
print "Truth:", truth
for (n, r) in results.iteritems():
    print "%07s [%.6f seconds]" % (n, times[n])

    if (not np.allclose(r[0], truth[0]) or
       not np.allclose(r[1], truth[1])):
    # if (abs(r.max() - truth.max()) > 0.0001) or \
    #     (abs(r.min() - truth.min()) > 0.0001):
        print "===============FAIL=============="
        print "Result:", r
    else:
        print "          ++++ Pass ++++"

print
s = max(times, key=lambda n: times[n])
print "Slowest: %s [%.6f seconds]" % (s, times[s])
f = min(times, key=lambda n: times[n])
print "Fastest: %s [%.6f seconds]" % (f, times[f])
