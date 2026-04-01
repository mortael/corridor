# Module: main
# Author: mortael
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
# v1.3.0: Watch history sync + progress reporting back to corridordigital.com

from __future__ import unicode_literals
import sys
import requests
from urllib import parse as urllib_parse
from kodi_six import xbmcplugin, xbmcgui

from resources.lib import constants
from resources.lib import api
from resources.lib import kodi

_url = sys.argv[0]
_handle = int(sys.argv[1])

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'

VIDEO_ROW_TYPES = {'latest-list', 'free-media-list', 'season-banner', 'hot-list',
                   'user-recommendations', 'continue-watching'}
SHOW_ROW_TYPES = {'playlist'}


def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urllib_parse.urlencode(kwargs))


def _make_request(url, token=None):
    headers = {
        'User-Agent': UA,
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://www.corridordigital.com',
        'Referer': 'https://www.corridordigital.com/',
        'x-platform': 'web',
    }
    if token:
        headers['Authorization'] = 'bearer ' + token
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def _pick_image(images, *preferred_types):
    for img_type in preferred_types:
        for img in images:
            if img.get('type') == img_type:
                return img['url']
    return images[0]['url'] if images else ''


def _get_token():
    if not kodi.get_setting('email'):
        return None
    return api.login()


def _duration_secs(duration_str):
    if not duration_str:
        return 0
    try:
        parts = duration_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except Exception:
        pass
    return 0


def _add_video_item(video, watch_history=None):
    """
    Build a playable ListItem from a video dict.
    watch_history: dict keyed by mediaId from api.get_watch_history()
    Returns (list_item, url, is_folder)
    """
    vid_id = video.get('id') or video.get('mediaId')
    name = video.get('title', 'Unknown')
    duration_str = video.get('duration', '')
    images = video.get('images', [])
    plot = video.get('shortDescription') or name
    videodate = video.get('datePublished', '')
    exclusive = video.get('exclusive', False)
    subscription_only = video.get('subscriptionOnly', False)

    # Watch state from history API (takes priority over inline percent)
    history = (watch_history or {}).get(vid_id, {})
    percentage = history.get('percentage', video.get('percent', 0))
    resume_ms = history.get('startTimeMs', 0)

    label = name
    if duration_str:
        label = '{0} ({1})'.format(name, duration_str)
    if exclusive:
        label = '[COLOR gold]\u2605[/COLOR] ' + label
    if subscription_only:
        label = '[COLOR gray][SUB][/COLOR] ' + label

    dateadded = premiered = ''
    if videodate:
        try:
            dateadded = videodate.split('+')[0].replace('T', ' ')
            premiered = dateadded.split(' ')[0]
        except Exception:
            pass

    dur_secs = _duration_secs(duration_str)

    # playcount=1 marks as watched in Kodi (green checkmark)
    watched = percentage >= constants.WATCHED_THRESHOLD
    playcount = 1 if watched else 0

    list_item = xbmcgui.ListItem(label=label)

    thumb = _pick_image(images, 'thumbnail', 'packshot', 'hero-web', 'hero-mobile')
    fanart = _pick_image(images, 'hero-web', 'hero-mobile', 'thumbnail')
    if thumb:
        list_item.setArt({'thumb': thumb, 'icon': thumb, 'fanart': fanart})

    # Kodi 21+: use InfoTagVideo API instead of deprecated setInfo()
    tag = list_item.getVideoInfoTag()
    tag.setTitle(label)
    tag.setPlot(plot)
    tag.setMediaType('video')
    if dateadded:
        tag.setDateAdded(dateadded)
    if premiered:
        tag.setPremiered(premiered)
    if dur_secs:
        tag.setDuration(dur_secs)
    tag.setPlaycount(playcount)

    # Resume position
    if resume_ms and not watched and dur_secs:
        list_item.setProperty('ResumeTime', str(int(resume_ms / 1000)))
        list_item.setProperty('TotalTime', str(dur_secs))

    list_item.setProperty('IsPlayable', 'true')
    return list_item, get_url(action='play', video=vid_id), False


def _add_show_folder(show):
    season_id = show.get('seasonId')
    name = show.get('title', 'Unknown')
    desc = show.get('shortDescription', '')
    images = show.get('images', [])
    exclusive = show.get('exclusive', False)

    label = ('[COLOR gold]\u2605[/COLOR] ' if exclusive else '') + name

    list_item = xbmcgui.ListItem(label=label)

    thumb = _pick_image(images, 'packshot', 'thumbnail', 'feature-logo')
    fanart = _pick_image(images, 'hero-web', 'hero-web-slim', 'packshot')
    if thumb:
        list_item.setArt({'thumb': thumb, 'icon': thumb, 'fanart': fanart})

    tag = list_item.getVideoInfoTag()
    tag.setTitle(name)
    tag.setPlot(desc)
    tag.setMediaType('video')

    return list_item, get_url(action='season', season_id=season_id, name=name), True


def list_home():
    xbmcplugin.setPluginCategory(_handle, 'Corridor Digital')
    xbmcplugin.setContent(_handle, 'videos')

    token = _get_token()

    try:
        data = _make_request(constants.HOME_PAGE, token)
    except Exception as e:
        kodi.log('list_home error: ' + str(e), level=4)
        kodi.notify('Failed to load home: ' + str(e)[:80])
        xbmcplugin.endOfDirectory(_handle)
        return

    shows_item = xbmcgui.ListItem(label='Shows')
    shows_item.getVideoInfoTag().setTitle('Shows')
    xbmcplugin.addDirectoryItem(_handle, get_url(action='shows'), shows_item, True)

    for row in data.get('pageRows', []):
        row_type = row.get('type', '')
        row_name = row.get('name', '')
        media = row.get('media', [])

        if not media or row_type == 'hero-carousel':
            continue

        if row_type in VIDEO_ROW_TYPES:
            item = xbmcgui.ListItem(label='{0} ({1})'.format(row_name, len(media)))
            item.getVideoInfoTag().setPlot(row_name)
            item_url = get_url(action='videorow', row_type=row_type, row_name=row_name)
            xbmcplugin.addDirectoryItem(_handle, item_url, item, True)
        elif row_type in SHOW_ROW_TYPES:
            item = xbmcgui.ListItem(label='{0} ({1})'.format(row_name, len(media)))
            item.getVideoInfoTag().setPlot(row_name)
            item_url = get_url(action='showrow', row_type=row_type, row_name=row_name)
            xbmcplugin.addDirectoryItem(_handle, item_url, item, True)

    xbmcplugin.endOfDirectory(_handle)


def list_video_row(row_type, row_name):
    xbmcplugin.setPluginCategory(_handle, row_name)
    xbmcplugin.setContent(_handle, 'videos')

    token = _get_token()
    watch_history = api.get_watch_history(token)

    try:
        data = _make_request(constants.HOME_PAGE, token)
    except Exception as e:
        kodi.log('list_video_row error: ' + str(e), level=4)
        kodi.notify('Error: ' + str(e)[:80])
        xbmcplugin.endOfDirectory(_handle)
        return

    for row in data.get('pageRows', []):
        if row.get('type') == row_type and row.get('name') == row_name:
            for video in row.get('media', []):
                if not (video.get('id') or video.get('mediaId')):
                    continue
                list_item, item_url, is_folder = _add_video_item(video, watch_history)
                xbmcplugin.addDirectoryItem(_handle, item_url, list_item, is_folder)
            break

    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_DATEADDED)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(_handle)


def list_show_row(row_type, row_name):
    xbmcplugin.setPluginCategory(_handle, row_name)
    xbmcplugin.setContent(_handle, 'videos')

    try:
        data = _make_request(constants.HOME_PAGE)
    except Exception as e:
        kodi.log('list_show_row error: ' + str(e), level=4)
        kodi.notify('Error: ' + str(e)[:80])
        xbmcplugin.endOfDirectory(_handle)
        return

    for row in data.get('pageRows', []):
        if row.get('type') == row_type and row.get('name') == row_name:
            for show in row.get('media', []):
                if not show.get('seasonId'):
                    continue
                list_item, item_url, is_folder = _add_show_folder(show)
                xbmcplugin.addDirectoryItem(_handle, item_url, list_item, is_folder)
            break

    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(_handle)


def list_shows():
    xbmcplugin.setPluginCategory(_handle, 'Shows')
    xbmcplugin.setContent(_handle, 'videos')

    try:
        data = _make_request(constants.SHOWS_PAGE)
    except Exception as e:
        kodi.log('list_shows error: ' + str(e), level=4)
        kodi.notify('Failed to load shows: ' + str(e)[:80])
        xbmcplugin.endOfDirectory(_handle)
        return

    seen = set()
    shows = []
    for row in data.get('pageRows', []):
        for item in row.get('media', []):
            sid = item.get('seasonId')
            if sid and sid not in seen:
                seen.add(sid)
                shows.append(item)

    shows.sort(key=lambda x: x.get('title', '').lower())

    for show in shows:
        list_item, item_url, is_folder = _add_show_folder(show)
        xbmcplugin.addDirectoryItem(_handle, item_url, list_item, is_folder)

    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(_handle)


def list_season(season_id, catname=None):
    if catname:
        xbmcplugin.setPluginCategory(_handle, catname)
    xbmcplugin.setContent(_handle, 'videos')

    token = _get_token()
    watch_history = api.get_watch_history(token)

    try:
        data = _make_request(constants.SEASON_URL + str(season_id))
    except Exception as e:
        kodi.log('list_season error: ' + str(e), level=4)
        kodi.notify('Failed to load season: ' + str(e)[:80])
        xbmcplugin.endOfDirectory(_handle)
        return

    season_images = data.get('images', [])
    season_fanart = _pick_image(season_images, 'hero-web', 'hero-web-slim', 'packshot')

    for video in data.get('media', []):
        if not (video.get('id') or video.get('mediaId')):
            continue
        list_item, item_url, is_folder = _add_video_item(video, watch_history)
        if season_fanart and not _pick_image(video.get('images', []), 'hero-web'):
            thumb = _pick_image(video.get('images', []), 'thumbnail', 'packshot')
            list_item.setArt({'thumb': thumb, 'icon': thumb, 'fanart': season_fanart})
        xbmcplugin.addDirectoryItem(_handle, item_url, list_item, is_folder)

    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_DATEADDED)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(_handle)


def play_video(video_id):
    """
    Fetch video info, resolve stream URL, then monitor playback
    to report progress back to corridordigital.com.
    """
    from inputstreamhelper import Helper
    from resources.lib.player import CorridorPlayer
    from resources.lib.license_proxy import LicenseProxy

    token = _get_token()
    device_id = kodi.get_setting(constants.DEVICE_ID_SETTING)

    req_headers = {
        'User-Agent': UA,
        'Origin': 'https://www.corridordigital.com',
        'x-platform': 'web',
        'device-identifier': device_id,
    }
    if token:
        req_headers['Authorization'] = 'bearer ' + token

    try:
        r = requests.get(constants.VIDEO_URL.format(video_id=video_id),
                         headers=req_headers, timeout=30)
        if r.status_code != 200:
            kodi.log('Video fetch failed HTTP {0}'.format(r.status_code), level=4)
            kodi.notify('Failed to load video (HTTP {0})'.format(r.status_code))
            xbmcplugin.setResolvedUrl(_handle, False, xbmcgui.ListItem())
            return
        data = r.json()
    except Exception as e:
        kodi.log('play_video error: ' + str(e), level=4)
        kodi.notify('Error: ' + str(e)[:80])
        xbmcplugin.setResolvedUrl(_handle, False, xbmcgui.ListItem())
        return

    dash_url = data.get('dashUrl')
    widevine_url = data.get('widevineUrl')
    hls_url = data.get('hlsUrl')
    subs = data.get('subtitles', {})
    uid = data.get('uid', '')                    # UUID for progress reporting
    numeric_video_id = data.get('videoId', video_id)  # numeric ID for reporting

    play_item = xbmcgui.ListItem()

    if subs:
        sub_urls = list(subs.values()) if isinstance(subs, dict) else subs
        play_item.setSubtitles(sub_urls)

    resolved = False

    if dash_url:
        is_helper = Helper('mpd', drm='com.widevine.alpha')
        if is_helper.check_inputstream():
            # Route license requests through our local proxy so we control
            # exactly what headers are sent to kms.corridordigital.com.
            # Browser HAR shows: no Content-Type, no Authorization — just
            # Origin + User-Agent + raw Widevine challenge as POST body.
            proxy = LicenseProxy()
            proxy.start()
            proxied_license_url = proxy.license_url(widevine_url)

            stream_headers = urllib_parse.urlencode({
                'User-Agent': UA,
                'Origin': 'https://www.corridordigital.com',
            })

            play_item.setProperty('inputstream', 'inputstream.adaptive')
            # drm_legacy: KeySystem|LicenseURL|Headers
            # License URL points to our local proxy which forwards to real KMS
            play_item.setProperty('inputstream.adaptive.drm_legacy',
                                  'com.widevine.alpha|{0}|'.format(proxied_license_url))
            play_item.setProperty('inputstream.adaptive.stream_headers', stream_headers)
            play_item.setMimeType('application/dash+xml')
            play_item.setPath(dash_url)
            play_item.setContentLookup(False)
            xbmcplugin.setResolvedUrl(_handle, True, play_item)
            resolved = True

    if not resolved and hls_url:
        is_helper = Helper('hls')
        if is_helper.check_inputstream():
            play_item.setProperty('inputstream', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            play_item.setMimeType('application/vnd.apple.mpegstream_url')
            play_item.setPath(hls_url)
            play_item.setContentLookup(False)
            xbmcplugin.setResolvedUrl(_handle, True, play_item)
            resolved = True

    if not resolved:
        kodi.notify('No playable stream found for video ' + str(video_id))
        xbmcplugin.setResolvedUrl(_handle, False, xbmcgui.ListItem())
        return

    # Monitor playback and report progress, then stop the proxy
    # CorridorPlayer gets actual duration from Kodi's getTotalTime()
    if token and uid:
        player = CorridorPlayer(token=token, uid=uid, video_id=numeric_video_id)
        player.monitor()
        if resolved:
            try:
                proxy.stop()
            except Exception:
                pass
    elif resolved:
        try:
            proxy.stop()
        except Exception:
            pass


def router(paramstring):
    params = dict(urllib_parse.parse_qsl(paramstring))
    if params:
        action = params.get('action', '')
        if action == 'shows':
            list_shows()
        elif action == 'season':
            list_season(params['season_id'], params.get('name'))
        elif action == 'videorow':
            list_video_row(params['row_type'], params['row_name'])
        elif action == 'showrow':
            list_show_row(params['row_type'], params['row_name'])
        elif action == 'play':
            play_video(params['video'])
        elif action == 'listing':
            list_season(params.get('category'), params.get('name'))
        else:
            raise ValueError('Invalid action: {0}'.format(action))
    else:
        list_home()


if __name__ == '__main__':
    router(sys.argv[2][1:])
