"""A subservice for redaction."""

import csv
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from mtcnn import MTCNN

from processing.utils.common import seconds_to_datetime as s2d
from processing.utils.local import filename
from processing.utils.opencvapi import draw_bounding_box, red, rescale
from processing.utils.paths import frontal_haar, lp_caffemodel, lp_prototxt

face_detector = MTCNN(min_face_size=20)
pixel_means = [0.406, 0.456, 0.485]
pixel_stds = [0.225, 0.224, 0.229]
pixel_scale = 255.0

convnet = cv2.dnn.readNetFromCaffe(lp_prototxt, lp_caffemodel)


def pixelate(roi) -> np.ndarray:
  """Pixelate ROIs like in ..."""
  # You can find the reference code here:
  # https://www.pyimagesearch.com/2020/04/06/blur-and-anonymize-faces-with-opencv-and-python/
  height, width, _ = roi.shape
  x_steps = np.linspace(0, width, 8, dtype='int')
  y_steps = np.linspace(0, height, 8, dtype='int')

  # Looping over blocks in both X & Y direction.
  for y_idx in range(1, len(y_steps)):
    for x_idx in range(1, len(x_steps)):
      x0 = x_steps[x_idx - 1]
      y0 = y_steps[y_idx - 1]
      x1 = x_steps[x_idx]
      y1 = y_steps[y_idx]
      _roi = roi[y0:y1, x0:x1]
      B, G, R = [int(idx) for idx in cv2.mean(_roi)[:3]]
      cv2.rectangle(roi, (x0, y0), (x1, y1), (B, G, R), -1)

  # Pixelated blurred roi
  return roi


def redact_faces(file: str,
                 log: logging.Logger,
                 use_ml_model: bool = True,
                 smooth_blur: bool = True,
                 resize: bool = False,
                 resize_width: int = 640,
                 debug_mode: bool = False) -> Optional[str]:
  """Apply face redaction in video using MTCNN."""
  x0, y0, x1, y1 = 0, 0, 0, 0
  boxes, temp_csv_entries = [], []
  face_count = {}

  directory = os.path.join(os.path.dirname(file), f'{Path(file).stem}_faces')

  if not os.path.isdir(directory):
    os.mkdir(directory)

  temp_file = os.path.join(directory, f'{Path(file).stem}.mp4')

  if debug_mode:
    log.info('Debug mode - Enabled.')

  log.info(f'Redacting faces from "{os.path.basename(file)}"...')

  try:
    stream = cv2.VideoCapture(file)
    fps = stream.get(cv2.CAP_PROP_FPS)
    width, height = (int(stream.get(cv2.CAP_PROP_FRAME_WIDTH)),
                     int(stream.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    if resize:
      width, height = resize_width, int(height * (resize_width / float(width)))

    save = cv2.VideoWriter(filename(temp_file, 1),
                           cv2.VideoWriter_fourcc(*'mp4v'), fps,
                           (width, height))

    while True:
      valid_frame, frame = stream.read()

      if not valid_frame:
        break

      if frame is None:
        break

      if resize:
        frame = rescale(frame, resize_width)

      height, width = frame.shape[:2]

      if use_ml_model:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_detector.detect_faces(rgb)

        for face_idx in faces:
            # Considering detections which have confidence score higher than the
            # set threshold.
          if face_idx['confidence'] > 0.75:
            x0, y0, x1, y1 = face_idx['box']
            x0, y0 = abs(x0), abs(y0)
            x1, y1 = x0 + x1, y0 + y1

            face = frame[y0:y1, x0:x1]

            if debug_mode:
              draw_bounding_box(frame, (x0, y0), (x1, y1), red)
            try:
              if smooth_blur:
                frame[y0:y1, x0:x1] = cv2.GaussianBlur(frame[y0:y1, x0:x1],
                                                       (49, 49), 0)
              else:
                frame[y0:y1, x0:x1] = pixelate(face)
            except Exception:
              pass

          boxes.append([x1, y1])
          face_occurence = s2d(int(stream.get(cv2.CAP_PROP_POS_MSEC) / 1000))

          if face_occurence not in face_count.keys():
            face_count[face_occurence] = []

          face_count[face_occurence].append(len(boxes))
      else:
        face_cascade = cv2.CascadeClassifier(frontal_haar)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray_frame, 1.3, 5)

        for (x0, y0, x1, y1) in faces:
          if debug_mode:
            draw_bounding_box(frame, (x0, y0), (x0 + x1, y0 + y1), red)
          try:
            if smooth_blur:
              frame[y0:(y0 + y1),
                    x0:(x0 + x1)] = cv2.GaussianBlur(frame[y0:(y0 + y1),
                                                           x0:(x0 + x1)],
                                                     (21, 21), 0)
            else:
              frame[y0:(y0 + y1),
                    x0:(x0 + x1)] = pixelate(frame[y0:(y0 + y1), x0:(x0 + x1)])
          except Exception:
            pass
          boxes.append([x1, y1])
          face_occurence = s2d(int(stream.get(cv2.CAP_PROP_POS_MSEC) / 1000))

          if face_occurence not in face_count.keys():
            face_count[face_occurence] = []

          face_count[face_occurence].append(len(boxes))

      boxes = []
      save.write(frame)

      if debug_mode:
        cv2.imshow('Video Processing Engine - Redaction', frame)

      if cv2.waitKey(1) & 0xFF == int(27):
        break

    stream.release()
    save.release()
    cv2.destroyAllWindows()

    # log.info('Logging detections into a CSV file...')
    # with open(os.path.join(directory, f'{Path(file).stem}.csv'), 'a',
    #           encoding="utf-8") as csv_file:
    #   _file = csv.writer(csv_file, quoting=csv.QUOTE_MINIMAL)
    #   _file.writerow(['Max no. of detections per second', 'Time frame'])
    #   temp_csv_entries = [(max(v), k) for k, v in face_count.items()]
    #   _file.writerows(temp_csv_entries)

    log.info('Applying H264 encoding for bypassing browser issues...')
    os.system(f'ffmpeg -loglevel error -y -i {filename(temp_file, 1)} -vcodec '
              f'libx264 {temp_file}')

    shutil.move(temp_file, file)

    if len(os.listdir(directory)) > 0:
      shutil.rmtree(directory)
    else:
      os.rmdir(directory)

    return file
  except Exception as error:
    log.exception(error)


def redact_license_plates(file: str,
                          log: logging.Logger,
                          smooth_blur: bool = True,
                          resize: bool = False,
                          resize_width: int = 640,
                          debug_mode: bool = False) -> Optional[str]:
  """Redact license plates in video using CaffeModel."""
  x0, y0, x1, y1 = 0, 0, 0, 0
  directory = os.path.join(os.path.dirname(file), f'{Path(file).stem}_license')

  if not os.path.isdir(directory):
    os.mkdir(directory)

  temp_file = os.path.join(directory, f'{Path(file).stem}.mp4')

  if debug_mode:
    log.info('Debug mode - Enabled.')

  log.info(f'Redacting license plates from "{os.path.basename(file)}"...')

  try:
    stream = cv2.VideoCapture(file)
    fps = stream.get(cv2.CAP_PROP_FPS)
    width, height = (int(stream.get(cv2.CAP_PROP_FRAME_WIDTH)),
                     int(stream.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    if resize:
      width, height = resize_width, int(height * (resize_width / float(width)))

    save = cv2.VideoWriter(filename(temp_file, 1),
                           cv2.VideoWriter_fourcc(*'mp4v'), fps,
                           (width, height))

    while True:
      valid_frame, frame = stream.read()

      if not valid_frame:
        break

      if frame is None:
        break

      if resize:
        frame = rescale(frame, resize_width)

      height, width = frame.shape[:2]

      bkp_frame = frame.copy()

      tensor = np.zeros((1, 3, bkp_frame.shape[0], bkp_frame.shape[1]))
      tmp_frame = bkp_frame.astype(np.float32)
      for t_i in range(3):
        tensor[0, t_i, :, :] = ((tmp_frame[:, :, 2 - t_i] /
                                 pixel_scale - pixel_means[2 - t_i]) /
                                pixel_stds[2 - t_i])
      convnet.setInput(tensor)
      detected_license_plate = convnet.forward()

      for idx in range(0, detected_license_plate.shape[2]):
        if detected_license_plate[0, 0, idx, 2] > 0.6:
          coords = detected_license_plate[0, 0, idx, 3:7] * np.array([width,
                                                                      height,
                                                                      width,
                                                                      height])
          x0, y0, x1, y1 = coords.astype('int')
          adj = int(x1 - x0) * 0.1

          x0 = x0 - adj
          y0 = y0 - adj
          x1 = x1 + adj
          y1 = y1 + adj

          x0, y0, x1, y1 = tuple(map(int, (x0, y0, x1, y1)))

          face = bkp_frame[y0:y1, x0:x1]

          if debug_mode:
            draw_bounding_box(frame, (x0, y0), (x1, y1), red)
          try:
            if smooth_blur:
              frame[y0:y1, x0:x1] = cv2.GaussianBlur(frame[y0:y1, x0:x1],
                                                     (49, 49), 0)
            else:
              frame[y0:y1, x0:x1] = pixelate(face)
          except Exception:
            pass

      save.write(frame)

      if debug_mode:
        cv2.imshow('Video Processing Engine - Redaction', frame)

      if cv2.waitKey(1) & 0xFF == int(27):
        break

    stream.release()
    save.release()
    cv2.destroyAllWindows()

    log.info('Applying H264 encoding for bypassing browser issues...')
    os.system(f'ffmpeg -loglevel error -y -i {filename(temp_file, 1)} -vcodec '
              f'libx264 {temp_file}')

    shutil.move(temp_file, file)

    if len(os.listdir(directory)) > 0:
      shutil.rmtree(directory)
    else:
      os.rmdir(directory)

    return file
  except Exception as error:
    log.exception(error)
