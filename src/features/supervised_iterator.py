import numpy as np
from src.features.hdf5_iterator import Hdf5Iterator
from src.features.mixer import FeatureMixer
from src.features.wav_iterator import batcher


class SupervisedIterator(Hdf5Iterator):
    
    def __init__(self, *args, **kwargs):
        super(SupervisedIterator,self).__init__(*args, **kwargs)
        
        self.labels = [ flac.split('/')[0] for flac in self.h5_groups ]
        self.labels.sort()
        self.labeldict = {}
        for i,l in enumerate(self.labels):
            self.labeldict[ l ] = i
    
    def make_random_embedding( self, hidden_units, num_labels=None ):
        ''' 
        Create a matrix that is of size hidden_units (the embedding
        size) x number_labels
        '''
        if num_labels:
            return np.random.randn( hidden_units, num_labels )
        else:
            return np.random.randn( hidden_units, len(self.labels) )
    
    def label2dict( self, lookup ):
        
        lookup = lookup.split('/')[0]
        if type(lookup)==list:
            return [ self.labeldict[l] for l in lookup ]
        return self.labeldict[lookup]
    
class SupervisedMixer(FeatureMixer):
    
    def __init__(self, *args, **kwargs):
        '''
        Currently only get_batch works; actual iteration does not.
        '''
        
        super(SupervisedMixer, self).__init__(*args, **kwargs, Iterator=SupervisedIterator)
        
        # Aggregate all the labels
        all_labels = set([])
        for iters in self.iterators:
            all_labels |= set(iters.labels)
        self.all_labels = list(all_labels)
        self.all_labels.sort()
        
        # Make a dictionary
        self.labeldict = {}
        for i,l in enumerate(self.all_labels):
            self.labeldict[ l ] = i
        
        
    def label2dict( self, lookup ):
        
        if type(lookup)==list:
            return [ self.labeldict[l.split('/')[0]] for l in lookup] 
        return self.labeldict[lookup]
        
    def make_random_embedding( self, hidden_units, num_labels=None ):
        ''' 
        Create a matrix that is of size hidden_units (the embedding
        size) x number_labels
        '''
        if num_labels:
            return np.random.randn( hidden_units, num_labels )
        else:
            return np.random.randn( hidden_units, len(self.all_labels) )
        
    def get_batch(self, num_samples, out_TF = -1, Y = None):

        '''
        Inputs:
            out_TF - the indices of which time bins (all freqs) to use. 
                     Default = None.
                     -1 = last index of the spectrum
            mask -  Current mask for data purposes. If not set (it should be!), 
                    will initialize to zeros
            Y - output labels of size NumSpkrs x BatchSize x TimeFreq, where Y 
                is +1 if it's the max, -1 if not, and 0 if not referenced
        
        Returns:
            mixed batch
            Y - output labels (+/- 1 or 0)
            I - indices
        '''

        batch = super(SupervisedMixer, self).get_batch( num_samples )
        if Y == None:
            data_shape = batch[0].shape
            if type(out_TF)==int:
                TF = data_shape[-1]
            elif type(out_TF)==np.ndarray:
                TF = len(out_TF)*data_shape[-1]
            else: # type(out_TF) == None    
                TF = np.prod( data_shape[-2:] )
            Y = np.zeros((data_shape[0],len(batch)-1, TF))

        I = []
        for i, X in enumerate(batch[1:]):
            if type(out_TF) == int or type(out_TF) == np.ndarray:
                Xsub = abs( X[1][:, out_TF] )
                Y[:,i,:] = 1
                for Xcomp in batch[1:]:
                    Y[:,i,:] *= abs(Xsub) >= abs(Xcomp[1][:, out_TF])
            else:
                Xsub = abs( X[1] )
            I += [self.label2dict(X[0])]

        I = np.array(I).T

        return batch[0], Y, I
        

