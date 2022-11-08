from tokenize import String
from PIL import Image
import cv2 as cv
import numpy as np
import pytesseract
import pdf2image
import re

TEXT_BOX_MIN_ASPECT_RATIO = 3
START_PAGE = 4
END_PAGE = 4
DILATION_KERNEL = (3,4)
CHARACTER_AREA = DILATION_KERNEL[0]*DILATION_KERNEL[1]

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
            DILATION_KERNEL, np.uint8), iterations=5)
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

def imageToString(img, psm=6):
    return pytesseract.image_to_string(img, config=f'--psm {psm}')

def sortBoxesTopToBottom(boxes):
    boxes = boxes.copy()
    boxes.sort(key=lambda b: b[1])
    return boxes

def sortBoxesLeftToRight(boxes):
    boxes = boxes.copy()
    boxes.sort(key=lambda b: b[0])
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

def getQuestionNumberBoxes(mat, boxes):
    sorted = sortBoxesLeftToRight(boxes)
    questionNumberBoxes = []
    for box in sorted:
        cropper = cropROI(mat)
        crop = cropper(box)
        text = imageToString(crop, psm=10).strip()
        if re.match('^\d+$', text):
            questionNumberBoxes.append(box)
        else: 
            return questionNumberBoxes

def processPage(page):
    mat = np.asarray(page)
    boxes = getROIsFromImage(mat)
    questionNumberBoxes = getQuestionNumberBoxes(mat, boxes)
    crop = cropROI(mat)
    pageWithROIBoxes = drawBoxes(mat, boxes)
    crops = map(cropROI(mat), boxes)
    boxes = sortBoxesTopToBottom(boxes)
    outputStr=""
    cv.imshow('new', pageWithROIBoxes)
    for crop in crops:
        outputStr = outputStr + imageToString(crop)
        print(outputStr)
    cv.waitKey(0)
    cv.destroyAllWindows()
    exit()
    
if __name__ == "__main__":
    pages = pdf2image.convert_from_path('testpdf.pdf')
    pages = pages[START_PAGE-1:END_PAGE+1]
    page = pages[-1]
    processPage(page)
