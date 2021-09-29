from tkinter import *
from PIL import ImageTk, Image
import os
import cv2

flip = True

root = Tk()

root.geometry("805x600")

fileNames = []

for r, dirs, files in os.walk("./toLabel"):
    for filename in files:
        fileNames.append(filename)


if len(fileNames) == 0:
    print("No more files to sort")
    exit()


firstImage = Image.open(
    "toLabel/" + fileNames[0])

if flip:
    firstImage = firstImage.rotate(90)


width, height = firstImage.size

firstImage = firstImage.resize((round(500/height*width), round(500)))

firstImage = ImageTk.PhotoImage(firstImage)

bgImage = Label(root, image=firstImage)
bgImage.pack()

e1 = Entry(root)
e1.insert(-1, '03260')
e1.pack()


idx = 0


def nextImage(idx):
    print("INDEX: ", idx)
    if idx > len(fileNames) - 1:
        print("No more files to sort")
        exit()

    thisImage = Image.open(
        "toLabel/" + fileNames[idx])

    if flip:
        thisImage = thisImage.rotate(90)

    width, height = thisImage.size

    print(thisImage.size)

    thisImage = thisImage.resize((round(500/height*width), round(500)))

    thisImage = ImageTk.PhotoImage(thisImage)

    bgImage.configure(image=thisImage)
    bgImage.image = thisImage

    # e1.delete(0, END)


def saveImage(idx):
    with open("imageList.txt", "a") as f:
        f.write(fileNames[idx] + " : " + e1.get() + "\n")
    imgLoad = cv2.imread("toLabel/" + fileNames[idx])

    if flip:
        imgLoad = cv2.rotate(imgLoad, cv2.ROTATE_90_COUNTERCLOCKWISE)

    cv2.imwrite("labelled/" + fileNames[idx], imgLoad)
    os.remove("toLabel/" + fileNames[idx])


def key_pressed(event):
    global idx
    if event.keycode == 13:
        saveImage(idx)
        print("Saved", fileNames[idx], "as", e1.get())
        idx += 1
        nextImage(idx)


root.bind("<KeyPress>", key_pressed)

root.mainloop()
