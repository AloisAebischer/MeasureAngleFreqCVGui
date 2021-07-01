import cv2
import numpy as np
 
def nothing(x):
    pass
 
# Create a window
cv2.namedWindow('image')
 
# create trackbars for color change
cv2.createTrackbar('lowH','image',0,179,nothing)
cv2.createTrackbar('highH','image',179,179,nothing)
 
cv2.createTrackbar('lowS','image',0,255,nothing)
cv2.createTrackbar('highS','image',255,255,nothing)
 
cv2.createTrackbar('lowV','image',0,255,nothing)
cv2.createTrackbar('highV','image',255,255,nothing)

# compute center
image = cv2.imread("images/2021-06-30-173225/0000000000000000.jpg")
centerX = image.shape[1] // 2
centerY = image.shape[0] // 2
radius = int(0.25*centerY)
inner_radius = int(0.8*radius)

# create mask to highlight circular section when magnet moves
white = (255,255,255)
black = (0,0,0)
mask = np.zeros(image.shape[:2], dtype="uint8")
cv2.circle(mask, (centerX, centerY), radius, white, -1)
cv2.circle(mask, (centerX, centerY), inner_radius, black, -1)
 
while(True):
    #ret, frame = cap.read()
    frame = cv2.imread("images/2021-06-30-173638/0000000000000000.jpg")
    # get current positions of the trackbars
    ilowH = cv2.getTrackbarPos('lowH', 'image')
    ihighH = cv2.getTrackbarPos('highH', 'image')
    ilowS = cv2.getTrackbarPos('lowS', 'image')
    ihighS = cv2.getTrackbarPos('highS', 'image')
    ilowV = cv2.getTrackbarPos('lowV', 'image')
    ihighV = cv2.getTrackbarPos('highV', 'image')
    
    image = frame.copy()
    # apply mask to select circular area
    masked_image = cv2.bitwise_and(image,image,mask = mask)
    # convert color to hsv because it is easy to track colors in this color model
    hsv = cv2.cvtColor(masked_image, cv2.COLOR_BGR2HSV)
    # Apply the cv2.inrange method to create color mask
    lower_hsv = np.array([ilowH, ilowS, ilowV])
    higher_hsv = np.array([ihighH, ihighS, ihighV])
    color_mask = cv2.inRange(hsv, lower_hsv, higher_hsv)
    # Apply the mask on the image to extract the original color
    image = cv2.bitwise_and(masked_image, masked_image, mask=color_mask)
    cv2.imshow('image', image)
    # Press q to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cv2.destroyAllWindows()