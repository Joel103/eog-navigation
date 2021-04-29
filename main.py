from pylsl import StreamInlet, resolve_byprop
import numpy as np
import utils
import math
import json
import sys

""" User input error handling """

option_1 = (len(sys.argv) == 2) and sys.argv[1] == "run"
option_2 = (len(sys.argv) == 3) and sys.argv[1] == "calibrate" and sys.argv[2] in ["resting", "right", "left", "upward",
                                                                                   "downward"]
if not (option_1 or option_2):
    print("Pass either \"run\" as argument or \"calibrate <type>\" (<type> is either \"resting\", \"right\", \"left\","
          " \"upward\" or \"downward\")")
    exit(1)

""" Load dictionary from config """

parameters = json.load(open("config.json"))
'''
config.json contents:

"number of recording phases": number of times data will be recorded in recording phases during calibration
"window size": number of samples that a window is composed of
"step size": distance in terms of number of samples that the window will slide further to compose the next window to be 
             analyzed
'''

""" Connect to the EEG stream """

print('Looking for EEG stream...')
streams = resolve_byprop('type', 'EEG', timeout=2)

if len(streams) == 0:
    raise RuntimeError('Cannot find EEG stream.')

# Construct a stream inlet using the EEG stream
print("Streaming started")
inlet = StreamInlet(streams[0])

""" Start running or calibrating the application """

if sys.argv[1] == "calibrate":
    # prepare calibration
    calibrator = utils.Calibrator(parameters["number of recording phases"])

    # determine how many steps to take when sliding the streaming window
    num_steps = 1

elif sys.argv[1] == "run":
    file = open(r"calibration.txt", "r")
    # check if calibration is completed
    if sum(1 for _ in file) < 8:
        file.close()
        print("You first need to perform all calibration steps")
        exit(1)

    # go back to beginning of file
    file.seek(0)

    # get thresholds for each direction and construct the Analyzer

    thresholds = list(map(lambda x: x.split(":"), [next(file) for i in range(0, 8)]))
    file.close()

    right = float(thresholds[4][1][:-2])
    left = float(thresholds[5][1][:-2])
    upward = float(thresholds[6][1][:-2])
    downward = float(thresholds[7][1][:-2])

    analyzer = utils.Analyzer(right, left, upward, downward)

    # determine how many steps to take initially when sliding the streaming window
    num_steps = 10

# initialize array
prev_window = np.zeros((parameters['window size'], 4))

while True:

    # determine how many samples to pull next
    max_samples = math.floor(num_steps * parameters["window size"] * parameters['step size'])

    # pull samples
    new_samples, _ = inlet.pull_chunk(timeout=4, max_samples=max_samples)

    # append pulled samples to part of the previously analyzed samples
    window = utils.update_window(prev_window, new_samples)

    # save current window for next iteration
    prev_window = window

    # preprocess window
    window = utils.preprocessing(window)

    # extract features needed for classification
    D = utils.compute_D(window)
    DD = utils.compute_DD(window)

    if sys.argv[1] == "run":

        # detect eye movements and set num_steps to determine when to resume window analysis
        num_steps = analyzer.classify_window(D, DD) + 1

    elif sys.argv[1] == "calibrate":

        if sys.argv[2] == "resting":

            # determine maximum and minimum values for D and DD during resting phases of the eyes
            if calibrator.calibrate_resting(D, DD) == "finished":
                exit(0)

        elif sys.argv[2] == "right":

            # determine threshold for eye movement to the right
            if calibrator.calibrate_direction(D, DD, "right") == "finished":
                exit(0)

        elif sys.argv[2] == "left":

            # determine threshold for eye movement to the left
            if calibrator.calibrate_direction(D, DD, "left") == "finished":
                exit(0)

        elif sys.argv[2] == "upward":

            # determine threshold for upward eye movement
            if calibrator.calibrate_direction(D, DD, "upward") == "finished":
                exit(0)

        elif sys.argv[2] == "downward":

            # determine threshold for downward eye movement
            if calibrator.calibrate_direction(D, DD, "downward") == "finished":
                exit(0)
