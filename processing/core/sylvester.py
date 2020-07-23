"""A subservice for compressing the videos."""

import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from processing.utils.common import file_size
from processing.utils.paths import reference_video


def print_stderr(message) -> None:
  print(message, file=sys.stderr)


def run_command(cmd: List, dry_run: bool = False, verbose: bool = False) -> Optional[Tuple]:
  """Run a command directly."""
  if dry_run or verbose:
    print_stderr('[cmd] ' + ' '.join(cmd))
    if dry_run:
      return None
  process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
  stdout, stderr = process.communicate()
  if process.returncode == 0:
    return stdout.decode("utf-8"), stderr.decode("utf-8")
  else:
    print_stderr('[e] Running command: {}'.format(' '.join(cmd)))
    print_stderr(stderr.decode("utf-8"))
    sys.exit(1)


def calc_ssim_psnr(file: str,
                   reference: str = reference_video,
                   scaling_algorithm: str = 'bicubic',
                   dry_run: bool = False, verbose: bool = False) -> Tuple:
  """Calculate SSIM and PSNR values for the video."""
  psnr_data, ssim_data = [], []
  temp_file_name_psnr, temp_file_name_ssim, rating = 'xa', 'xa', 'xa'
  try:
    temp_dir = tempfile.gettempdir()
    # pyright: reportGeneralTypeIssues=false
    temp_file_name_ssim = os.path.join(temp_dir,
      next(tempfile._get_candidate_names()) + '-ssim.txt')
    temp_file_name_psnr = os.path.join(temp_dir,
      next(tempfile._get_candidate_names()) + '-psnr.txt')
    filter_chains = [
      f'[1][0]scale2ref=flags={scaling_algorithm}[file][reference]',
      '[file]split[dist1][dist2]',
      '[reference]split[ref1][ref2]',
      f'[dist1][ref1]psnr={temp_file_name_psnr}',
      f'[dist2][ref2]ssim={temp_file_name_ssim}']
    cmd = ['ffmpeg', '-nostdin', '-y', '-threads', '1', '-i', reference, '-i',
           file, '-filter_complex', ';'.join(filter_chains), '-an', '-f',
           'null', '/dev/null']
    run_command(cmd, dry_run, verbose)
    if not dry_run:
        with open(temp_file_name_psnr, 'r') as in_psnr:
          lines = in_psnr.readlines()
          for line in lines:
            line = line.strip()
            fields = line.split(' ')
            frame_data = {}
            for field in fields:
              k, v = field.split(':')
              frame_data[k] = round(float(v), 3) if k != 'n' else int(v)
            psnr_data.append(frame_data)
        with open(temp_file_name_ssim, 'r') as in_ssim:
          lines = in_ssim.readlines()
          for line in lines:
            line = line.strip().split(' (')[0]
            fields = line.split(' ')
            frame_data = {}
            for field in fields:
              k, v = field.split(':')
              if k != 'n':
                k = 'ssim_' + k.lower()
                k = k.replace('all', 'avg')
              frame_data[k] = round(float(v), 3) if k != 'n' else int(v)
            ssim_data.append(frame_data)
  except Exception as error:
    raise error
  finally:
    if os.path.isfile(temp_file_name_psnr):
      os.remove(temp_file_name_psnr)
    if os.path.isfile(temp_file_name_ssim):
      os.remove(temp_file_name_ssim)
  scores = {'ssim': ssim_data, 'psnr': psnr_data}
  score = float((scores['ssim'][0]['ssim_avg']))
  if score < 0.5:
    rating = 'Bad'
  elif 0.88 > score > 0.5:
    rating = 'Poor'
  elif 0.95 > score > 0.88:
    rating = 'Fair'
  elif 0.99 > score > 0.95:
    rating = 'Good'
  elif score > 1:
    rating = 'Excellent'
  return (score * 100, rating)


def new_bitrate(file: str) -> int:
  """Returns bitrate of the video file."""

  bit = subprocess.check_output(
      f"ffprobe -hide_banner -loglevel 0 -of flat -i '{file}' -select_streams v -show_entries 'format=bit_rate'", shell=True)
  return int(bit.decode().replace('"', '').strip('format.bit_rate='))


def compress_video(file: str, log: logging.Logger) -> str:
  """Compresses video.

  Compresses video as per the requirements.

  Args:
    file: File to be compressed.
    ratio: Compression ratio to be applied.

  Returns:
    Path of the temporary duplicate file created.
  """
  score, _ = calc_ssim_psnr(file)
  log.info(f'Analyzed score: {round(score, 2)}%')

  if score < 50.0:
    log.info('Applying 20% compression...')
    bitrate = int(new_bitrate(file) * 0.8)
  elif 88.0 >= score >= 50.0:
    log.info('Applying 50% compression...')
    bitrate = int(new_bitrate(file) * 0.5)
  else:
    log.info('Applying 70% compression...')
    bitrate = int(new_bitrate(file) * 0.3)

  ext = os.path.splitext(file)[1]
  temp = os.path.join(os.path.dirname(file),
                      ''.join([Path(file).stem, '_temp_xa', ext]))

  os.rename(file, temp)
  os.system("ffmpeg -loglevel error -y -i {source}  -vcodec libx264 -b {compresion} {file_name}".format(
      source=temp, compresion=bitrate, file_name=file))
  os.remove(temp)
  return file
