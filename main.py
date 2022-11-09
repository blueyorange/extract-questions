from tokenize import String
from PIL import Image
import cv2 as cv
import numpy as np
import pytesseract
import pdf2image
import re

TEXT_BOX_MIN_ASPECT_RATIO = 3
START_PAGE = 2
END_PAGE = 2
DILATION_KERNEL = (3, 5)


class Item:
    def __init__(self, image, text):
        self.img = image
        self.txt = text


class Question:
    items = []
    options = {}

    def addItem(self, image):
        self.items.append(Item(image))

    def addOption(self, key, value):
        # key should be A, B, C, or D
        self.options[key] = value


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
    boxes = rejectChildBoxes(boxes)
    return boxes


def drawBoxes(img, boxes):
    img = img.copy()
    for box in boxes:
        x, y, w, h = box
        cv.rectangle(img, (x, y), (x+w, y+h), 2)
    return img


def imageToString(img):
    return pytesseract.image_to_string(img, config=f'--psm 6')


def sortBoxesTopToBottom(boxes):
    boxes = boxes.copy()
    boxes.sort(key=lambda b: b[1])
    return boxes


def sortBoxesLeftToRight(boxes):
    boxes = boxes.copy()
    boxes.sort(key=lambda b: b[0])
    return boxes


def sortBoxes(boxes):
    boxes = boxes.copy()
    boxes.sort(key=lambda b: b[0]+b[1])
    return boxes


def isTextBoxByAspectRatio(img):
    h, w, _ = img.shape
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


def createCropper(mat):
    def fn(box):
        x, y, w, h = box
        return mat[y:y+h, x:x+w]
    return fn


def nestBoxesByLine(boxes):
    sortedVertically = sortBoxesTopToBottom(boxes)
    nestedList = []
    currentLine = []
    for i in range(len(boxes)-1):
        print(nestedList)
        currentLine.append(boxes[i])
        y1 = boxes[i][1]
        h1 = boxes[i][3]
        y2 = boxes[i+1][1]
        h2 = boxes[i+1][3]
        if y2 > (y1+h1) or y1 > (y2+h2):
            print("newline")
            currentLine = sortBoxesLeftToRight(currentLine)
            nestedList.append(currentLine)
            currentLine = []
        else:
            print("same line")
    return nestedList


def processPage(page):
    mat = np.asarray(page)
    boxes = getROIsFromImage(mat)
    boxes = sortBoxesTopToBottom(boxes)
    lines = nestBoxesByLine(boxes)
    newQuestionRe = '^\d+$'
    endQuestionRe = 'Your answer'
    optionLetterRe = '[ABCD]'
    questions = []
    capture = False
    optionLetter = ""
    # remove first line (page number)
    output = []
    for boxes in lines:
        items = []
        for box in boxes:
            x, y, w, h = box
            crop = mat[y:y+h, x:x+w]
            text = imageToString(crop)
            item = Item(crop, text)
            items.append(item)
        output.append(items)
    return output
    exit()


if __name__ == "__main__":
    pages = pdf2image.convert_from_path('testpdf.pdf')
    pages = pages[START_PAGE-1:END_PAGE]
    page = pages[0]
    output = processPage(page)
    n = 0
    with open('test.md', 'a') as f:
        for line in output:
            for item in line:
                n += 1
                img = Image.fromarray(item.img)
                imgPath = f'./Images/Image{n}.png'
                img.save(imgPath)
                f.write(f'![{item.txt}]({imgPath}) ')
            f.write('\n\n')
