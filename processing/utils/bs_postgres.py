"""Utility for working with the PostgresSQL database."""

from typing import Union

from bs_vpe.db_connection import DEPLOY
from ve_admin import models as ve_models


class style():
    CBOLD = '\33[1m'
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'


def create_video_map_obj(order_id: Union[int, str], video_id: int,
                         video_url: str, video_file_name: str) -> None:
  try:
      print(style.BLUE, "Values entering >>> ", order_id, video_id,
            video_url, video_file_name, style.RESET)
      save_obj = ve_models.VideoMapping.objects.create(order_id=order_id,
                                                       video_id=video_id,
                                                       video_url=video_url,
                                                       video_file_name=video_file_name)
      print(style.GREEN, "Completed: ", save_obj, style.RESET)
  except Exception as error:
      print(style.RED, "Django ORM Error >>> ", error, style.RESET)
