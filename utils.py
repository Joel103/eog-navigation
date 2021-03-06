import numpy as np
import pyautogui
import os

# define audio feedback
duration_1 = 0.1  # seconds
frequency_1 = 440  # hertz
duration_2 = 0.6  # seconds
frequency_2 = 640  # hertz
frequency_3 = 800  # hertz


class Analyzer:
    """
    This class is used to analyze the generated windows of the EEG stream.

    Attributes:
        navigation (bool): is set to True when navigation mode is currently active
        right (float): threshold used to detect right eye movements
        left (float): threshold used to detect left eye movements
        upward (float): threshold used to detect upward eye movements
        downward (float): threshold used to detect downward eye movements
        u_dict (dict): is used to identify whether an upward eye movement or eye closure is performed
        d_dict (dict): is used to identify whether eyes are maintained at a downward position
    """

    def __init__(self, right, left, upward, downward):

        self.navigation = False
        self.right = right
        self.left = left
        self.upward = upward
        self.downward = downward
        self.u_dict = {"upward signal received": False, "timer": 0}
        self.d_dict = {"downward signal received": False, "timer": 0, "potential glance": False, "timer2": 0}

    def classify_window(self, D, DD):
        """
        Classifies a window using its values for D and DD.

        If navigation mode is currently turned on:

            -It is evaluated whether an upward-/closing eye movement signal was detected when analyzing the previous
            window (the EOG signals for these two events are more similar than for other events). If so, analyze_upward()
            will be executed to evaluate whether the user maintains the eyes closed or only glanced upwards.

            -If not, then it is evaluated whether the user performed a right- (D > self.right), left- (D <  self.left),
            downward- (DD < self.downward), or upward- /closing eye movement (DD > self.upward). If right-,left- or
            downward eye movement is detected, the operating system will perform the respective command. If
            upward- /closing eye movement was detected, self.u_dict["upward signal received"] will be set to True and
            self.u_dict["timer"] to 8.

        If navigation mode is turned off:

            -It is evaluated whether a downward eye movement was detected when analyzing the previous window. If so,
            analyze_downward() will be executed to evaluate whether the user maintains the eyes in downward position
            or if the user merely glanced downwards.

            -If not, it is evaluated whether the user performes any extreme eye movements to the right (D > self.right),
            left (D <  self.left) or in upward direction (DD > self.upward). In this case a few windows will be dropped
            before classify_window() will be executed again. This is done to prevent noise from interfering with the next
            window to be analyzed.

            -If not, it is evaluated whether the user performed a downward eye movement (DD < self.downward). If so,
            self.d_dict["downward signal received"] is set to True, self.d_dict["potential glance"] is set to True,
            self.d_dict["timer"] is set to 8, and self.d_dict["timer2"] is set to 50.

        Arguments:
            D (float): The region under the graph as computed by compute_D()
            DD (float): The region under the graph as computed by compute_DD()

        Returns:
            drop_windows (int): number of windows to drop, until the next window will be analyzed. For instance if
                                drop_window = 20, then the following 20 windows will be dropped and analysis resumes with
                                the 21st window arriving. This is done to prevent noise, generated by eye movements in
                                the current window, from interfering with the next window to be analyzed.
        """

        drop_windows = 0

        # check if navigation mode is True
        if self.navigation:

            # check if an upward signal was received in the previous window
            if self.u_dict["upward signal received"]:
                drop_windows = self.analyze_upward(DD)

            # check if right eye movement is performed
            elif D > self.right:
                print("right")
                # press "right" key
                pyautogui.press("right")
                # play beep
                os.system('play -nq -t alsa synth {} sine {}'.format(duration_2, frequency_1))
                drop_windows = 20

            # check if left eye movement is performed
            elif D < self.left:
                print("left")
                pyautogui.press("left")
                os.system('play -nq -t alsa synth {} sine {}'.format(duration_2, frequency_1))
                drop_windows = 20

            # check if downward eye movement is performed
            elif DD < self.downward:
                print("down")
                pyautogui.press("down")
                os.system('play -nq -t alsa synth {} sine {}'.format(duration_2, frequency_1))
                drop_windows = 20

            # check if upward/closing eye movement is performed
            elif DD > self.upward:
                self.u_dict["upward signal received"] = True
                self.u_dict["timer"] = 8
                drop_windows = 12

        # navigation mode is False
        else:
            # check if a downward signal was received in the previous window
            if self.d_dict["downward signal received"]:
                drop_windows = self.analyze_downward(DD)

            # check if any extreme eye movements to the right, left or upward are performed
            elif D > self.right or D < self.left or DD > self.upward:
                drop_windows = 40

            # check if a downward eye movement is performed
            elif DD < self.downward:
                self.d_dict["downward signal received"] = True
                self.d_dict["potential glance"] = True
                self.d_dict["timer"] = 8
                self.d_dict["timer2"] = 30
                drop_windows = 12

        return drop_windows

    def analyze_upward(self, DD):
        """
        During execution of classify_window(), this function is used to identify whether the user only glanced upward
        when an upward signal was detected in navigation mode, or if the user keeps the eyes closed instead.

        As long as self.u_dict["timer"] has not elapsed, it is evaluated whether DD > self.upward * 0.5 (DD will exceed
        this threshold when the user only glances upwards). If DD exceeds this threshold, the operating system will
        perform the "up" command and self.u_dict["upward signal received"] will be set to False again.

        If DD does not exceed the threshold before self.u_dict["timer"] elapses, the user maintains the eyes closed and
        the operating system performs the "enter" command. Navigation mode is then turned off.

        Arguments:
            DD (float): The region under the graph as computed by compute_DD()

        Returns:
            drop_windows (int): number of windows to drop, until the next window will be analyzed. For instance if
                                drop_window = 20, then the following 20 windows will be dropped and analysis resumes with
                                the 21st window arriving. This is done to prevent noise, generated by eye movements in
                                the current window, from interfering with the next window to be analyzed.
        """
        drop_windows = 0

        # check if user glanced upward
        if DD > self.upward * 0.5:
            pyautogui.press("up")
            print("up")
            os.system('play -nq -t alsa synth {} sine {}'.format(duration_2, frequency_1))
            self.u_dict["upward signal received"] = False
            drop_windows = 20

        # check if timer has elapsed
        elif self.u_dict["timer"] > 0:
            self.u_dict["timer"] -= 1

        else:
            # user maintains eyes closed

            pyautogui.press("enter")
            print("enter")
            os.system('play -nq -t alsa synth {} sine {}'.format(duration_2, frequency_1))

            # switch state of navigation mode
            self.navigation = False
            print("viewing mode is now active")

            self.u_dict["upward signal received"] = False
            drop_windows = 20

        return drop_windows

    def analyze_downward(self, DD):
        """
        During execution of classify_window(), this function is used to identify whether the user maintains the eyes
        in downward position, after a downward signal was detected in viewing mode (i.e. when self.navigation is False).

        As long as self.d_dict["timer"] has not elapsed, it is evaluated whether DD < self.downward * 0.5 (DD will exceed
        this threshold if the user only glances downwards). If DD exceeds this threshold,
        self.d_dict["downward signal received"] will be set to False again

        If DD does not exceed the threshold before self.u_dict["timer"] elapses, the user maintains the eyes in downward
        position. In this case, it is evaluated whether the user raises the eyes again (DD > self.upward) before
        self.d_dict["timer2"] elapses. If DD > self.upward does not evaluate to True before the timer elapses, the user
        maintained the eyes in downward position long enough to activate navigation mode again. self.navigation will
        subsequently be set to True again and self.d_dict["downward signal received"] to False.

        Arguments:
            DD (float): The region under the graph as computed by compute_DD()

        Returns:
            drop_windows (int): number of windows to drop, until the next window will be analyzed. For instance if
                                drop_windows = 20, then the following 20 windows will be dropped and analysis resumes
                                with the 21st window arriving. This is done to prevent noise, generated by eye movements
                                in the current window, from interfering with the next window to be analyzed.
        """
        drop_windows = 0

        if self.d_dict["potential glance"]:
            # evaluate whether user merely glanced downward

            # check if user merely glanced downward
            if DD < self.downward * 0.5:
                self.d_dict["downward signal received"] = False
                drop_windows = 40

            # check if timer has elapsed
            elif self.d_dict["timer"] > 0:
                self.d_dict["timer"] -= 1

            # if timer has elapsed, set self.d_dict["potential glance"] to False
            elif self.d_dict["timer"] == 0:
                self.d_dict["potential glance"] = False

        if not self.d_dict["potential glance"]:
            # user maintains eyes in downward position

            # play a beep every 2nd time timer2 is reduced
            if self.d_dict["timer2"] % 2 == 0:
                os.system('play -nq -t alsa synth {} sine {}'.format(duration_1, frequency_2))

            # evaluate whether user looked upwards again
            if DD > self.upward:
                self.d_dict["downward signal received"] = False
                drop_windows = 40

            # check if timer has elapsed
            elif self.d_dict["timer2"] > 0:
                self.d_dict["timer2"] -= 1

            else:
                # user maintained eyes in downward position long enough to trigger activation of navigation mode

                # switch state of navigation mode
                self.navigation = True
                print("navigation mode is now active")

                self.d_dict["downward signal received"] = False
                os.system('play -nq -t alsa synth {} sine {}'.format(duration_2, frequency_1))
                drop_windows = 45

        return drop_windows


class Calibrator:
    """
        This class is used to calibrate the classifier for right-, left, upward- and downward eye movements, as well as
        for eye closure.

        Attributes:
            storage_D (np.ndarray): array used to store all D values during each recording phase during calibration
            storage_DD (np.ndarray): array used to store all DD values during each recording phase during calibration
            minimum_D (np.ndarray): array used to store the minimum D value of each storage_D array created during
                                    resting calibration
            maximum_D (np.ndarray): array used to store the maximum D value of each storage_D array created during
                                    resting calibration
            minimum_DD (np.ndarray): array used to store the minimum DD value of each storage_DD array created during
                                     resting calibration
            maximum_DD (np.ndarray): array used to store the maximum DD value of each storage_DD array created during
                                     resting calibration
            t_candidates (np.ndarray): array used to store threshold candidates during calibration of a specific
                                       direction
            self.num_recording (int): number of recording phases when performing the calibrations
            timer (int): timer used to time resting periods during calibration
        """

    def __init__(self, num_recording):
        self.minimum_D = np.array([])
        self.maximum_D = np.array([])
        self.minimum_DD = np.array([])
        self.maximum_DD = np.array([])
        self.storage_D = np.array([])
        self.storage_DD = np.array([])
        self.t_candidates = np.array([])
        self.num_recording = num_recording
        self.timer = 80

    def calibrate_resting(self, D, DD):
        """
        Computes estimates for the lowest and highest values for D and DD that can occur during phases of no eye
        movement. In self.num_recording recording phases (start and end of recording phases are signaled by a beep), the
        function stores the maximum and minimum values for D and DD that occurred during each recording phase, and
        then writes the maxima and minima of these resulting sets of values to calibration.txt.

        The beep that is used to notify the user of the start of the recording phase is actually played shortly before
        recording begins. This ensures that noise, caused by eye movements happening shortly before recording starts,
        does not interfere with the signal during recording.

        Arguments:
            D (float): The region under the graph as computed by compute_D()
            DD (float): The region under the graph as computed by compute_DD()

        Returns:
            str: returns "running" as long as self.num_recording recording phases have not yet been completed, and
            "finished" otherwise
        """

        if self.timer == 80:
            print("Get ready to keep eyes fixed...")
        # while self.timer has not reached 0, give user time to prepare for recording phase
        if self.timer > 0:
            self.timer -= 1

            # once self.timer hits 30, play a beep, signaling the user not to move eyes anymore
            if self.timer == 30:
                os.system('play -nq -t alsa synth {} sine {}'.format(duration_1, frequency_1))
                print("Keep eyes fixed")

        # once self.timer is equal to 0, the user is in recording phase
        elif self.timer == 0:

            # store 100 D and DD values
            if len(self.storage_D) < 100:
                self.storage_D = np.append(self.storage_D, np.array(D))
                self.storage_DD = np.append(self.storage_DD, np.array(DD))

            # once 100 D and 100 DD values are stored, the maximum and minimum of these sets of values are
            # computed and stored
            else:
                self.minimum_D = np.append(self.minimum_D, np.min(self.storage_D))
                self.maximum_D = np.append(self.maximum_D, np.max(self.storage_D))

                self.minimum_DD = np.append(self.minimum_DD, np.min(self.storage_DD))
                self.maximum_DD = np.append(self.maximum_DD, np.max(self.storage_DD))

                # timer and arrays are initialized again for the next recording phase
                self.timer = 80
                self.storage_D = np.array([])
                self.storage_DD = np.array([])

                # play beep to notify the user of the ending of current recording phase
                os.system('play -nq -t alsa synth {} sine {}'.format(duration_1, frequency_2))

                # check if self.num_recording recording phases have been completed
                if len(self.minimum_D) == self.num_recording:
                    # write minima and maxima to calibration.txt
                    # for minima and maxima of D and DD, the lowest and highest values that occurred throughout all
                    # recording phases are selected, in order to ensure the best possible estimates based on recorded
                    # data
                    file = open(r"calibration.txt", "w")
                    file.writelines(["min_D resting:" + str(np.min(self.minimum_D)) + "\n"
                                    , "max_D resting:" + str(np.max(self.maximum_D)) + "\n"
                                    , "min_DD resting:" + str(np.min(self.minimum_DD)) + "\n"
                                    , "max_DD resting:" + str(np.max(self.maximum_DD)) + "\n"])
                    file.close()

                    print("Resting calibration completed")
                    return "finished"

        return "running"

    def calibrate_direction(self, D, DD, direction):
        """
        Computes a threshold to be used for detecting the direction specified in the "direction" argument of the
        function. Depending on which direction is to be calibrated, in self.num_recording recording phases (during which
        a certain eye movement is performed) the function stores the first D or DD value that is higher/lower than the
        respective reference value computed by calibrate_resting() and stored in calibration.txt. Subsequently,
        the minimum/maximum of these values is selected and written to calibration.txt. (For example to determine
        the threshold for right direction, in each of the self.num_recording recording phases the first D value larger
        than ("max_D resting" *2) is stored. Then the minimum of the self.num_recording values is chosen to ensure
        the most effective threshold is selected based on the available data)

        The function notifies the user to not move the eyes anymore by playing a beep. Following is another beep
        notifying the user to move the eyes in the direction chosen for calibration. Subsequently another beep is
        played, notifying the user of the end of the recording phase. The initial beep notifying the user to not move the
        eyes anymore ensures that noise caused by eye movements happening before recording, does not interfere with the
        signal during recording.

        Arguments:
            D (float): The region under the graph as computed by compute_D()
            DD (float): The region under the graph as computed by compute_DD()
            direction (str) : The direction to be used for calibrating the classifier

        Returns:
            str: returns "running" as long as self.num_recording recording phases have not yet been completed, and
            "finished" otherwise
        """

        # start off by checking whether calibration during resting phases has been completed already
        if self.timer == 80:
            try:
                file = open(r"calibration.txt", "r")
            except OSError:
                print("You need to run \"main.py calibrate resting\" first")
                exit(1)
            if sum(1 for _ in file) < 4:
                file.close()
                print("You need to run \"main.py calibrate resting\" first")
                exit(1)
            file.close()
            print("Get ready to keep eyes fixed...")

        # while self.timer has not reached 0, give user time to prepare for recording phase
        if self.timer > 0:
            self.timer -= 1
            # once self.timer hits 30, play a beep, signaling the user not to move eyes anymore
            if self.timer == 30:
                print("Keep eyes fixed")
                os.system('play -nq -t alsa synth {} sine {}'.format(duration_1, frequency_1))
            # once self.timer reaches 0, recording starts
            if self.timer == 0:
                os.system('play -nq -t alsa synth {} sine {}'.format(duration_1, frequency_1))
                print("Look " + direction)

        # once self.timer is equal to 0, the user is in recording phase
        if self.timer == 0:

            # 30 D and DD values are stored, while keeping the order in which they occurred
            if len(self.storage_D) < 30:

                self.storage_D = np.append(self.storage_D, np.array(D))
                self.storage_DD = np.append(self.storage_DD, np.array(DD))

            # once 30 D and 30 DD values are stored, depending on which direction
            # is to be calibrated, the first D- or DD value is selected, that is lower/higher than 2 multiplied by the
            # respective reference value stored in calibration.txt (when not performing any eye movements, the
            # lowest/highest D- or DD value that can occur during no-eye-movement phases should not be larger/smaller
            # than double the reference value stored in calibration.txt
            else:

                file = open(r"calibration.txt", "r")

                # create a list containing the first 4 lines of calibration.txt and then map split(":") to each
                # element of this list
                k = list(map(lambda x: x.split(":"), [next(file) for _ in range(0, 4)]))
                file.close()

                if direction == "right":
                    max_D = float(k[1][1][:-2])
                    indices = np.where(self.storage_D > max_D * 2)
                    if len(indices[0]) == 0:
                        print("Calibration Error: Eye movement was not detected. Please restart calibration for "
                              "current direction")
                        exit(1)
                    t_candidate = np.take(self.storage_D, indices).flatten()[0]

                elif direction == "left":
                    min_D = float(k[0][1][:-2])
                    indices = np.where(self.storage_D < min_D * 2)
                    if len(indices[0]) == 0:
                        print("Calibration Error: Eye movement was not detected. Please restart calibration for "
                              "current direction")
                        exit(1)
                    t_candidate = np.take(self.storage_D, indices).flatten()[0]

                elif direction == "upward":
                    max_DD = float(k[3][1][:-2])
                    indices = np.where(self.storage_DD > max_DD * 2)
                    if len(indices[0]) == 0:
                        print("Calibration Error: Eye movement was not detected. Please restart calibration for "
                              "current direction")
                        exit(1)
                    t_candidate = np.take(self.storage_DD, indices).flatten()[0]

                else:
                    # direction == "downward":

                    min_DD = float(k[2][1][:-2])
                    indices = np.where(self.storage_DD < min_DD * 2)
                    if len(indices[0]) == 0:
                        print("Calibration Error: Eye movement was not detected. Please restart calibration for "
                              "current direction")
                        exit(1)
                    t_candidate = np.take(self.storage_DD, indices).flatten()[0]

                self.t_candidates = np.append(self.t_candidates, np.array([t_candidate]))

                # timer and arrays are initialized again for the next recording phase
                self.timer = 80
                self.storage_D = np.array([])
                self.storage_DD = np.array([])

                # play beep to notify the user of the ending of the current recording phase
                os.system('play -nq -t alsa synth {} sine {}'.format(duration_1, frequency_2))

                # check if self.num_recording recording phases have been completed
                if len(self.t_candidates) == self.num_recording:

                    # write the respective threshold to calibration.txt
                    # for minima and maxima of D and DD, the lowest and highest values that occurred throughout all
                    # recording phases are selected, in order to ensure the best possible estimates based on recorded
                    # data
                    if direction == "right":
                        add_line = "threshold right:" + str(np.min(self.t_candidates)) + "\n"

                    elif direction == "left":
                        add_line = "threshold left:" + str(np.max(self.t_candidates)) + "\n"

                    elif direction == "upward":
                        add_line = "threshold up:" + str(np.min(self.t_candidates)) + "\n"

                    elif direction == "downward":
                        add_line = "threshold down:" + str(np.max(self.t_candidates)) + "\n"

                    file = open(r"calibration.txt", "r+")
                    lines = file.readlines()

                    # check if calibration for current direction has already been performed before
                    if lines[-1].split(":")[0] == add_line.split(":")[0]:
                        file.close()
                        file = open(r"calibration.txt", "w")
                        # overwrite old threshold
                        file.writelines(lines[:-1] + [add_line])
                        file.close()

                    else:
                    # calibration has not been performed before for current direction
                        file.write(add_line)
                        file.close()

                    print(direction + " calibration completed")
                    return "finished"

        return "running"


def preprocessing(window):
    """
    Preprocesses window by removing artifacts. First the baseline is removed and then least-squares polynomial
    approximation used to smooth the signal

    Arguments:
        window (np.ndarray): The window to be preprocessed

    Returns:
        np.ndarray: The preprocessed window
    """

    # remove baseline
    means = np.mean(window, axis=0)
    window = np.subtract(window, means)

    # least-squares polynomial approximation with a degree of 10
    arr = np.empty((window.shape[0], 0))
    for i in range(0, 4):
        coefficients = np.polyfit(range(window.shape[0]), window[:, i], 10)
        fitted_data = np.polyval(coefficients, range(window.shape[0]))
        arr = np.column_stack((arr, fitted_data))
    window = arr

    return window


def compute_D(window):
    """
    Computes the difference X between the signals coming from AF7 and AF8 of the input window. The region under the
    graph (D) of the function defined by X is then approximated using the "trapezoidal rule".

    Arguments:
        window (np.ndarray): The window to be analyzed

    Returns:
        float: The region under the graph
    """

    X = np.subtract(window[:, 1], window[:, 2])
    D = 0.5 * X.shape[0] * (np.mean(X[0:10]) - np.mean(X[-10:]))
    return D


def compute_DD(window):
    """
    Computes the mean Y between the signals coming from TP9 and TP10 of the input window. The region under the
    graph (DD) of the function defined by Y is then approximated using the "trapezoidal rule".

    Arguments:
        window (np.ndarray): The window to be analyzed

    Returns:
        float: The region under the graph
    """
    window = np.column_stack((window[:, 0], window[:, 3]))
    Y = np.mean(window, axis=1)
    DD = 0.5 * Y.shape[0] * (np.mean(Y[0:10]) - np.mean(Y[-10:]))
    return DD


def update_window(window_1, window_2):
    """
    Appends window_2 to part of window_1. The amount of samples kept from window_1 depends on the size of window_2.
    The number of samples dropped from window_1 is equal to the size of window_2. This also means that, if window_2
    is larger than window_1, the resulting window will not contain any samples of window_1 (it will then only contain
    a subwindow of window_2)

    Arguments:
        window_1 (np.ndarray): window that contains the subwindow, that window_2 will get appended to
        window_2 (list): window that will be appended to a subwindow of window_1

    Returns:
        np.ndarray: The resulting window after appending window_2 to part of window_1
    """
    arr = np.array([])

    if len(window_2) >= window_1.shape[0]:
        # only consider the last "window size" samples (as specified in config.json)
        # (this is equal to window_1.shape[0]
        window_2 = window_2[-(window_1.shape[0]):]

    for i in window_2:
        # we consider only the first 4 channels (TP9, AF7, AF8, TP10)
        arr = np.append(arr, np.array(i[0:4]))
    window_2 = arr.reshape((-1, 4))

    # window_1 will drop as many samples as there are samples contained in window_2
    start = window_2.shape[0]

    next_window = np.append(window_1[start:, :], window_2, axis=0)

    return next_window
