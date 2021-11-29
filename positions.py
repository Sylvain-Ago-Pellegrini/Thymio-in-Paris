import numpy as np
import cv2 as cv
import math


def detect_circles(img, lower_range, upper_range):

    # convert img from rgb to hsv
    hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)

    # extract colored circles in white
    mask = cv.inRange(hsv, lower_range, upper_range)

    # detect circles
    blurred = cv.blur(mask, (3, 3))
    circles = cv.HoughCircles(blurred, cv.HOUGH_GRADIENT, 1, 20,
                                param1 = 50, param2 = 30, minRadius = 1, maxRadius = 50)
    print(circles)
    #circles = np.uint16(np.around(circles))
    return circles

# (x,y)


def get_goal_position(img):
    # green color in hsv: 120°, 100%, 50% or 120°, 100%, 100%
    lower_green = np.array([36, 0, 0])
    upper_green = np.array([70, 255, 255])

    circle = detect_circles(img, lower_green, upper_green)

    if circle is None:
        print("no circle found")
        return False, None

    elif len(circle) > 1:
        print("more than two circles found")
        return len(circle)

    center = (circle[0], circle[1])

    return center


# (x,y) + angle between -pi and pi
def get_robot_position(img):
    # blue color in hsv:
    lower_blue = np.array([100, 50, 38])
    upper_blue = np.array([110, 255, 255])

    circles = detect_circles(img, lower_blue, upper_blue)

    list_centers = []
    list_radius = []

    #for i in circles[0, :]:
    #    list_centers.append = (i[0], i[1])
    #    list_radius.append = i[2]

    if not len(circles):
        print("no circle found")
        return 0

    elif len(circles) > 2:
        print("more than two circles found")
        return len(circles)

    #if list_radius[0] > list_radius[1]:
    #    center1 = list_centers[0]
    #    center2 = list_centers[1]
    #else:
    #    center1 = list_centers[1]
    #    center2 = list_centers[0]

    if circles[0][2] > circles[1][2]:
        center1 = circles[0][0:1]
        center2 = circles[1][0:1]
    else:
        center1 = circles[1][0:1]
        center2 = circles[0][0:1]

    angle = math.atan2((center2[1]-center1[1])/(center2[1]-center2[0]))

    position = np.array([center1, angle])

    return position


def get_arch_positions(img):
    hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)

    lower_red = np.array([169, 100, 100])
    upper_red = np.array([189, 255, 255])

    # extract red arch in white
    mask = cv.inRange(hsv, lower_red, upper_red)
    blurred = cv.blur(mask, (3, 3))



