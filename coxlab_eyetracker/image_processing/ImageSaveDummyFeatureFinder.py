import logging
from EyeFeatureFinder import EyeFeatureFinder
import cPickle as pkl
import os.path
import os
import time


class ImageSaveDummyFeatureFinder(EyeFeatureFinder):

    def __init__(self, real_ff, path):
        self.real_ff = real_ff
        self.session_key = \
            time.strftime('%Y-%m-%d-%H%M-%S',
                          time.localtime(time.time()))
        #self.n_frames = 0
        #self.frames_per_dir = 1000

        self.base_path = os.path.expanduser(path)
        self.base_path += '/' + self.session_key

        os.makedirs(self.base_path)

        #self.current_path = None
        self.current_path = self.base_path
        self.save = False

    def analyze_image(self, image, guess=None, **kwargs):
        if self.save:
            if guess is not None and 'timestamp' in guess:
                self.save_image(image, guess['timestamp'])
            else:
                logging.error('Cannot save to disk without timestamp set')

        return self.real_ff.analyze_image(image, guess, **kwargs)

    def get_result(self):
        return self.real_ff.get_result()

    def stop_threads(self):
        if hasattr(self.real_ff, 'stop_threads'):
            self.real_ff.stop_threads()

    def save_image(self, image, timestamp):

        #if (self.n_frames % self.frames_per_dir == 0 or
        #        self.current_path is None):
        #
        #    # make a new directory
        #    self.current_path = (self.base_path + '/' +
        #                         '%.10d' % (self.n_frames /
        #                                    self.frames_per_dir))
        #    os.mkdir(self.current_path)

        fname = '%s/%i.pkl' % (self.current_path,
                               int(timestamp * 1000.))

        with open(fname, 'w') as f:
            #self.n_frames += 1
            pkl.dump(image.astype('>u1'), f)
