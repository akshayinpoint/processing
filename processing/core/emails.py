import logging
import json
import requests

headers = {'api-key': 'apiCI@mlsrs20200129RJGSsAhNaAikh7897542328jtdb'}
url = 'https://email.bitstreamservices.com/smtp/sendemail/'


def email_to_admin_for_order_success(json_data: dict,
                                     log: logging.Logger) -> None:
  try:
    data = {}

    order_id = json_data.get('order_pk', 0)
    admin = json_data.get('admin_user', 'Admin')

    test_users = ["akshay@inpointtech.com", "nikhil@inpointtech.com",
                  "suraj@inpointtech.com", "rajendra@inpointtech.com"]
    admin_email = json_data.get('admin_email', test_users)

    src_type = "Stored" if json_data.get('use_archived', False) else "Live"
    f_name = json_data.get('f_name', None)
    f_url = json_data.get('org_file', None)
    clip_length = json_data.get('clip_length', 30)
    sampling_rate = json_data['sampling_rate']
    clips_count = json_data['clips_count']

    data['subject'] = f'[SUCCESSFULL] (CI-{order_id}) Processed Successfully'
    data['from_email'] = 'noreply@bitstreamservices.com'
    data['to_email'] = admin_email
    data['email_type'] = "html"

    data['message'] = f'''
    <html>

    <body>
        <p>Dear <b>{admin}</b>,</p>
        <p>Order ID: {order_id} is processed <b>successfully</b>.</p>
        <p><b>Order details</b>:<br>
            Video source type: <b>{src_type}</b><br>
            Video file name: <b>{f_name}</b><br>
            Video AWS S3 url: <b>{f_url}</b><br>
            Video sampling rate: <b>{sampling_rate}</b>%<br>
            Video clip length: <b>{clip_length}</b> secs<br>
            Video clips count: <b>{clips_count}</b><br>
        </p>
        <p>Thanks,<br>The Video Processing Engine Team<br>© 2020 Video Processing Engine, USA</p>
    </body>

    </html>
    '''
    response = requests.post(url, json.dumps(data), headers=headers)
    status = response.status_code
    data = response.text
    log.info(f'Received status code as {status}.')
  except Exception as e:
    log.exception(e)


def email_to_admin_for_order_failure(json_data: dict,
                                     log: logging.Logger) -> None:
  try:
    data = {}

    order_id = json_data.get('order_pk', 0)
    admin = json_data.get('admin_user', 'Admin')

    test_users = ["akshay@inpointtech.com", "nikhil@inpointtech.com",
                  "suraj@inpointtech.com", "rajendra@inpointtech.com"]
    admin_email = json_data.get('admin_email', test_users)

    src_type = "Stored" if json_data.get('use_archived', False) else "Live"
    f_name = json_data.get('f_name', None)
    f_url = json_data.get('org_file', None)
    clip_length = json_data.get('clip_length', 30)
    sampling_rate = json_data['sampling_rate']
    clips_count = json_data['clips_count']

    data['subject'] = f'[FAILED] (CI-{order_id}) Didn\'t Process'
    data['from_email'] = 'noreply@bitstreamservices.com'
    data['to_email'] = admin_email
    data['email_type'] = "html"

    data['message'] = f'''
    <html>

    <body>
        <p>Dear <b>{admin}</b>,</p>
        <p>Order ID: {order_id} has <b>not processed</b>.</p>
        <p>Please try after sometime.</p>
        <p><b>Order details</b>:<br>
            Video source type: <b>{src_type}</b><br>
            Video file name: <b>{f_name}</b><br>
            Video AWS S3 url: <b>{f_url}</b><br>
            Video sampling rate: <b>{sampling_rate}</b>%<br>
            Video clip length: <b>{clip_length}</b> secs<br>
            Video clips count: <b>{clips_count}</b><br>
        </p>
        <p>Thanks,<br>The Video Processing Engine Team<br>© 2020 Video Processing Engine, USA</p>
    </body>

    </html>
    '''
    response = requests.post(url, json.dumps(data), headers=headers)
    status = response.status_code
    data = response.text
    log.info(f'Received status code as {status}.')
  except Exception as e:
    log.exception(e)


b = {'start_date': '2020-08-14', 'end_date': '2020-08-15', 'country_code': 'xa', 'customer_id': 71, 'contract_id': '1', 'order_id': 14, 'order_pk': 254, 'camera_address': '', 'store_id': 55, 'camera_id': '2', 'area_code': 'BE', 'use_archived': True, 'original_file': 'VIDEO FILE', 'access_mode': 'FTP', 'camera_username': '', 'camera_password': '', 'start_time': '21:34:15', 'end_time': '21:10:00', 'stream_duration': 60, 'sub_json': {'p_ip': 'files1.earthcam.net', 'p_name': 'collectiveintelinc', 'p_pass': 'e$TemCuZ7i', 'start_date': '', 'start_time': '', 'point_access': '/last5days/ci_njSeasideHeightsNorth/2020/', 'camera_timezone': 'Asia/Kolkata', 'stored_filename': 'stored_1597330044', 'earthcam_download': True, 'earthcam_end_time': '02:00', 'schedule_download': False, 'earthcam_start_date': None, 'earthcam_start_time': '01:00'}, 'select_sample': True, 'sampling_rate': '30.00', 'perform_compression': True, 'perform_trimming': True, 'trim_compressed': True, 'compression_ratio': '60', 'number_of_clips': '3', 'trim_type': 'trim_by_factor', 'equal_distribution': True, 'clip_length': '10', 'trim_factor': 's', 'last_clip': True, 'sample_start_time': '17:00:00', 'sample_end_time': '18:00:00', 'camera_timezone': 'Asia/Kolkata', 'ui_timestamp_format': '%Y-%m-%d %H:%M:%S', 'point_start_time': 0, 'point_end_time': 30, 'analyze_motion': False, 'analyze_face': False, 'vpe_unit': 'acquisition', 'count_obj': False, 'objects': None, 'analyze_license_plate': False, 'clips_count': 26}


from processing.utils.logs import log
log = log('info')
email_to_admin_for_order_success(b, log)
