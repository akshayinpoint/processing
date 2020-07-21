"""Utility for defining the necessary paths."""

import os

# Parent directory path. All the references will be made relatively
# using the below defined parent directory.
parent_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# OpenCV models path
FACE_PROTOTXT = 'deploy.prototxt.txt'
FACE_CAFFEMODEL = 'res10_300x300_ssd_iter_140000.caffemodel'
TEXT_EAST_DETECTOR = 'frozen_east_text_detection.pb'
FRONTAL_HAAR = 'haarcascade_frontalface_default.xml'
FRONTAL_HAAR_2 = 'haarcascade_frontalface_alt2.xml'
PROFILE_HAAR = 'haarcascade_profileface.xml'
TF_PROTOTXT = 'tf_ssd_deploy.prototxt'
TF_CAFFEMODEL = 'tf_ssd_deploy.caffemodel'
LP_PROTOTXT = 'mssd512_voc.prototxt'
LP_CAFFEMODEL = 'mssd512_voc.caffemodel'

# Reference video
REFERENCE_VIDEO = 'reference.mkv'

# Models used in the video processing engine.
models = os.path.join(parent_path, 'processing/models')

# Path where all the downloaded files are stored.
videos = os.path.join(parent_path, 'videos')

# Other paths
logs = os.path.join(parent_path, 'logs')

caffemodel = os.path.join(models, FACE_CAFFEMODEL)
prototxt = os.path.join(models, FACE_PROTOTXT)
tf_caffemodel = os.path.join(models, TF_CAFFEMODEL)
tf_prototxt = os.path.join(models, TF_PROTOTXT)
lp_caffemodel = os.path.join(models, LP_CAFFEMODEL)
lp_prototxt = os.path.join(models, LP_PROTOTXT)
frontal_haar = os.path.join(models, FRONTAL_HAAR)
frontal_haar_2 = os.path.join(models, FRONTAL_HAAR_2)
profile_haar = os.path.join(models, PROFILE_HAAR)
reference_video = os.path.join(models, REFERENCE_VIDEO)
