from kodi_six import xbmc, xbmcaddon

addon = xbmcaddon.Addon()
pluginname = addon.getAddonInfo("name")


def log(msg, level=xbmc.LOGINFO):
    xbmc.log("[{0}] {1}".format(pluginname, msg), level=level)


def get_setting(setting):
    return addon.getSetting(setting)


def set_setting(id, value):
    if not isinstance(value, str):
        value = str(value)
    addon.setSetting(id, value)


def notify(msg, title=None):
    if title is None:
        title = pluginname
    xbmc.executebuiltin('Notification({0},{1},5000)'.format(title, msg))
