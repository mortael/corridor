# Module: api
# Handles login and HTTP requests to corridordigital.com
# Login uses /v2/account/login JWT endpoint (no reCAPTCHA/Firebase needed)
# Token is NOT cached to settings - login is called fresh each invocation
# (settings caching is unreliable on CoreELEC/embedded Kodi)

import requests
import uuid
from resources.lib import kodi
from resources.lib.constants import LOGIN_URL, DEVICE_ID_SETTING, \
    WATCH_HISTORY_URL, VIDEO_REPORT_URL

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'

BASE_HEADERS = {
    'User-Agent': UA,
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://www.corridordigital.com',
    'Referer': 'https://www.corridordigital.com/',
    'x-platform': 'web',
}


def _get_device_id():
    device_id = kodi.get_setting(DEVICE_ID_SETTING)
    if not device_id:
        device_id = str(uuid.uuid4())
        kodi.set_setting(DEVICE_ID_SETTING, device_id)
    return device_id


def login():
    """
    Log in and return a fresh JWT token, or None on failure.
    Token is returned directly and NOT stored in settings.
    """
    email = kodi.get_setting('email')
    password = kodi.get_setting('password')

    if not email or not password:
        kodi.log('No credentials configured')
        return None

    payload = {
        'email': email,
        'password': password,
        'device': {
            'deviceIdentifier': _get_device_id(),
            'isActive': True,
            'platform': 'web',
            'model': 'Windows Chrome',
        }
    }

    headers = dict(BASE_HEADERS)
    headers['Content-Type'] = 'application/json'

    try:
        r = requests.post(LOGIN_URL, json=payload, headers=headers, timeout=30)
        if r.status_code != 200:
            kodi.log('Login failed: HTTP {0} - {1}'.format(r.status_code, r.text[:200]))
            return None
        token = r.json().get('token')
        if token:
            kodi.log('Login successful')
            return token
        kodi.log('Login: no token in response')
        return None
    except Exception as e:
        kodi.log('Login exception: ' + str(e), level=4)
        return None


def get_watch_history(token):
    """
    Fetch full watch history.
    Returns dict keyed by mediaId: {percentage, startTimeMs, position}
    """
    if not token:
        return {}
    headers = dict(BASE_HEADERS)
    headers['Authorization'] = 'bearer ' + token
    try:
        r = requests.get(WATCH_HISTORY_URL, headers=headers, timeout=15)
        if r.status_code != 200:
            kodi.log('Watch history failed: HTTP {0}'.format(r.status_code))
            return {}
        return {item['mediaId']: item for item in r.json()}
    except Exception as e:
        kodi.log('get_watch_history error: ' + str(e), level=4)
        return {}


def report_progress(token, uid, video_id, current_ms, total_ms, duration_watched_ms):
    """
    POST playback progress to the Corridor Digital API.
    All time values in milliseconds.
    """
    if not token:
        return
    url = VIDEO_REPORT_URL.format(uid=uid, video_id=video_id)
    headers = dict(BASE_HEADERS)
    headers['Authorization'] = 'bearer ' + token
    headers['Content-Type'] = 'application/json'
    payload = {
        'currentTime': int(current_ms),
        'totalTime': int(total_ms),
        'durationWatched': int(duration_watched_ms),
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        kodi.log('Progress report {0}ms/{1}ms -> HTTP {2}'.format(
            int(current_ms), int(total_ms), r.status_code))
    except Exception as e:
        kodi.log('report_progress error: ' + str(e), level=4)
