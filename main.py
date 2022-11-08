from tokenize import String
from PIL import Image
import cv2 as cv
import numpy as np
import pytesseract
import pdf2image

TEXT_BOX_MIN_ASPECT_RATIO = 3
START_PAGE = 2
END_PAGE = 2

def rejectChildBoxes(boxes):
    """Takes a list of box tuples in form x,y,w,h and rejects those inside another"""
    filtered = []
    for box2 in boxes:
        x2, y2, w2, h2 = box2
        notInside = True
        for box1 in boxes:
            x1, y1, w1, h1 = box1
            if x2 > x1 and (x2+w2) < (x1+w1) and y2 > y1 and (y2+h2) < (y1+h1):
                notInside = False
        if notInside:
            filtered.append(box2)
    return filtered

def getROIsFromImage(mat):
    mat = cv.threshold(mat, 127, 255, cv.THRESH_BINARY)[1]
    mat = cv.Canny(mat, 200, 255)
    mat = cv.dilate(mat, np.ones(
            (1,1), np.uint8), iterations=5)
    contours = cv.findContours(mat, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    contours = contours[0] if len(contours) == 2 else contours[1]
    boxes = [cv.boundingRect(c) for c in contours]
    boxes= rejectChildBoxes(boxes)
    return boxes

def drawBoxes(img, boxes):
    img = img.copy()
    for box in boxes:
        x,y,w,h = box
        cv.rectangle(img, (x,y),(x+w, y+h), 2)
    return img

def imageToString(img):
    return pytesseract.image_to_string(img, config='--psm 6')

def sortBoxesTopToBottom(boxes):
    boxes = boxes.copy()
    boxes.sort(key=lambda b: b[1])
    return boxes

def isTextBoxByAspectRatio(img):
    h,w,_ = img.shape
    return w/h > TEXT_BOX_MIN_ASPECT_RATIO

def convertToImageOrText(img):
    if isTextBoxByAspectRatio(img):
        return imageToString(img)
    else:
        return img

def matrixToImage(mat):
    return Image.fromarray(mat)

    # textBoxes = [box for box in boxes if isTextBoxByAspectRatioFunc(
    #     TEXT_BOX_MIN_ASPECT_RATIO)(box)]
    # imageBoxes = [box for box in boxes if not isTextBoxByAspectRatioFunc(
    #     TEXT_BOX_MIN_ASPECT_RATIO)(box)]

def cropROI(mat):
    def fn(box):
        x,y,w,h = box
        return mat [y:y+h,x:x+w]
    return fn

if __name__ == "__main__":
    pages = pdf2image.convert_from_path('testpdf.pdf')
    pages = pages[START_PAGE-1:END_PAGE+1]
    page = pages[-1]
    mat = np.asarray(page)
    boxes = getROIsFromImage(mat)
    boxes = sortBoxesTopToBottom(boxes)
    print(boxes)
    # def leftBoxes(box):
    #     x,y,w,h = box
    #     return x<100
    # boxes = filter(leftBoxes, boxes)
    pageWithROIBoxes = drawBoxes(mat, boxes)
    ROIs = map(cropROI(mat), boxes)
    outputStr=""
    cv.imshow('new', pageWithROIBoxes)
    for roi in ROIs:
        outputStr = outputStr + imageToString(roi)
        print(outputStr)
    cv.waitKey(0)
    cv.destroyAllWindows()
    exit()