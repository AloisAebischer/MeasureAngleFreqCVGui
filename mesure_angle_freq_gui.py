# import libraries
import sys
import cv2
import os
import time
from datetime import datetime
import imutils
import numpy as np
import progressbar
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore
from imutils import paths

# define some constants
IMAGEWIDTH = 320
IMAGEHEIGHT = 240
RESOLUTION = [IMAGEWIDTH,IMAGEHEIGHT]
SHAPE = [IMAGEHEIGHT,IMAGEWIDTH]
DISPLAYWIDTH = 320
DISPLAYHEIGHT = 240
FPS = 30
RECORD_FPS = 60
THRESHOLD = 10
MIN_AREA = 1000
MIN_AREA_DIFF = 1000
BLURSIZE = (15,15)
blue = (255,0,0)
deepskyblue = (255,191,0)
red = (0,0,255)
green = (128,255,0)
white = (255,255,255)
black = (0,0,0)
CLOCKWISE = 1
COUNTER_CLOCKWISE = 2
STATIC_COUNTER_THRESH = 3
#define some variables
startX = 0
startY = 0
cX = 0
cY = 0
prev_cX = 0
prev_cY = 0
start_angle = 0
angle = 0
previous_angle = 0
stop = False
count = 0
start_pressed = False
quit_pressed = False
display_angle = True
focus_value = 960
focus_changed = True
rec_duration = 5000
running = False
# compute center coordinates and radius for drawing a target
centerX = IMAGEWIDTH // 2
centerY = IMAGEHEIGHT // 2
radius = int(centerY // 2)
inner_radius = radius - 30
target_size = 15
# create mask to highlight circular section 
circ_mask = np.zeros(SHAPE, dtype="uint8")
cv2.circle(circ_mask, (centerX, centerY), radius, white, -1)
cv2.circle(circ_mask, (centerX, centerY), inner_radius, black, -1)
# create filter to highlight magnet
lower_hsv = np.array([20, 100, 0])
higher_hsv = np.array([100, 255, 255])
# create empty array to compute image substraction
previous_diff = None
frame_diff = np.zeros(SHAPE, dtype="uint8")
thresh_diff = np.zeros(SHAPE, dtype="uint8")
# function to get the frame number from the image path
def get_number(imagePath):
	return int(imagePath.split(os.path.sep)[-1][:-4])
# separate thread for camera stream
class cameraThread(QThread):
    imageUpdate = pyqtSignal(QImage)
    def __init__(self):
        super().__init__()
        self.ThreadActive = True
    def run(self):
        # global variables
        global cap
        global start_pressed
        global quit_pressed
        global display_angle
        global focus_value
        global focus_changed
        global previous_diff
        global rec_duration
        global running
        cap = cv2.VideoCapture(0)
        # main loop
        while self.ThreadActive:
            # setup camera
            print("[INFO] Warming up camera...")
            running = False
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,IMAGEWIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT,IMAGEHEIGHT)
            cap.set(cv2.CAP_PROP_FPS, FPS)
            time.sleep(1)
            # setup loop to center object with target
            print("[INFO] Center the wheel and press start...")
            while True:
                # grab the frame from the stream
                ret, image = cap.read()
                #image = imutils.resize(image, width=IMAGEWIDTH)
                # draw circular area used for computation
                cv2.circle(image, (centerX, centerY), radius, red, 2)
                cv2.circle(image, (centerX, centerY), inner_radius, red, 2)
                # draw target at the center
                cv2.line(image, (centerX, centerY), (centerX + target_size, centerY), red, 2)
                cv2.line(image, (centerX, centerY), (centerX, centerY + target_size), red, 2)
                cv2.line(image, (centerX, centerY), (centerX - target_size, centerY), red, 2)
                cv2.line(image, (centerX, centerY), (centerX, centerY - target_size), red, 2)
                # display datetime
                ts = datetime.now().strftime("%A %d %B %Y %I:%M:%S:%p")
                cv2.putText(image, ts, (10, image.shape[0]-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.3, green, 1)
                # display FPS
                fps = str(int(RECORD_FPS))
                cv2.putText(image, fps, (image.shape[1]-70, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, red, 1)
                cv2.putText(image, "fps", (image.shape[1]-50, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, red, 1)
                # convert from opencv format to pyqt format
                imageRGB = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                #flippedImage = cv2.flip(imageRGB, 1)
                convertToQtFormat = QImage(imageRGB.data, imageRGB.shape[1], imageRGB.shape[0], QImage.Format_RGB888)
                qtImage = convertToQtFormat.scaled(DISPLAYWIDTH, DISPLAYHEIGHT, Qt.KeepAspectRatio)
                # display image
                self.imageUpdate.emit(qtImage)
                # if `start` is pressed, break from the loop and start recording
                if start_pressed:
                    start_pressed = False
                    break
                # adjust focus
                if focus_changed:
                    value = (focus_value<<4) & 0x3ff0
                    dat1 = (value>>8)&0x3f
                    dat2 = value & 0xf0
                    os.system("i2cset -y 0 0x0c %d %d" % (dat1,dat2))
                    time.sleep(0.5)
                    focus_changed = False
            focus_changed = True
            running = True
            print("[INFO] Recording video at " + str(RECORD_FPS) + " FPS...")
            # compute total amount of frames to record
            total_frames = int(RECORD_FPS * rec_duration / 1000)
            # create the images directory 
            outputDir = os.path.join("images",
                datetime.now().strftime("%Y-%m-%d-%H%M%S"))
            os.makedirs(outputDir)
            # set fps for recording
            cap.set(cv2.CAP_PROP_FPS, RECORD_FPS)
            time.sleep(1)
            # save current time to measure real fps
            #start_time = time.time()
            # loop to record images
            for i in range(5):
                ret, img = cap.read()
            # loop to record images
            for i in range(total_frames):
                ret, img = cap.read()
                # write the current frame to images directory
                if ret:
                    filename = "{}.jpg".format(str(i).zfill(16))
                    cv2.imwrite(os.path.join(outputDir, filename), img)
            # compute elapsed time to measure real fps
            #end_time = time.time()
            #elapsed_time = round(end_time - start_time, 2)
            print("[INFO] Total frames recorded = " + str(total_frames))
            real_fps = round(1000*total_frames/rec_duration, 2)
            sec_per_frame = 1/real_fps
            #print("[INFO] Video recorded at " + str(real_fps) + " FPS")

            # COMPUTE ANGLES AND FREQ
            # define local variables
            start_position_found = False
            direction = None
            previous_direction = None
            swing_cw = False
            swing_ccw = False
            first_swing = False
            freq = 0.000
            angle = 0
            start_angle = 0
            previous_angle = 0
            frame_counter = 0
            freq_frame_counter = 0
            static_image_counter = 0
            first_image_diff = None
            startX = 0
            startY = 0
            cX = 0
            cY = 0
            found_countour = None
            prev_cX = 0
            prev_cY = 0
            outputDir2 = os.path.join("images", "2021-05-28-165733")
            total_frames = 270
            imagePaths = list(paths.list_images(outputDir))
            imagePaths2 = list(paths.list_images(outputDir2))
            # initialize the video and progress bar for processing
            widgets_mean = ["[INFO] Processing angles and frequencies...", progressbar.Percentage(), " ", 
                progressbar.Bar()]
            pbar_mean = progressbar.ProgressBar(maxval=total_frames, 
                widgets=widgets_mean).start()
            # loop through the images to compute angles and frequencies
            previous_diff = None
            for (i, imagePath) in enumerate(sorted(imagePaths2, key=get_number)):
                # capture frame-by-frame
                frame = None
                frame = cv2.imread(imagePath)
                if frame is not None:
                    # pause image
                    while start_pressed:
                        pass
                    image = frame
                    # copy for substraction method 
                    image_diff = image.copy()
                    # copy for color filter method 
                    image_color = image_diff
                    # apply mask to select only circular part
                    masked_image_diff = cv2.bitwise_and(image_color,image_color,mask = circ_mask)
                    masked_image_color = masked_image_diff.copy()
                    # IMAGE SUBSTRACTION METHOD TO COMPUTE FREQUENCY
                    # convert to gray 
                    gray_diff = cv2.cvtColor(masked_image_diff, cv2.COLOR_BGR2GRAY)
                    # apply blur
                    gray_diff = cv2.GaussianBlur(gray_diff, BLURSIZE, 0)
                    # compute difference with previsous image
                    if previous_diff is None:
                        previous_diff = gray_diff
                    frame_diff = cv2.absdiff(gray_diff, previous_diff)
                    # apply threshold and dilatation
                    thresh_diff = cv2.threshold(frame_diff, THRESHOLD, 255, cv2.THRESH_BINARY)[1]
                    thresh_diff = cv2.dilate(thresh_diff, None, iterations = 2)
                    # grab contours in threshold image
                    cnts_diff = cv2.findContours(thresh_diff.copy(), cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
                    cnts_diff = imutils.grab_contours(cnts_diff)
                    biggest_area_diff = 0
                    # loop through all found contours
                    for c in cnts_diff:
                        M = cv2.moments(c)
                        if M["m00"] != 0:
                            # compute the center of the contour
                            cX = int(M["m10"] / M["m00"])
                            cY = int(M["m01"] / M["m00"])
                            # draw countour
                            #cv2.drawContours(image, [c], -1, blue, 2)
                            # compute the bounding box for the contour
                            (x1, y1, w1, h1) = cv2.boundingRect(c)
                            # get an approximate area of the contour
                            found_area = w1*h1 
                            # find the largest bounding rectangle
                            if (found_area > biggest_area_diff):  
                                biggest_area_diff = found_area
                    # check for moving object
                    object_moving = False
                    if biggest_area_diff > MIN_AREA_DIFF:
                        object_moving = True
                    # check if first image
                    if first_image_diff is None:
                        first_image_diff = True
                        static_image_counter = STATIC_COUNTER_THRESH
                    # if moving object
                    elif object_moving:
                        static_image_counter = 0
                    # if no moving object
                    else:
                        static_image_counter = static_image_counter + 1
                    # compute frequency
                    if static_image_counter == STATIC_COUNTER_THRESH:
                        if first_swing is False:
                            first_swing = True
                        else:
                            if freq_frame_counter > 0 and sec_per_frame > 0:
                                freq = round(1/(freq_frame_counter * sec_per_frame), 2)
                            freq_frame_counter = 0
                            first_swing = False
                    # counter to compute frequency
                    freq_frame_counter = freq_frame_counter + 1
                    # save current image to compute difference with the next one
                    previous_diff = gray_diff
                    # COLOR FILTER METHOD TO COMPUTE ANGLE
                    if display_angle:
                        # convert the frame to HSV
                        hsv = cv2.cvtColor(masked_image_color, cv2.COLOR_BGR2HSV)
                        # create HSV color mask
                        color_mask = cv2.inRange(hsv, lower_hsv, higher_hsv)
                        # apply HSV color mask
                        result_color_filter = cv2.bitwise_and(masked_image_color,masked_image_color,mask = color_mask)
                        # convert to gray and apply threshold
                        gray_color = cv2.cvtColor(result_color_filter, cv2.COLOR_BGR2GRAY)
                        #gray = cv2.GaussianBlur(gray, BLURSIZE, 0)
                        thresh = cv2.threshold(gray_color, THRESHOLD, 255, cv2.THRESH_BINARY)[1]
                        # grab contours
                        cnts_color = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)
                        cnts_color = imutils.grab_contours(cnts_color)
                        object_fg_found = False
                        biggest_area_color = 0
                        # loop through all found contours
                        for c in cnts_color:
                            M = cv2.moments(c)
                            if M["m00"] != 0:
                                # compute the bounding box for the contour
                                (x1, y1, w1, h1) = cv2.boundingRect(c)
                                # get an approximate area of the contour
                                found_area = w1*h1 
                                # find the largest bounding rectangle
                                if (found_area > MIN_AREA and found_area > biggest_area_color):  
                                    biggest_area_color = found_area
                                    object_fg_found = True
                                    # compute the center of the contour
                                    cX = int(M["m10"] / M["m00"])
                                    cY = int(M["m01"] / M["m00"])
                                    found_countour = c
                                    x = x1
                                    y = y1
                                    h = h1
                                    w = w1
                        #print(biggest_area_color)
                        # IF COLOR FILTER METHOD FOUND AN OBJECT
                        if object_fg_found:
                            # draw the contour and center of the shape on the image
                            cv2.drawContours(image, [found_countour], -1, red, 2)
                            # compute x,y in trigo space
                            trigX = cX - centerX
                            trigY = -(cY - centerY)
                            # compute current angle between 0-360
                            current_angle = np.arctan2(trigY, trigX)*360/(2*np.pi)
                            if current_angle < 0:
                                current_angle = current_angle + 360
                            # compute reference position
                            if start_position_found is False:
                                # save start x,y in image space
                                startX = cX
                                startY = cY
                                # save angle as start angle
                                start_angle = current_angle
                                previous_angle = start_angle
                                start_position_found = True
                            else:
                                # compute delta for clockwise direction
                                delta1 = current_angle - previous_angle
                                if delta1 < 0:
                                    delta1 = delta1 + 360
                                # compute delta for counterclockwise direction
                                delta2 = previous_angle - current_angle 
                                if delta2 < 0:
                                    delta2 = delta2 + 360
                                wrong_value = False
                                # check if the wheel is not moving
                                if static_image_counter >= STATIC_COUNTER_THRESH:
                                    # set new start position
                                    startX = cX
                                    startY = cY
                                    start_angle = current_angle
                                # check for noise value
                                elif delta1 < 3 or delta2 < 3:
                                    pass
                                # check if the direction is CW
                                elif delta1 <= delta2:
                                    direction = CLOCKWISE
                                # check if the direction is CCW
                                elif delta2 < delta1:
                                    direction = COUNTER_CLOCKWISE
                                # compute angle for CW direction
                                if direction is CLOCKWISE:
                                    # compute delta with start angle
                                    angle = current_angle - start_angle
                                    # draw partial circle
                                    if angle < 0:
                                        angle = angle + 360
                                        cv2.ellipse(image, (centerX, centerY), (15,15), 0, -start_angle , -(current_angle+360), deepskyblue, -1)
                                    else:
                                        cv2.ellipse(image, (centerX, centerY), (15,15), 0, -start_angle , -current_angle, deepskyblue, -1)
                                # compute angle for CCW direction
                                elif direction is COUNTER_CLOCKWISE:
                                    # compute delta with start angle
                                    angle = start_angle - current_angle
                                    # draw partial circle
                                    if angle < 0:
                                        angle = angle + 360
                                        cv2.ellipse(image, (centerX, centerY), (15,15), 0, -current_angle, -(start_angle+360), deepskyblue, -1)
                                    else:
                                        cv2.ellipse(image, (centerX, centerY), (15,15), 0, -current_angle , -start_angle, deepskyblue, -1)
                                # draw construction lines
                                cv2.circle(image, (centerX, centerY), 3, deepskyblue, -1)
                                cv2.circle(image, (cX, cY), 3, deepskyblue, -1)
                                cv2.line(image, (centerX, centerY), (cX, cY), deepskyblue, 2)
                                # save current values in previous values
                                previous_angle = current_angle
                                previous_direction = direction
                                prev_cX = cX
                                prev_cY = cY
                            # draw line from center to start position
                            if start_position_found:
                                cv2.circle(image, (centerX, centerY), 3, deepskyblue, -1)
                                cv2.circle(image, (startX, startY), 3, deepskyblue, -1)
                                cv2.line(image, (centerX, centerY), (startX, startY), deepskyblue, 2)
                    else:
                        angle = 0
                    # display FPS
                    real_fps = str(int(real_fps))
                    cv2.putText(image, real_fps, (image.shape[1]-70, 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, red, 1)
                    cv2.putText(image, "fps", (image.shape[1]-50, 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, red, 1)
                    # display frequency
                    freq_string = str(freq)
                    cv2.putText(image, freq_string, (image.shape[1]-90, image.shape[0]-40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, deepskyblue, 2)
                    cv2.putText(image, "Hz", (image.shape[1]-50, image.shape[0]-40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, deepskyblue, 2)
                    # display angle
                    angle_string = str(int(angle))
                    cv2.putText(image, angle_string, (image.shape[1]-90, image.shape[0]-20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, deepskyblue, 2)
                    cv2.putText(image, "deg", (image.shape[1]-50, image.shape[0]-20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, deepskyblue, 2)
                    # update progress bar
                    frame_counter = frame_counter + 1
                    pbar_mean.update(frame_counter)
                    #cv2.imshow("Mesure angle balancier",image)
                    # convert from opencv format to pyqt format
                    imageRGB = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    #flippedImage = cv2.flip(imageRGB, 1)
                    convertToQtFormat = QImage(imageRGB.data, imageRGB.shape[1], imageRGB.shape[0], QImage.Format_RGB888)
                    qtImage = convertToQtFormat.scaled(DISPLAYWIDTH, DISPLAYHEIGHT, Qt.KeepAspectRatio)
                    # display image
                    self.imageUpdate.emit(qtImage)
                    time.sleep(0.1)
                    if quit_pressed:
                        quit_pressed = False
                        break
                else:
                    break
            # release the video capture object
            #cap.release()
            print("\n")
            # remove images folder
            for (i, imagePath) in enumerate(sorted(imagePaths, key=get_number)):
                os.remove(imagePath)
            os.rmdir(outputDir)
    # stop camera stream
    def stop(self):
        self.ThreadActive = False
        self.quit()
# create GUI app
class App(QDialog):
    # define some variables
    def __init__(self):
        super().__init__()
        self.title = 'Mesure angle et fréquence'
        self.left = 0
        self.top = 0
        self.width = 640
        self.height = 480
        self.initUI()
    # init the UI app
    def initUI(self):
        # init window and grid
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setStyleSheet("background-color:black;")
        self.createCameraLayout()
        self.createButtonsLayout()
        # create main window
        windowLayout = QVBoxLayout()
        windowLayout.addLayout(self.cameraLayout)
        windowLayout.addLayout(self.buttonGroupLayout)
        self.setLayout(windowLayout)
        # create camera feed
        self.cameraStream = cameraThread()
        self.cameraStream.start()
        self.cameraStream.imageUpdate.connect(self.imageUpdateSlot)
        self.show()
    # create camera box layout
    def createCameraLayout(self):
        # camera horizontal layout
        self.cameraLayout = QHBoxLayout()
        # layout for parameter
        paramGroupBox = QWidget()
        paramGroupBox.setStyleSheet("QLabel {font-size: 12pt; font-weight: bold; color: deepskyblue} QCheckBox {color: deepskyblue ;font-size: 10pt; font-weight: bold;}")
        paramLayout = QVBoxLayout()
        paramLayout.setContentsMargins(0,0,0,0)
        # duration checkbox
        durationGroupBox = QGroupBox()
        durationGroupBox.setStyleSheet("QGroupBox {border: 2px solid deepskyblue;}")
        durationLayout = QVBoxLayout()
        labelDuration = QLabel("Temps")
        durationLayout.addWidget(labelDuration)
        durationCheckGroup = QButtonGroup(self)
        durationCheckGroup.buttonClicked[QAbstractButton].connect(self.durationClicked)
        self.duration1 = QCheckBox("1 sec")
        self.duration2 = QCheckBox("2 sec")
        self.duration3 = QCheckBox("3 sec")
        self.duration4 = QCheckBox("5 sec")
        self.duration4.setChecked(True)
        self.duration5 = QCheckBox("10 sec")
        durationCheckGroup.addButton(self.duration1,1)
        durationCheckGroup.addButton(self.duration2,2)
        durationCheckGroup.addButton(self.duration3,3)
        durationCheckGroup.addButton(self.duration4,4)
        durationCheckGroup.addButton(self.duration5,5)
        durationLayout.addWidget(self.duration1)
        durationLayout.addWidget(self.duration2)
        durationLayout.addWidget(self.duration3)
        durationLayout.addWidget(self.duration4)
        durationLayout.addWidget(self.duration5)
        durationLayout.addStretch(1)
        durationGroupBox.setLayout(durationLayout)
        paramLayout.addWidget(durationGroupBox)
        # compute angle checkbox
        angleGroupBox = QGroupBox()
        angleGroupBox.setStyleSheet("QGroupBox {border: 2px solid deepskyblue;} " )
        angleLayout = QVBoxLayout()
        angleLabel = QLabel("Angle")
        angleLayout.addWidget(angleLabel)
        self.angleButton = QPushButton("ON", self)
        angleLayout.addWidget(self.angleButton)
        self.angleButton.clicked.connect(self.anglePressed)
        angleGroupBox.setLayout(angleLayout)
        paramLayout.addWidget(angleGroupBox)
        paramGroupBox.setLayout(paramLayout)
        self.cameraLayout.addWidget(paramGroupBox)
        # canvas for camera stream
        cameraGroupBox = QGroupBox()
        cameraGroupBox.setFixedWidth(DISPLAYWIDTH)
        cameraGroupBox.setStyleSheet("QGroupBox {border: 2px solid deepskyblue;} QLabel {font-size: 12pt; font-weight: bold; color: deepskyblue}")
        cameraLayout = QVBoxLayout()
        cameraLayout.setContentsMargins(5,10,0,0)
        cameraLabel = QLabel("Camera")
        cameraLayout.addWidget(cameraLabel)
        self.cameraBox = QLabel(self)
        #self.cameraBox.setFixedWidth(DISPLAYWIDTH)
        #self.cameraBox.setFixedHeight(DISPLAYHEIGHT)
        #self.cameraBox.resize(DISPLAYWIDTH, DISPLAYHEIGHT)
        #self.cameraBox.setStyleSheet("QLabel {border: 2px solid deepskyblue;}")
        cameraLayout.addWidget(self.cameraBox)
        cameraLayout.addStretch(1)
        cameraGroupBox.setLayout(cameraLayout)
        self.cameraLayout.addWidget(cameraGroupBox)
        # slider for focus
        focusGroupBox = QGroupBox()
        focusGroupBox.setStyleSheet("QGroupBox {border: 2px solid deepskyblue;} QLabel {font-size: 12pt; font-weight: bold; color: deepskyblue}")
        focusLayout = QVBoxLayout()
        angleLabel = QLabel("Focus")
        focusLayout.addWidget(angleLabel)
        self.focusSlider = QSlider(Qt.Vertical)
        self.focusSlider.setMinimum(10)
        self.focusSlider.setMaximum(1000)
        global focus_value
        self.focusSlider.setValue(focus_value)
        self.focusSlider.setTickPosition(QSlider.TicksBothSides)
        self.focusSlider.setTickInterval(100)
        self.focusSlider.valueChanged.connect(self.focusSliderMoved)
        #self.focusSlider.adjustSize()
        focusLayout.addWidget(self.focusSlider, alignment = QtCore.Qt.AlignHCenter)
        focusGroupBox.setLayout(focusLayout)
        self.cameraLayout.addWidget(focusGroupBox)
    # create buttons layout
    def createButtonsLayout(self):
        self.buttonGroupLayout = QHBoxLayout()
        buttonGroupBox = QGroupBox()
        buttonGroupBox.setStyleSheet("QPushButton {color: springgreen; font-size: 16pt; font-weight: bold; border: 2px solid springgreen}")
        buttonsLayout = QHBoxLayout()
        saveButton = QPushButton("SAVE")
        saveButton.setMinimumHeight(50)
        buttonsLayout.addWidget(saveButton)
        startButton = QPushButton("START")
        startButton.clicked.connect(self.startPressed)
        startButton.setMinimumHeight(50)
        buttonsLayout.addWidget(startButton)
        quitButton = QPushButton("QUIT")
        quitButton.clicked.connect(self.quitPressed)
        quitButton.setMinimumHeight(50)
        buttonsLayout.addWidget(quitButton)
        buttonGroupBox.setLayout(buttonsLayout)
        self.buttonGroupLayout.addWidget(buttonGroupBox)
    # start button function
    def startPressed(self):
        global start_pressed
        if start_pressed is True:
            start_pressed = False
        else:
            start_pressed = True
    # quit button function
    def quitPressed(self):
        global quit_pressed
        global running
        quit_pressed = True
        if running is False:
            self.stopApp()
    def anglePressed(self):
        global display_angle
        if display_angle:
            display_angle = False
            self.angleButton.setText("OFF")
        else:
            display_angle = True
            self.angleButton.setText("ON")
    # focus slider moved function
    def focusSliderMoved(self):
        global focus_changed
        focus_changed = True
        global focus_value
        focus_value = self.focusSlider.value()
    # duration clicked function
    def durationClicked(self, duration):
        global rec_duration
        switcher = {
            "1 sec": 1,
            "2 sec": 2,
            "3 sec": 3,
            "5 sec": 5,
            "10 sec": 10,
        }
        #rec_duration = 1000*
        check_box_value = switcher.get(duration.text(), None)
        if check_box_value is None:
            print("[INFO] Invalid duration value")
        else:
            rec_duration = 1000*check_box_value
    # update video feed
    def imageUpdateSlot(self, Image):
        self.cameraBox.setPixmap(QPixmap.fromImage(Image))
    # stop the app
    def stopApp(self):
        self.cameraStream.stop()
        self.close()
    
# main app
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
