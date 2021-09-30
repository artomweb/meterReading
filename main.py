# import the necessary packages
from imutils.perspective import four_point_transform
from imutils import contours
import imutils
import cv2
import numpy as np

from sklearn import tree
from PIL import Image
from sklearn.tree.export import export_text
from sklearn.tree import _tree
from sklearn.model_selection import train_test_split

import matplotlib.pyplot as plt

import os


def getDigitsFromImage(image, debug=False):
    image = imutils.resize(image, height=750)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edged = cv2.Canny(blurred, 50, 150, 255)

    thresh = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # print(len(cnts))
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.015 * peri, True)
        (x, y, w, h) = cv2.boundingRect(c)
        if len(approx) == 4 and w >= 30:
            cv2.rectangle(image, (x, y), (x+w, y+h), (36, 255, 12), 2)
            x, y, w, h = cv2.boundingRect(approx)
            displayCnt = approx
            break

    warped = four_point_transform(gray, displayCnt.reshape(4, 2))
    output = four_point_transform(image, displayCnt.reshape(4, 2))

    w, h = warped.shape
    m = 10
    warped = warped[m:w-m, m:h-m]
    output = output[m:w-m, m:h-m]

    kernel = np.ones((7, 7), np.uint8)

    # threshold params
    low = 0
    high = 255
    iters = 1

    blur = cv2.GaussianBlur(warped, (1, 1), 0)

    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 87, 9)

    thresh[0:thresh.shape[0], 219:227] = 0
    warped[0:thresh.shape[0], 219:227] = 0

    # print(blur[10, 10])

    for a in range(iters):
        thresh = cv2.dilate(thresh, kernel)

    for a in range(iters):
        thresh = cv2.erode(thresh, kernel)

    # cv2.imshow("2", thresh)
    # cv2.waitKey(0)

    cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    digitCnts = []
    for c in cnts:
        # cv2.drawContours(output, [c], -1, (36, 255, 12), 3)
        x, y, w, h = cv2.boundingRect(c)
        # print(w, h)
        if w < 50 and h > 50:
            cv2.rectangle(thresh, (x, y), (x+w, y+h), (0, 255, 0), 2)
            digitCnts.append(c)
        else:
            cv2.rectangle(thresh, (x, y), (x+w, y+h), (0, 0, 255), 2)

    if debug:
        print("num digits: ", len(digitCnts))

    digitCnts = contours.sort_contours(digitCnts,
                                       method="left-to-right")[0]

    digits = []
    for i, c in enumerate(digitCnts):
        x, y, w, h = cv2.boundingRect(c)
        ROI = thresh[y:y+h, x:x+w]
        # ROI = cv2.equalizeHist(ROI)
        # ROI = np.invert(ROI)
        ROI = cv2.resize(ROI, (8, 16))
        ROI = cv2.threshold(ROI, 1, 255, cv2.THRESH_BINARY)[1]
        digits.append(ROI)
        cv2.imwrite("proc/" + str(i) + ".jpg", ROI)
        cv2.waitKey(0)
        # print(w)

    # if debug:
    #     cv2.imshow("2", thresh)
    #     cv2.waitKey(0)

    # cv2.imshow("out", output)
    # cv2.imshow("2", thresh)
    # cv2.waitKey(0)

    return digits


image_vals = {}

for r, dirs, files in os.walk("./labelled"):
    for filename in files:
        fn = filename.split("_")
        image_vals[filename] = fn[2].split(".")[0]

# print(image_vals)


X = []
Y = []


for img, val in image_vals.items():
    image = cv2.imread("./labelled/" + img)
    actualDigits = list(val.split(".")[0])
    digits = getDigitsFromImage(image,
                                # debug=True
                                )

    if len(digits) == len(actualDigits):
        X.extend(digits)
        Y.extend(actualDigits)
    else:
        print("Error: mismatch digit lengths")


# image = cv2.imread("labelled/" + "4.jpg")

# digits = getDigitsFromImage(image)

# print(len(digits))


def view_digit(digit):
    plt.imshow(digit,
               cmap="gray", interpolation='nearest')
    plt.show()


# view_digit(X[0])

# print(Y)
# print(X)

X = np.array(X)

X = X.reshape(X.shape[0], X.shape[1] * X.shape[2])

# print(X.shape)
X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.1)
clf = tree.DecisionTreeClassifier(max_depth=3,
                                  random_state=0)
clf = clf.fit(X_train, y_train)

print(clf.score(X_test, y_test))

# Y = np.array(Y)

# print(sorted(np.unique(Y)))


# for i in range(len(Y)):
#     print("\n")
#     print(clf.predict(X[i].reshape(1, -1)))
#     print(Y[i])

# tree.plot_tree(clf,
#                class_names=Y,
#                filled=True)

# plt.show()

# cv2.imshow("Output", thresh)
# cv2.waitKey(0)

testImage = cv2.imread("imgs\esp32-cam_1632945211_0326260.jpg")
digits = getDigitsFromImage(testImage)

if len(digits) < 7:
    print("Could not find all digits")
    exit()

result = ''
for d in digits:
    pred = clf.predict(d.reshape(1, -1))[0]
    print(pred)
    result += pred

finalNum = float(result[:6] + '.' + result[6])

print(finalNum)

# tree.plot_tree(clf,
#                class_names=Y,
#                filled=True)

# plt.show()
