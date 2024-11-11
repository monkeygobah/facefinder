import os
# from symbol import file_input
import cv2
from PIL import Image
import matplotlib.pyplot as plt
import shutil
import numpy as np
# from tkinter import *
# from tkinter import ttk
# from tkinter import filedialog
from PIL import Image, ExifTags, ImageOps
from exif import Image as exim
import piexif
import time
# import re
from PIL.ExifTags import TAGS
import threading



start = time.time()


def cleaner(home):    #remove all special characters from directories and subdirectories
    for i in range(3):
        for root, dirs, files in os.walk(home):
            for dir in dirs:
                if 'DS' not in dir:
                    try:
                        r = dir.replace(".","_").replace(" ","").replace(",","_").replace("(","_").replace(")","_").replace("!","_").replace("@","_")
                        os.rename(os.path.join(root, dir),os.path.join(root, r))
                    except OSError as error :
                        dir1 = dir+'dup_name'
                        r = dir1.replace(".","_").replace(" ","").replace(",","_").replace("(","_").replace(")","_").replace("!","_").replace("@","_")
                        os.rename(os.path.join(root, dir),os.path.join(root, r))

    #remove all special characters from files
    for i in range(3):
        for root, dirs, files in os.walk(home, followlinks=True):
            for file in files:
                if 'DS' not in file:
                    interest = file[:-4]
                    end = file[-4:]
                    r = interest.replace(".","_").replace(" ","").replace(",","_").replace("(","_").replace(")","_").replace("!","_").replace("@","_")
                    r = r + end
                    os.rename(os.path.join(root, file),os.path.join(root, r))


def correct_orientation_and_save(image_path, image, exif):
    """
    Correct the orientation of the image based on EXIF data and save it.
    """
    img = Image.open(image_path)
    if "exif" in img.info:
        exif_dict = piexif.load(img.info["exif"])
        if piexif.ImageIFD.Orientation in exif_dict["0th"]:
            orientation = exif_dict["0th"].pop(piexif.ImageIFD.Orientation)
            exif_bytes = piexif.dump(exif_dict)

            if orientation == 2:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 3:
                img = img.rotate(180)
            elif orientation == 4:
                img = img.rotate(180).transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 5:
                img = img.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 6:
                img = img.rotate(360, expand=True)
            elif orientation == 7:
                img = img.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 8:
                img = img.rotate(360, expand=True)

            img.save(image_path, exif=exif_bytes)

def writeOut(path_list, output_folder, orig_path, image, home_dir, file, bad_counter):
    """
    Write out detected files and store in a new, unique folder if it doesn't exist.
    """
    split_path_home = os.path.normpath(home_dir)
    working_subdir = split_path_home.split(os.sep)[-1]

    # Determine the depth level based on the working_subdir position
    depth_level = None
    for i in range(1, 6):
        if working_subdir == path_list[-i]:
            depth_level = i
            break

    if depth_level is None:
        print("Working directory not found in path list.")
        return


    # Construct the directory path
    dir_path = os.path.join(output_folder, *path_list[-(depth_level - 1):-1])
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    # Save the image
    data_path_image = os.path.join(dir_path, file)
    
    # make sure no false bounding boxes slip through
    if image is None or image.size == 0:
        print(f"Error: Trying to write an empty image for file: {file}")
        bad_counter +=1
        return    
    else:
        
        cv2.imwrite(data_path_image, image)

        try:
            # Load image from source and extract EXIF
            image = Image.open(orig_path)
            exif = image.info['exif']

            # Correct orientation and save
            correct_orientation_and_save(data_path_image, image, exif)

        except (RuntimeError, TypeError, KeyError, NameError, FileNotFoundError):
            print(f'No EXIF data found for {file}')
            pass

def adjust_bbox(h, w, y, x, image_width, image_height, increase_by=.2):
    """
    Adjust the bounding box and check if eye rectangles overlap.
    Returns the new bounding box coordinates and overlap status.
    """

    extend_up = min(h * increase_by, y)
    extend_down = min(h * increase_by, image_height - y - h)
    extend_left = min(w * increase_by, x)
    extend_right = min(w * increase_by, image_width - x - w)

    extend_y = y + h + extend_down
    extend_x = x + w + extend_right
    new_y = y - extend_up
    new_x = x - extend_left

    return (int(new_y), int(extend_y), int(new_x), int(extend_x))

side_face = cv2.CascadeClassifier('haarcascade_frontalface_alt.xml')
eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_alt.xml')

def threaded_main_loop(home, good_out, bad_out,stop_event,  eye_min_neighbors, face_min_neighbors):
    main_loop(home, good_out, bad_out,stop_event, eye_min_neighbors, face_min_neighbors)



def main_loop(home, good_out, bad_out, stop_event, eye_min_neighbors = 8, face_min_neighbors = 0):
    start_time = time.time()
    total_images = 0
    processed_images = 0
    bad_counter = 0
    
    cleaner(home)
    # main loop
    for root, dirs, files in os.walk(home):

        for file in files:
            if stop_event.is_set():
                break
            print(f'Processing {file}')
            if file.lower().endswith(('.jpg', '.png', '.jpeg')):
                total_images += 1

                path = os.path.join(root, file)
                split_path = os.path.normpath(path)
                path_list = split_path.split(os.sep)

                img = cv2.imread(path)
            
                if img is None:
                    continue

                grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                copy = img.copy()
            
                faces = face_cascade.detectMultiScale(grey, scaleFactor=1.1, minNeighbors=face_min_neighbors, minSize=(30, 30))
            
                good_detection_found = False
                print(len(faces))
                
                height, width, _ = img.shape 

                
                for (x, y, w, h) in faces:
                    roi_grey = grey[y:y+h, x:x+w]
                    eyes = eye_cascade.detectMultiScale(roi_grey, scaleFactor=1.2, minNeighbors=eye_min_neighbors)
                    
                    bbox = adjust_bbox(h, w, y, x, width, height)
                    if len(eyes)>=2:
                        good_detection_found = True
                        processed_images += 1
                        face_save = img[bbox[0]:bbox[1], bbox[2]:bbox[3]]
                        writeOut(path_list, good_out, path, face_save, home, file, bad_counter)
                        break
                    
                if not good_detection_found:
                    writeOut(path_list, bad_out, path, img, home, file, bad_counter)   

    end_time = time.time()
    time_taken = end_time - start_time
    
    # print(time_taken)
    # print(total_images)
    # print(processed_images)
    print(f'Images Not processed: {bad_counter}')
    return processed_images, total_images, time_taken

