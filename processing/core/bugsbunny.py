"""Complete video processing engine in one go."""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

import requests

# pyright: reportMissingImports=false
from app import models
from app.email import (email_to_admin_for_order_fail,
                       email_to_admin_for_order_success)
from processing.core.redact import redact_faces, redact_license_plates
from processing.core.motion import track_motion
from processing.core.sylvester import compress_video
from processing.core.trim import (trim_by_factor, trim_by_points,
                                  trim_num_parts, trim_sample_section,
                                  trim_sub_sample)
from processing.utils.boto_wrap import create_s3_bucket, upload_to_bucket
from processing.utils.bs_postgres import create_video_map_obj
from processing.utils.common import now
from processing.utils.generate import bucket_name, order_name, video_type
from processing.utils.local import rename_aaaa_file, rename_original_file
from processing.utils.paths import videos

_AWS_ACCESS_KEY = 'XAMES3'
_AWS_SECRET_KEY = 'XAMES3'


def calling_processing(json_obj: str, log: logging.Logger) -> bool:
  """This is something which works with/on REST api."""
  try:
    header = {'api-key': ('epVgnissecorP2020yjbadsdsa05jdagdsah22a'
                          'll0ahm0duil0lah03333fo0r33eve0ryt0hin0g')}

    #UAT and Staging
    #URL = 'http://64.227.0.147:9000/new_connection_order/'
    #URL = 'http://127.0.0.1:9000/new_connection_order/'

    #Production
    URL = 'http://161.35.6.215:9000/new_connection_order/'

    response = requests.post(URL, json.dumps(json_obj), headers=header)
    log.info(f'Response status: {response}')

    return True
  except Exception as error:
    log.exception(error)
    log.critical('Something went wrong while running calling_processing().')
    return False


def trimming_callable(json_data: dict,
                      final_file: str,
                      log: logging.Logger) -> Union[Optional[List], str]:
  """Trimming function."""
  trimmed = []

  trim_type = json_data['trim_type']
  clip_length = json_data.get('clip_length', 30)
  trim_factor = json_data.get('trim_factor', 's')
  last_clip = json_data.get('last_clip', False)
  number_of_clips = json_data.get('number_of_clips', 24)
  equal_distribution = json_data.get('equal_distribution', True)
  random_start = json_data.get('random_start', True)
  random_sequence = json_data.get('random_sequence', True)
  start_time = json_data['start_time']
  end_time = json_data['end_time']
  sample_start_time = json_data['sample_start_time']
  sample_end_time = json_data['sample_end_time']
  timestamp_format = json_data.get('timestamp_format', '%H:%M:%S')
  pt_start_time = json_data.get('point_start_time', 0)
  pt_end_time = json_data.get('point_end_time', 30)

  if trim_type == 'trim_by_factor':
    log.info('Trimming video by factor.')
    trimmed = trim_by_factor(final_file, trim_factor, clip_length, last_clip)
  elif trim_type == 'trim_num_parts':
    log.info(f'Trimming video in {number_of_clips} parts.')
    trimmed = trim_num_parts(final_file, number_of_clips, equal_distribution,
                             clip_length, random_start, random_sequence)
  elif trim_type == 'trim_sub_sample':
    log.info('Trimming portion of the video as per timestamp.')
    trimmed = trim_sub_sample(final_file, start_time, end_time,
                              sample_start_time, sample_end_time,
                              timestamp_format)
  elif trim_type == 'trim_by_points':
    log.info('Trimming video as per start & end time.')
    trimmed = trim_by_points(final_file, pt_start_time, pt_end_time,
                             trim_factor)

  return trimmed


def write_to_db(order_id: Union[int, str],
                video_obj: List[dict],
                log: logging.Logger) -> None:
  """Write data to database.

  Args:
    order_id: Primary key of Order ID.
    video_obj: List of dictionary of file, id & url.
  """
  for idx in video_obj:
    video_id = idx['video_id']
    video_url = idx['url']
    video_file_name = idx['file_name']
    try:
      create_video_map_obj(order_id, video_id, video_url, video_file_name, log)
    except Exception as error:
      log.exception(error)


def smash_db(order_id: int,
             videos: List,
             urls: List,
             log: logging.Logger) -> None:
  """Smashes video information into database.

  Args:
    order_id: Primary key of Order ID.
    videos: List of names of videos uploaded to S3.
    urls: List of urls of video uploaded to S3.
  """
  order_id = int(order_id)
  video_obj = [{'file_name': os.path.basename(k),
                'url': v,
                'video_id': Path(k).stem} for k, v in zip(videos, urls)]
  log.info("Smashing object details in the database...")
  write_to_db(order_id, video_obj, log)


def spin(json_obj: str,
         current: datetime,
         log: logging.Logger,
         db_pk: int) -> None:
  """Spin the Video Processing Engine."""
  try:
    start = now()
    upload, trimmed, urls, addons = [], [], [], []

    json_data = json.loads(json_obj)
    log.info('Parsed consumer JSON request.')

    country = json_data.get('country_code', 'xa')
    customer = json_data.get('customer_id', 0)
    contract = json_data.get('contract_id', 0)
    order = json_data.get('order_id', 0)
    store = json_data.get('store_id', 0)
    area = json_data.get('area_code', 'e')
    camera = json_data.get('camera_id', 0)
    org_file = json_data.get('org_file', None)
    sampling_rate = json_data['sampling_rate']
    motion = json_data.get('analyze_motion', False)
    count_obj = json_data.get('count_obj', False)
    objects = json_data.get('objects', None)
    analyze_face = json_data.get('analyze_face', False)
    analyze_license_plate = json_data.get('analyze_license_plate', False)
    compress = json_data.get('perform_compression', True)
    trim = json_data.get('perform_trimming', True)
    trimpress = json_data.get('trim_compressed', True)
    db_order = json_data.get('order_pk', 0)

    bucket = bucket_name(country, customer, contract, order)
    order = order_name(store, area, camera, current)

    log.info('Processing Engine loaded.')
    log.info(f'Processing Engine started spinning for angle #{camera}...')

    if org_file:
      log.info(f'Prime base file "{os.path.basename(org_file)}" acquired.')
      log.info(f'Creating directory for processing...')
      init_clone = rename_original_file(org_file, bucket, order)
      init_path = os.path.join(videos, ''.join([bucket, order, '_xa']))

      if not os.path.isdir(init_path):
        os.mkdir(init_path)

      temp_clone = os.path.join(init_path, os.path.basename(init_clone))
      cloned = shutil.copy(init_clone, os.path.join(init_clone, temp_clone))
      os.remove(init_clone)
      temp = cloned

      if motion:
        cloned = track_motion(cloned, log)
        log.info('Fixing up the symbolic link of the motion detected video...')
        shutil.move(cloned, temp)
        log.info('Symbolic link has been restored for motion detected video.')
        cloned = temp
      else:
        log.info('Skipping motion analysis...')

      log.info('Updating Event Milestone 02 - Motion Trimming...')
      milestone_db = models.MilestoneStatus(work_status_id=db_pk,
                                            milestone_id=2)
      milestone_db.save()
      log.info('Event Milestone 02 - Motion Trimming: UPDATED')

      log.info(f'Randomly sampling {sampling_rate}% of the original video...')
      trim_sample_section(temp, sampling_rate)
      log.info('Updating Event Milestone 03 - Random Sampling...')
      milestone_db = models.MilestoneStatus(work_status_id=db_pk,
                                            milestone_id=3)
      milestone_db.save()
      log.info('Event Milestone 03 - Random Sampling: UPDATED')

      if not trim:
        trimpress = False

      log.info('Renaming original video as per internal nomenclature...')
      final = rename_aaaa_file(cloned, video_type(compress, trim, trimpress))

      if compress:
        log.info('Analyzing and compressing video...')
        final = compress_video(final, log)
        log.info('Updating Event Milestone 04 - QA & Compression...')
        milestone_db = models.MilestoneStatus(work_status_id=db_pk,
                                              milestone_id=4)
        milestone_db.save()
        log.info('Event Milestone 04 - QA & Compression: UPDATED')

        if trimpress:
          trimmed = trimming_callable(json_data, final, log)

      elif trim:
        trimmed = trimming_callable(json_data, final, log)

      if trimmed:
        upload.extend(trimmed)
      log.info('Updating Event Milestone 05 - Trimming Videos...')
      milestone_db = models.MilestoneStatus(work_status_id=db_pk,
                                            milestone_id=5)
      milestone_db.save()
      log.info('Event Milestone 05 - Trimming Videos: UPDATED')

      if count_obj:
        for idx in upload:
          log.info(f'Counting object(s) in video {os.path.basename(idx)}...')
          try:
            addon_temp = track_motion(idx, log, objects)
          except Exception:
            addon_temp = idx
          addons.append(addon_temp)
        upload = addons
        addons = []

      if analyze_face:
        for idx in upload:
          log.info(f'Redacting face(s) in video {os.path.basename(idx)}...')
          try:
            addon_temp = redact_faces(idx, log)
          except Exception:
            addon_temp = idx
          addons.append(addon_temp)
        upload = addons
        addons = []

      if analyze_license_plate:
        for idx in upload:
          log.info('Redacting license plate(s) in video '
                   f'{os.path.basename(idx)}...')
          try:
            addon_temp = redact_license_plates(idx, log)
          except Exception:
            addon_temp = idx
          addons.append(addon_temp)
        upload = addons
        addons = []

      log.info('Updating Event Milestone 06 - Addon Features...')
      save_milestone(db_pk, 6)
      log.info('Event Milestone 06 - Addon Features: UPDATED')

      try:
        create_s3_bucket(_AWS_ACCESS_KEY, _AWS_SECRET_KEY, bucket[:-4], log)
      except Exception:
        pass

      log.info(f'Uploading {len(upload)} video(s) on S3 bucket...')
      for idx, file in enumerate(upload):
        url = upload_to_bucket(_AWS_ACCESS_KEY, _AWS_SECRET_KEY, bucket[:-4],
                               file, log, directory=bucket)
        urls.append(url)
        log.info(f'Uploaded {idx + 1}/{len(upload)} on to S3 bucket.')
      
      log.info('Updating Event Milestone 07 - Video Upload...')
      save_milestone(db_pk, 7)
      log.info('Event Milestone 07 - Video Upload: UPDATED')

      smash_db(db_order, upload, urls, log)
      log.info('Updating Event Milestone 08 - Database Hit...')
      save_milestone(db_pk, 8)
      log.info('Event Milestone 08 - Database Hit: UPDATED')

      log.info('Cleaning up secure directory...')
      shutil.rmtree(init_path)
      log.info('Updating Event Milestone 09 - Final Cleanup...')
      save_milestone(db_pk, 9)
      log.info('Event Milestone 09 - Final Cleanup: UPDATED')
      log.info('Updating admin via email.')
      email_to_admin_for_order_success(json_data.get('order_pk', 0))
      log.info(f'Processing Engine ran for about {now() - start}.')
    else:
      log.error("Skipping order creation since Processing Engine could not "
                "video file for processing.")
  except KeyboardInterrupt:
    log.error('Spinner interrupted.')
  except Exception as error:
    log.exception(error)
    log.error('Processing failed, updating admin regarding the issue.')
    # pyright: reportUnboundVariable=false
    email_to_admin_for_order_fail(json_data.get('order_pk', 0))
    log.critical('Something went wrong while video processing was running.')


def save_milestone(db_pk, stone_id) -> bool:
  try:
    milestone_db = models.MilestoneStatus(work_status_id=db_pk,
                                          milestone_id=stone_id)
    milestone_db.save()
    return True
  except Exception as error:
    print(error)
    return False
