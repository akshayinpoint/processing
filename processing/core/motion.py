import csv
import logging
import os
import shutil
import time
from collections import deque
from itertools import repeat
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Union

import cv2
import imutils
import numpy as np

from processing.core.concate import concate_videos
from processing.utils.common import seconds_to_datetime as s2d
from processing.utils.local import filename
from processing.utils.opencvapi import (disconnect, draw_bounding_box, green,
                                        rescale, temp_list)
from processing.utils.paths import tf_caffemodel, tf_prototxt

CLASSES = ['background', 'aeroplane', 'bicycle', 'bird', 'boat',
           'bottle', 'bus', 'car', 'cat', 'chair', 'cow', 'diningtable',
           'dog', 'horse', 'motorbike', 'person', 'pottedplant', 'sheep',
           'sofa', 'train', 'tvmonitor']

new_color = list(repeat((np.random.random(size=3) * 256), len(CLASSES)))


class KeyClipWriter:
  def __init__(self, bufSize=64, timeout=1.0):
    # store the maximum buffer size of frames to be kept
    # in memory along with the sleep timeout during threading
    self.bufSize = bufSize
    self.timeout = timeout

    # initialize the buffer of frames, queue of frames that
    # need to be written to file, video writer, writer thread,
    # and boolean indicating whether recording has started or not
    self.frames = deque(maxlen=bufSize)
    self.Q = None
    self.writer = None
    self.thread = None
    self.recording = False

  def update(self, frame):
    # update the frames buffer
    self.frames.appendleft(frame)

    # if we are recording, update the queue as well
    if self.recording:
      self.Q.put(frame)

  def start(self, outputPath, fourcc, fps):
    # indicate that we are recording, start the video writer,
    # and initialize the queue of frames that need to be written
    # to the video file
    self.recording = True
    self.writer = cv2.VideoWriter(outputPath, fourcc, fps,
                                  (self.frames[0].shape[1],
                                   self.frames[0].shape[0]), True)
    self.Q = Queue()
    # loop over the frames in the deque structure and add them
    # to the queue
    for i in range(len(self.frames), 0, -1):
      self.Q.put(self.frames[i - 1])

    # start a thread write frames to the video file
    self.thread = Thread(target=self.write, args=())
    self.thread.daemon = True
    self.thread.start()

  def write(self):
    # keep looping
    while True:
      # if we are done recording, exit the thread
      if not self.recording:
        return

      # check to see if there are entries in the queue
      if not self.Q.empty():
        # grab the next frame in the queue and write it
        # to the video file
        frame = self.Q.get()
        self.writer.write(frame)

      # otherwise, the queue is empty, so sleep for a bit
      # so we don't waste CPU cycles
      else:
        time.sleep(self.timeout)

  def flush(self):
    # empty the queue by flushing all remaining frames to file
    while not self.Q.empty():
      frame = self.Q.get()
      self.writer.write(frame)

  def finish(self):
    # indicate that we are done recording, join the thread,
    # flush all remaining frames in the queue to file, and
    # release the writer pointer
    self.recording = False
    self.thread.join()
    self.flush()
    self.writer.release()


def track_motion(file: str,
                 log: logging.Logger,
                 track_what: Union[list, str] = None,
                 precision: int = 1500,
                 resize: bool = False,
                 resize_width: int = 640,
                 debug_motion: bool = False,
                 debug_object: bool = False) -> str:
  """Track motion in the video using Background Subtraction method."""
  kcw = KeyClipWriter(bufSize=32)
  consec_frames, x0, y0, x1, y1, count = 0, 0, 0, 0, 0, 0

  temp_obj_count = {}
  motion_count = {}

  boxes, temp_csv_entries, obj_csv_entries = [], [], []
  directory = os.path.join(os.path.dirname(file), f'{Path(file).stem}_motion')
  net = cv2.dnn.readNetFromCaffe(tf_prototxt, tf_caffemodel)

  if not os.path.isdir(directory):
    os.mkdir(directory)

  temp_file = os.path.join(directory, f'{Path(file).stem}.mp4')
  file_idx = 1

  if debug_motion or debug_object:
    log.info('Debug mode - Enabled.')
  log.info(f'Analyzing motion for "{os.path.basename(file)}"...')
  log.warning('Extracting CSV report is disabled for now...')

  try:
    stream = cv2.VideoCapture(file)
    fps = stream.get(cv2.CAP_PROP_FPS)
    first_frame = None

    while True:
      valid_frame, frame = stream.read()

      if not valid_frame:
        break

      if frame is None:
        break

      if resize:
        frame = rescale(frame, resize_width)

      update_frame = True
      gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)
      height, width, _ = frame.shape

      if first_frame is None:
        first_frame = gray_frame
        continue

      blob = cv2.dnn.blobFromImage(frame, 0.007843, (width, height), 127.5)
      net.setInput(blob)
      detected_objs = net.forward()
      count = 1

      if track_what is not None:
        for idx in range(0, detected_objs.shape[2]):
          if detected_objs[0, 0, idx, 2] > 0.3:
            coords = detected_objs[0, 0, idx, 3:7] * np.array([width, height,
                                                               width, height])
            x0, y0, x1, y1 = coords.astype('int')
            obj_idx = int(detected_objs[0, 0, idx, 1])

            if isinstance(track_what, str):
              if CLASSES[obj_idx] == track_what:
                if debug_object:
                  draw_bounding_box(frame, (x0, y0), (x1, y1), green)

                count += 1

                obj_occurence = s2d(
                    int(stream.get(cv2.CAP_PROP_POS_MSEC) / 1000))

                if obj_occurence not in temp_obj_count.keys():
                  temp_obj_count[obj_occurence] = []

                temp_obj_count[obj_occurence].append(count)

            elif isinstance(track_what, list):
              if CLASSES[obj_idx] in track_what:
                _idx = 0 if obj_idx > 8 else obj_idx

                if obj_idx > 8:
                  _idx -= 8
                else:
                  _idx = obj_idx

                if debug_object:
                  draw_bounding_box(frame, (x0, y0), (x1, y1), temp_list[_idx])

                count += 1

                obj_occurence = s2d(
                    int(stream.get(cv2.CAP_PROP_POS_MSEC) / 1000))

                if obj_occurence not in temp_obj_count.keys():
                  temp_obj_count[obj_occurence] = []

                temp_obj_count[obj_occurence].append(count)

      frame_delta = cv2.absdiff(first_frame, gray_frame)
      threshold = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
      threshold = cv2.dilate(threshold, None, iterations=2)
      contours = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL,
                                  cv2.CHAIN_APPROX_SIMPLE)
      contours = imutils.grab_contours(contours)

      for contour in contours:
        if cv2.contourArea(contour) < precision:
          continue

        if debug_motion:
          (x0, y0, x1, y1) = cv2.boundingRect(contour)
          draw_bounding_box(frame, (x0, y0), (x0 + x1, y0 + y1))

        consec_frames = 0

        if not kcw.recording:
          kcw.start(filename(temp_file, file_idx),
                    cv2.VideoWriter_fourcc(*'mp4v'), fps)
          file_idx += 1

        boxes.append([x1, y1])
        motion_occurence = s2d(int(stream.get(cv2.CAP_PROP_POS_MSEC) / 1000))

        if motion_occurence not in motion_count.keys():
          motion_count[motion_occurence] = []

        motion_count[motion_occurence].append(len(boxes))

      boxes = []

      if update_frame:
        consec_frames += 1

      kcw.update(frame)

      if kcw.recording and consec_frames == 32:
        log.info('Extracting buffered portion of video with detected motion...')
        kcw.finish()

      if debug_motion or debug_object:
        cv2.imshow('Video Processing Engine - Motion Detection', frame)

      if cv2.waitKey(1) & 0xFF == int(27):
        disconnect(stream)

    if kcw.recording:
      kcw.finish()

    if len(os.listdir(directory)) < 1:
      return file

    concate_temp = concate_videos(directory, delete_old_files=False)
    # with open(os.path.join(directory, f'{Path(file).stem}_motion.csv'), 'a',
    #           encoding="utf-8") as csv_file:
    #   log.info('Logging detections into a CSV file.')
    #   _file = csv.writer(csv_file, quoting=csv.QUOTE_MINIMAL)
    #   _file.writerow(['Max no. of detections per second', 'Time frame'])
    #   temp_csv_entries = [(max(v), k) for k, v in motion_count.items()]
    #   _file.writerows(temp_csv_entries)

    # if track_what:
    #   with open(os.path.join(directory, f'{Path(file).stem}_object.csv'), 'a',
    #             encoding="utf-8") as obj_csv_file:
    #     log.info('Logging objects into a CSV file.')
    #     _file = csv.writer(obj_csv_file, quoting=csv.QUOTE_MINIMAL)
    #     _file.writerow(['Max no. of detections per second', 'Time frame'])
    #     obj_csv_entries = [(max(ov), ok) for ok, ov in temp_obj_count.items()]
    #     _file.writerows(obj_csv_entries)

    if concate_temp:
      if os.path.isfile(concate_temp):
        log.info('Applying H264 encoding for bypassing browser issues...')
        os.system(f'ffmpeg -loglevel error -y -i {concate_temp} -vcodec '
                  f'libx264 {temp_file}')
        log.info('Cleaning up archived files...')

    shutil.move(temp_file, file)

    if len(os.listdir(directory)) > 0:
      shutil.rmtree(directory)
    else:
      os.rmdir(directory)

    return file
  except Exception as error:
    log.critical(f'Something went wrong because of {error}')
    raise error
