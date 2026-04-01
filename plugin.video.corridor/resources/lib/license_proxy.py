# license_proxy.py
# Minimal HTTP proxy server that forwards Widevine license requests to the KMS.
# Runs on localhost, receives the raw challenge from ISA, forwards to KMS,
# returns the raw license response. This gives us full control over headers.
#
# ISA is pointed at http://localhost:PORT/widevine?cd=...
# instead of directly at kms.corridordigital.com

import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib import parse as urllib_parse
from resources.lib import kodi

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'
PROXY_PORT = 47952  # arbitrary local port


class LicenseHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        kodi.log('LicenseProxy: ' + (format % args))

    def do_POST(self):
        # Read the raw Widevine challenge from ISA
        content_length = int(self.headers.get('Content-Length', 0))
        challenge = self.rfile.read(content_length)
        kodi.log('LicenseProxy: received challenge {} bytes'.format(len(challenge)))

        # Reconstruct the real KMS URL from our path (ISA sends /widevine?cd=...)
        kms_url = 'https://kms.corridordigital.com' + self.path

        # Forward to KMS with exact headers the browser uses - no Content-Type
        try:
            resp = requests.post(
                kms_url,
                data=challenge,
                headers={
                    'User-Agent': UA,
                    'Origin': 'https://www.corridordigital.com',
                    'Referer': 'https://www.corridordigital.com/',
                    'Accept': '*/*',
                },
                timeout=15,
            )
            kodi.log('LicenseProxy: KMS responded HTTP {}'.format(resp.status_code))

            if resp.status_code == 200:
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Length', str(len(resp.content)))
                self.end_headers()
                self.wfile.write(resp.content)
            else:
                kodi.log('LicenseProxy: KMS error body: ' + resp.text[:200])
                self.send_response(resp.status_code)
                self.end_headers()

        except Exception as e:
            kodi.log('LicenseProxy: request failed: ' + str(e), level=4)
            self.send_response(500)
            self.end_headers()


class LicenseProxy:
    """Start a local license proxy server in a background thread."""

    def __init__(self):
        self._server = None
        self._thread = None

    def start(self):
        if self._server:
            return
        self._server = HTTPServer(('127.0.0.1', PROXY_PORT), LicenseHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        kodi.log('LicenseProxy: started on port {}'.format(PROXY_PORT))

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server = None
            kodi.log('LicenseProxy: stopped')

    def license_url(self, real_kms_url):
        """Replace the kms.corridordigital.com host with our local proxy."""
        parsed = urllib_parse.urlparse(real_kms_url)
        proxied = parsed._replace(
            scheme='http',
            netloc='127.0.0.1:{}'.format(PROXY_PORT)
        )
        return urllib_parse.urlunparse(proxied)
