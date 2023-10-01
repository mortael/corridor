from resources.lib.constants import ANCHOR_URL, LOGIN_URL, RELOAD_URL, APPCHECK_URL
from resources.lib import kodi
from urllib.parse import urlparse, parse_qs
import requests


def login():
    email = kodi.get_setting('email')
    password = kodi.get_setting('password')
    session = requests.session()
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'

    url_variables = parse_qs(urlparse(ANCHOR_URL).query)
    r = session.get(ANCHOR_URL, headers={
        "User-Agent": ua})
    token_1 = r.text.split("type=\"hidden\" id=\"recaptcha-token\" value=\"")[1].split("\"")[0]

    loginpayload = {
        'clientType': 'CLIENT_TYPE_WEB',
        'email': email,
        'password': password,
        'returnSecureToken': True,
    }

    data = f"v={url_variables['v'][0]}&reason=q&c={token_1}&k={url_variables['k'][0]}&co={url_variables['co'][0]}&hl=en&size=invisible"
    headers = {
        "User-Agent": ua,
        "referer": r.url,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    r = session.post(RELOAD_URL, headers=headers, data=data)
    rresp = r.text.split("[\"rresp\",\"")[1].split("\"")[0]

    payload = {'recaptcha_enterprise_token': rresp}
    r = session.post(APPCHECK_URL, json=payload)
    token = r.json()['token']

    data = session.post(LOGIN_URL, json=loginpayload, headers={'x-firebase-appcheck': token, 'user-agent': ua})
    if data.status_code != 200:
        kodi.set_setting('idtoken', 'null')
        return 'null'
    else:
        data = data.json()
        idToken = data.get('idToken') if data.get('idToken') else 'null'
        kodi.set_setting('idtoken', idToken)
        return idToken
