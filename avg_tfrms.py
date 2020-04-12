import numpy as np
import pandas as pd

from scipy.signal import stft
from scipy.signal import lombscargle as lssa

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import SGDClassifier

import sleep_an_tools as st

from typing import Union

def get_accel(subject : str, non_neg = True):
    # Import the acceleration data
    accel = pd.read_csv("data/motion/{}_acceleration.txt".format(subject), sep=' ', names=['time', 'x', 'y', 'z'])
    if non_neg:
        accel = accel[accel['time'] >= 0]
    accel.reset_index(drop=True, inplace=True)
    
    # Calculate magnitude of the (x,y,z) accelerations
    accel['mag'] = st.mag(accel[['x', 'y', 'z']])
    # then calculate numerical derivative of the acceleration magnitudes.
    tstat, t0, dmag = st.vder(accel[['time', 'mag']])

    dmag_df = pd.DataFrame({'time' : t0, 'dmag' : dmag})

    return (accel, dmag_df)

# Compute Lomb-Scargle periodogram in 30 second chunks, with 10 second overlap.
# First time period is 20 seconds long.
def lssa_chunks(time : np.ndarray, y : np.ndarray, max_freq = 4*np.pi/0.5): 
    

    fr = np.linspace(1e-4, max_freq + 1e-4, 500)

    t_min = time.min()
    t_max = time.max()

    masks = [(t_min <= time) & (time <= t_min + 20)] + [(t_min + n*20 - 10 <= time) & (time <= t_min + (n+1)*20) for n in range(1, int((t_max - t_min)/20)-1)]

    times = [time[mask] for mask in masks]
    ys = [y[mask] for mask in masks]

    lssas = [lssa(t, y, fr) for t, y in zip(times, ys)]

    return (fr, lssas)

# Computes the time-averaged short-term Fourier transform over 30 second segments.
# Returns a list of lists, where stft_d[i] is the set of averaged transforms with  PSG label i. 
# --> Current caveat: labels=[0,1], with 0 ~~> awake; 1 ~~> asleep
# Building classifier based on this seems to suffer somewhat from rare class 0.
def make_avg_tfrms(subject : str, dB = True, non_neg = True, labels=[0,1]):
    # Import the acceleration data
    accel = pd.read_csv("data/motion/{}_acceleration.txt".format(subject), sep=' ', names=['time', 'x', 'y', 'z'])
    if non_neg:
        accel = accel[accel['time'] >= 0]
    accel.reset_index(drop=True, inplace=True)
    
    # Calculate magnitude of the (x,y,z) accelerations
    accel['mag'] = st.mag(accel[['x', 'y', 'z']])
    # then calculate numerical derivative of the acceleration magnitudes.
    tstat, t0, dmag = st.vder(accel[['time', 'mag']])
    
    # Import the PSG labels
    psg = pd.read_csv("data/labels/{}_labeled_sleep.txt".format(subject), sep=' ', names=['time', 'label'])

    stages = [psg[psg['label'] == 0]['time'], psg[psg['label'] > 0]['time']]
    
    dmag_segs = [[dmag[(t0 >= t) & (t0 <= t+30)] for t in stage] for stage in stages]
    
    stft_d = [[stft(dm, nperseg=128)[-1] for dm in dmag_segs[j] if len(dm) >= 128] for j in labels]
    
    if dB:
        stft_d = [[10*np.log10(abs(s)) for s in stft_d[j]] for j in labels]
    else:
        stft_d = [[abs(s) for s in stft_d[j]] for j in labels]
        
    stft_d = [[np.mean(s, axis=1) for s in stft_d[j]] for j in labels]
        
    return stft_d

# dmag_df should have columns named 'time' and 'dmag'.
# This is the case when dmag_df comes from get_accel. 
def tfrm(dmag_df : pd.DataFrame, tstart : np.float64, tstop : np.float64, dB = True, mean = False):
    dmag_seg = dmag_df[(dmag_df['time'] >= tstart) & (dmag_df['time'] <= tstop)]['dmag'].to_numpy()
    
    stft_d = stft(dmag_seg, nperseg=128)[-1]
    
    if dB:
        stft_d = lb.amplitude_to_db(abs(stft_d))
    else:
        stft_d = abs(stft_d)
        
    if mean:
        stft_d = np.mean(stft_d, axis=1)
        stft_d.reshape(1, -1) 

    return stft_d
