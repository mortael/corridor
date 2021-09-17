from kodi_six import xbmc, xbmcaddon
import six

addon = xbmcaddon.Addon()
pluginname = addon.getAddonInfo("name")

def log(msg, level=xbmc.LOGINFO):
    xbmc.log("[{0}] {1}".format(pluginname, msg), level=level)

def get_setting(setting):
    return addon.getSetting(setting)

def set_setting(id, value):
    if not isinstance(value, six.string_types):
        value = str(value)
    addon.setSetting(id, value)
