import json
from typing import List

from processing.core.bugsbunny import spin
from processing.utils.common import now
from processing.utils.logs import log
# pyright: reportMissingImports=false
from app import models

deployed = False

if deployed:
  _log = log('error')
else:
  _log = log('info')


def sheep(json_obj: dict, db_pk: int) -> None:
  """Sheep thread object.

  Args:
    json_obj: JSON dictionary which Admin sends to VPE.
    db_pk: Primary key of Database entry.
  """
  try:
    status_db = models.RequestStatus.objects.filter(id=db_pk).values()
    status_db.update(processing_status_id=2)
    spin(json.dumps(json_obj), now(), _log, db_pk)
    _log.critical('Processing Engine is ready to consume new request.')
  except KeyboardInterrupt:
    _log.error('Video processing engine sheep interrupted.')
  except Exception as _error:
    _log.exception(_error)


def hill(orders: List):
  """Some threading related stuff."""
  for idx in orders:
    db_pk = int(idx['db_pk'])
    sheep(idx, db_pk)
