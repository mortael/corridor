from . import constants
import requests
from . import kodi


def login():
    email = kodi.get_setting('email')
    password = kodi.get_setting('password')

    params = {
        'key': constants.GOOGLE_KEY,
    }

    payload = {
        'email': email,
        'password': password,
        'returnSecureToken': True,
    }

    session = requests.session()

    data = session.post(constants.LOGIN_URL, params=params, json=payload)
    if data.status_code != 200:
        kodi.set_setting('idtoken', 'null')
        return 'null'
    else:
        data = data.json()
        idToken = data.get('idToken') if data.get('idToken') else 'null'
        kodi.set_setting('idtoken', idToken)
        return idToken