# Module: main
# Author: mortael
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals
import sys
from six.moves import urllib_parse
import requests
from kodi_six import xbmcplugin, xbmcgui
import six

from resources.lib import constants
from resources.lib import api
from resources.lib import kodi


_url = sys.argv[0]
_handle = int(sys.argv[1])


def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urllib_parse.urlencode(kwargs))


def get_shows(url):
    shows = requests.get(url).json()
    return shows


def get_videos(url, showid):
    shows = get_shows(url)
    videos = [x['media'] for x in shows if x['id'] == int(showid)]
    return videos[0]


def list_mainvideos(url, category, catname=None):
    if catname:
        xbmcplugin.setPluginCategory(_handle, catname)
    xbmcplugin.setContent(_handle, 'videos')
    videos = get_videos(url, category)
    for video in videos:
        name = video.get('title')
        videoid = video.get('id')
        images = video.get('images')
        plot = video.get('shortDescription') if video.get('shortDescription') else name
        duration = video.get('duration')
        videodate = video.get('datePublished')
        dateadded = videodate.split('+')[0].replace('T', ' ')
        premiered = dateadded.split(' ')[0]
        name = '{0} ({1})'.format(name, duration)
        list_item = xbmcgui.ListItem(label=name)
        list_item.setInfo('video', {'title': name,
                                    'plot': plot,
                                    'mediatype': 'video',
                                    'dateadded': dateadded,
                                    'premiered': premiered})
        if images:
            standardimage = [x['url'] for x in images if x['type'] == 'thumbnail']
            if standardimage:
                list_item.setArt({'thumb': standardimage[0],
                                  'icon': standardimage[0]})
        list_item.setProperty('IsPlayable', 'true')
        itemurl = get_url(action='play', video=videoid)
        is_folder = False
        xbmcplugin.addDirectoryItem(_handle, itemurl, list_item, is_folder)


def list_shows(url):
    xbmcplugin.setPluginCategory(_handle, 'Shows')
    xbmcplugin.setContent(_handle, 'videos')
    shows = get_shows(url)
    shows_dict = {}

    for show in shows:
        if 'media' in show:
            for showitem in show['media']:
                if 'seasonId' in showitem and showitem['seasonId'] not in shows_dict:
                    shows_dict[showitem['seasonId']] = showitem

    for show in sorted(shows_dict.values(), key=lambda x: x['title']):
        name = show.get('title')
        showid = show.get('seasonId')
        images = show.get('images')
        description = show.get('shortDescription')
        list_item = xbmcgui.ListItem(label='{0} ({1})'.format(name, description))
        if images:
            standardimage = [x['url'] for x in images if x['type'] == 'thumbnail']
            if not standardimage:
                standardimage = [x['url'] for x in images if x['type'] == 'packshot']
            if standardimage:
                list_item.setArt({'thumb': standardimage[0],
                                  'icon': standardimage[0]})
        list_item.setInfo('video', {'title': name,
                                    'mediatype': 'video'})
        itemurl = get_url(action='listing', category=showid, url=constants.SEASON, name=name)
        is_folder = True
        xbmcplugin.addDirectoryItem(_handle, itemurl, list_item, is_folder)
    # xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(_handle)


def list_showvideos(url, season, catname=None):
    if catname:
        xbmcplugin.setPluginCategory(_handle, catname)
    xbmcplugin.setContent(_handle, 'videos')
    seasonurl = '{0}{1}'.format(url, season)
    videos = get_shows(seasonurl)
    for video in videos['media']:
        name = video.get('title')
        videoid = video.get('id')
        images = video.get('images')
        plot = video.get('shortDescription') if video.get('shortDescription') else name
        duration = video.get('duration')
        videodate = video.get('datePublished')
        dateadded = videodate.split('+')[0].replace('T', ' ')
        premiered = dateadded.split(' ')[0]
        name = '{0} ({1})'.format(name, duration)
        list_item = xbmcgui.ListItem(label=name)
        list_item.setInfo('video', {'title': name,
                                    'plot': plot,
                                    'mediatype': 'video',
                                    'dateadded': dateadded,
                                    'premiered': premiered})
        if images:
            standardimage = [x['url'] for x in images if x['type'] == 'thumbnail']
            if standardimage:
                list_item.setArt({'thumb': standardimage[0],
                                  'icon': standardimage[0]})
        list_item.setProperty('IsPlayable', 'true')
        itemurl = get_url(action='play', video=videoid)
        is_folder = False
        xbmcplugin.addDirectoryItem(_handle, itemurl, list_item, is_folder)


def play_video(path):
    from inputstreamhelper import Helper
    token = api.login()
    path = '{0}/free'.format(path) if token == 'null' else path
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
               'Origin': 'https://www.corridordigital.com',
               'Authorization': 'bearer {0}'.format(token)}
    url = 'https://content.watchcorridor.com/v4/video/{0}?platform=Web'.format(path)
    data = requests.get(url, headers=headers)
    if data.status_code != 200:
        # insert notification with failure to play
        return
    data = data.json()
    lurl = data.get('widevineUrl')
    subs = data.get('subtitles', [])
    play_item = xbmcgui.ListItem()
    IA = 'inputstream' if six.PY3 else 'inputstreamaddon'
    play_item.setProperty(IA, 'inputstream.adaptive')
    if subs:
        subtitles = subs.values()
        play_item.setSubtitles(list(subtitles)) 
    if lurl:
        is_helper = Helper('mpd', drm='com.widevine.alpha')
        if is_helper.check_inputstream():
            strurl = data.get('dashUrl')
            headers.pop('Authorization')
            lic = lurl + '|Origin=https://www.corridordigital.com&Content-Type= |R{SSM}|'
            play_item.setProperty('inputstream.adaptive.stream_headers', urllib_parse.urlencode(headers))
            play_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
            play_item.setProperty('inputstream.adaptive.license_key', lic)
            play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
            play_item.setMimeType('application/dash+xml')
            play_item.setPath(strurl)
            play_item.setContentLookup(False)
            xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)
    else:
        is_helper = Helper('hls')
        if is_helper.check_inputstream():
            hlsurl = data.get('hlsUrl')
            uid = data.get('uid')
            lic = 'uid={0}&platform=Web|{1}'.format(uid, urllib_parse.urlencode(headers))
            play_item.setProperty('inputstream.adaptive.license_key', lic)
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            play_item.setMimeType('application/vnd.apple.mpegstream_url')
            play_item.setPath(hlsurl)
            play_item.setContentLookup(False)
            xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)


def router(paramstring):
    params = dict(urllib_parse.parse_qsl(paramstring))
    if params:
        if params['action'] == 'listing':
            list_showvideos(params['url'], params['category'], params['name'])
            xbmcplugin.endOfDirectory(_handle)
        elif params['action'] == 'shows':
            list_shows(constants.SHOWS)
        elif params['action'] == 'play':
            play_video(params['video'])
        else:
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        email = kodi.get_setting('email')
        if email == '':
            list_mainvideos(constants.MAIN, '58', 'Free videos')
            xbmcplugin.endOfDirectory(_handle)
        else:
            list_item = xbmcgui.ListItem(label='Shows')
            xbmcplugin.addDirectoryItem(_handle, get_url(action='shows'), list_item, True)
            # list_showvideos(constants.MAIN, '9', 'Latest videos')
            list_mainvideos(constants.MAIN, '23', 'Latest videos')
            xbmcplugin.endOfDirectory(_handle)


if __name__ == '__main__':
    router(sys.argv[2][1:])
