#
#  PipelinedFeatureFinder.py
#  EyeTrackerStageDriver
#
#  Created by David Cox on 9/3/08.
#  Copyright (c) 2008 The Rowland Institute at Harvard. All rights reserved.
#

from multiprocessing.managers import SyncManager, BaseProxy

from FrugalCompositeEyeFeatureFinder import *
from FastRadialFeatureFinder import *
from SubpixelStarburstEyeFeatureFinder import *

import processing
import Queue
import threading
import cPickle as pickle
import copy


class PipelinedWorker:

    def __init__(self, ff, input_queue, output_queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.ff = ff
    
    def start(self):
        while(1):
            input = self.input_queue.get()
            
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

def worker_thread(worker):
    worker.start()

class PipelinedWorkerProcessManager(SyncManager):

    #CompositeEyeFeatureFinder_ = CreatorMethod(CompositeEyeFeatureFinder)
    #FastRadialFeatureFinder_ = CreatorMethod(FastRadialFeatureFinder)
    #StarBurstEyeFeatureFinder_ = CreatorMethod(SubpixelStarburstEyeFeatureFinder)
    #PipelinedWorker_ = CreatorMethod(PipelinedWorker)
    
    def __init__(self, queue_size = None):
        print "instantiating process manager"
        SyncManager.__init__(self)
        self.start()
        self.ff = None
        self.input_queue = self.Queue(queue_size)
        self.output_queue = self.Queue(queue_size)
        self.worker = None
        
        self.register('FrugalCompositeEyeFeatureFinder', FrugalCompositeEyeFeatureFinder)
        self.register('FastRadialFeatureFinder', FastRadialFeatureFinder)
        self.register('SubpixelStarburstEyeFeatureFinder', SubpixelStarburstEyeFeatureFinder)
        self.register('PipelinedWorker', PipelinedWorker)
    
    def set_main_feature_finder(self, ff):
        self.ff = ff
    
    def start_worker_loop(self):
        self.worker = self.PipelinedWorker_(self.ff, self.input_queue, self.output_queue)
        self.worker_thread = threading.Thread(target=worker_thread, args=[self.worker])
        self.worker_thread.start()
        

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
            
            worker = PipelinedWorkerProcessManager(queue_length);
            self.workers.append(worker)
            self.input_queues.append(worker.input_queue)
            self.output_queues.append(worker.output_queue)
            
        self.grace =  nworkers+1
        #self.grace = 10
        
    def start(self):
        for worker in self.workers:
            worker.start_worker_loop()
    
    @clockit
    def analyze_image(self, image, guess = None):
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

        self.current_output_worker += 1
        return result
        
        
        
        