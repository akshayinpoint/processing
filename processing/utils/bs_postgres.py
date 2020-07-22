"""Utility for working with the PostgresSQL database."""

import logging
from typing import Union

from peewee import *

from bs_vpe.db_connection import DEPLOY  # pyright: reportMissingImports=false

# pyright: reportUndefinedVariable=false
if DEPLOY == "vpelive":
  db = PostgresqlDatabase('productiondb',
                          user='produser',
                          password='ColInte1@20200701',
                          host='165.227.91.212')
elif DEPLOY == "MasterVPEstaging":
  db = PostgresqlDatabase('stagingbsdb',
                          user='stageuser',
                          password='ColInte1@20200610',
                          host='67.205.187.41')
else:
  db = PostgresqlDatabase('bitstreamuatdb_20200328_pool1',
                          user='uatuser',
                          password='admin@123',
                          host='161.35.1.43')

__db_connect = None


class BaseModel(Model):
  class Meta:
    database = db


class VideoMapping(BaseModel):
  order_id = IntegerField() # Foreign Key references to PK of CCOrder.
  video_id = CharField()
  video_url = CharField()
  video_file_name = CharField()
  is_used_for_survey = BooleanField(default=False)

  class Meta:
    db_table = u'bitstreamapp_video_mapping'


def create_video_map_obj(order_id: Union[int, str],
                         video_id: int,
                         video_url: str,
                         video_file_name: str,
                         log: logging.Logger) -> None:
  try:
    log.debug(f"PeeWee Order ID: {order_id}, Video ID: {video_id}, Video URL: "
              f"{video_url} and Video: {video_file_name}.")
    VideoMapping.create(order_id=order_id,
                        video_id=video_id,
                        video_url=video_url,
                        video_file_name=video_file_name)
    log.debug("Closing PeeWee connection...")
    db.close()
  except Exception:
    log.debug("Skipping video mapping using Peewee...")
  global __db_connect
  __db_connect = None

def connectPsqlDB():
  print('Connecting to PostgresSQL database...')

  global __db_connect
  __db_connect = db.connect()


if not __db_connect:
  connectPsqlDB()
