#
#  PipelinedFeatureFinder.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 9/3/08.
#  Copyright (c) 2008 The Rowland Institute at Harvard. All rights reserved.
#

from multiprocessing.managers import SyncManager

from FrugalCompositeEyeFeatureFinder import *
from FastRadialFeatureFinder import *
from SubpixelStarburstEyeFeatureFinder import *

import time
import Queue
import threading
import cPickle as pickle


class PipelinedWorker:

    def __init__(self, ff, input_queue, output_queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.ff = ff
        self._stop = threading.Event()

    def stop(self):
        #print "Worker told to stop: %s" % self
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def start(self):
        while(not self.stopped()):
            #print "%s.stopped = %s" % (self, self.stopped())
            try:
                input = self.input_queue.get(timeout=1.)
            except Queue.Empty:
                continue

            if input is not None:
                (im, guess) = input
            else:
                im = None
                guess = None

            # else an image
            self.ff.analyze_image(im, guess)
            features = self.ff.get_result()

            features["transform"] = None
            features["im_array"] = None

            # pickle the structure manually, because Queue doesn't seem to do the
            # job correctly
            self.output_queue.put(pickle.dumps(features))
            self.input_queue.task_done()


def worker_thread(worker):
    worker.start()


class PipelinedWorkerProcessManager(SyncManager):

    #CompositeEyeFeatureFinder_ = CreatorMethod(CompositeEyeFeatureFinder)
    #FastRadialFeatureFinder_ = CreatorMethod(FastRadialFeatureFinder)
    #StarBurstEyeFeatureFinder_ = CreatorMethod(SubpixelStarburstEyeFeatureFinder)
    #PipelinedWorker_ = CreatorMethod(PipelinedWorker)

    def __init__(self, queue_size=None):
        #print "instantiating process manager"
        SyncManager.__init__(self)

        self.start()

        self.ff = None
        self.input_queue = self.Queue(queue_size)
        self.output_queue = self.Queue(queue_size)
        self.worker = None

    def set_main_feature_finder(self, ff):
        self.ff = ff

    def start_worker_loop(self):
        self.worker = self.PipelinedWorker(self.ff, self.input_queue, self.output_queue)
        self.worker_thread = threading.Thread(target=worker_thread, args=[self.worker])
        self.worker_thread.start()
    
    def stop(self):
        #print "Stopping worker: %s" % self
        self.worker.stop()
    
    def join_worker(self):
        # wait for join
        #print "%s.is_alive = %s" % (self.worker_thread, self.worker_thread.is_alive())
        self.worker_thread.join(1.0)
        #print "%s.is_alive = %s" % (self.worker_thread, self.worker_thread.is_alive())


def worker_loop(ff, image_queue, output_queue, id=-1):
    while(1):
        input = image_queue.get()

        if input is not None:
            (im, guess) = input
        else:
            im = None
            guess = None

        # else an image
        ff.analyze_image(im, guess)
        features = ff.get_result()

        # take these out because they are a bit big
        features["transform"] = None
        features["im_array"] = None

        # pickle the structure manually, because Queue doesn't seem to do the
        # job correctly
        output_queue.put(pickle.dumps(features))


PipelinedWorkerProcessManager.register('FrugalCompositeEyeFeatureFinder', FrugalCompositeEyeFeatureFinder)
PipelinedWorkerProcessManager.register('FastRadialFeatureFinder', FastRadialFeatureFinder, exposed=('get_param', 'set_param'))
PipelinedWorkerProcessManager.register('StarBurstEyeFeatureFinder', SubpixelStarburstEyeFeatureFinder, exposed=('get_param', 'set_param'))
PipelinedWorkerProcessManager.register('PipelinedWorker', PipelinedWorker)


class PipelinedFeatureFinder:

    def __init__(self, nworkers):

        self.workers = []

        queue_length = 3

        self.current_input_worker = 0
        self.current_output_worker = 0
        self.input_queues = []
        self.output_queues = []
        self.image_queue = Queue.Queue()

        self.last_im = None

        for w in range(0, nworkers):

            worker = PipelinedWorkerProcessManager(queue_length)
            self.workers.append(worker)
            self.input_queues.append(worker.input_queue)
            self.output_queues.append(worker.output_queue)

        self.grace = nworkers + 1
        #self.grace = 10

    def start(self):
        for worker in self.workers:
            worker.start_worker_loop()

    #@clockit
    def analyze_image(self, image, guess=None):
        if(self.current_input_worker >= len(self.workers)):
            self.current_input_worker = 0

        self.input_queues[self.current_input_worker].put((image, guess))
        self.current_input_worker += 1

        self.image_queue.put(image)
        #self.last_im = image

    def get_result(self):

        if(self.grace > 0):
            self.grace -= 1
            return None

        if(self.current_output_worker >= len(self.workers)):
            self.current_output_worker = 0

        # unpickle manually, because Queue doesn't seem to do it right
        result = pickle.loads(self.output_queues[self.current_output_worker].get())
        result["im_array"] = self.image_queue.get()
        self.output_queues[self.current_output_worker].task_done()

        self.current_output_worker += 1
        return result

    def stop_threads(self):
        for worker in self.workers:
            worker.stop()
        time.sleep(len(self.workers) + 1)
        #for iq in self.input_queues:
        #    iq.join()
        #for oq in self.output_queues:
        #    oq.join()
        for worker in self.workers:
            worker.join_worker()


    def __del__(self):
        self.stop_threads()


