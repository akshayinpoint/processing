"""Utility for making convenient use of OpenCV."""

from typing import Any, List, Optional, Tuple, Union

import cv2
import numpy as np

red = [48, 59, 255]
blue = [255, 122, 0]
green = [100, 217, 76]
yellow = [0, 204, 255]
orange = [0, 149, 255]
teal = [250, 200, 90]
purple = [214, 86, 88]
pink = [85, 45, 255]
white = [255, 255, 255]
black = [0, 0, 0]

temp_list = [red, blue, green, yellow, orange, teal, purple, pink, black]


def rescale(frame: np.ndarray,
            width: Optional[int] = 300,
            height: Optional[int] = None,
            interpolation: Optional[Any] = cv2.INTER_AREA) -> np.ndarray:
  """Rescale the frame.

  Rescale the stream to a desirable size. This is required before
  performing the necessary operations.

  Args:
    frame: Numpy array of the image frame.
    width: Width (default: None) to be rescaled to.
    height: Height (default: None) to be rescaled to.
    interpolation: Interpolation algorithm (default: INTER_AREA) to be
                    used.

  Returns:
    Rescaled numpy array for the input frame.
  """
  dimensions = None
  frame_height, frame_width = frame.shape[:2]
  # If both width & height are None, then return original frame size.
  # No rescaling will be done in that case.
  if width is None and height is None:
    return frame

  if width and height:
    dimensions = (width, height)
  elif width is None:
    ratio = height / float(frame_height)
    dimensions = (int(frame_width * ratio), height)
  else:
    ratio = width / float(frame_width)
    dimensions = (width, int(frame_height * ratio))

  return cv2.resize(frame, dimensions, interpolation=interpolation)


def disconnect(stream: np.ndarray) -> None:
  """Disconnect stream and exit the program."""
  stream.release()
  cv2.destroyAllWindows()


def draw_bounding_box(frame: np.ndarray,
                      x0_y0: Tuple,
                      x1_y1: Tuple,
                      color: List = green,
                      alpha: Union[float, int] = 0.3,
                      thickness: int = 2) -> None:
  """Draw bounding box using the Numpy tuple.
  Draws the bounding box around the detection using tuple of numpy
  coordinates.
  Args:
    frame: Numpy array of the image frame.
    x0_y0: Tuple of top left coordinates.
    x1_y1: Tuple of bottom right coordinates.
    color: Bounding box (default: yellow) color.
    alpha: Opacity of the detected region overlay.
    thickness: Thickness (default: 1) of the bounding box.
  Note:
    This method can be used for drawing the bounding boxes around
    objects whose coordinates are derived from a Machine Learning based
    model.
    * For Haar based detections, use the below settings -
        draw_bounding_box(frame, x0, y0, (x1 - x0), (y1 - y0))
    * For adding the detection name, add the below settings - 
        (x0, y0), (x1, y1) = x0_y0, x1_y1
        cv2.rectangle(frame, (x0, y1), (x1, y1 + 20), color, -1)
  """
  overlay = frame.copy()
  cv2.rectangle(overlay, x0_y0, x1_y1, color, -1)
  cv2.rectangle(frame, x0_y0, x1_y1, color, thickness)
  cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
