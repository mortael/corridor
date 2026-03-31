# All API endpoints discovered from HAR capture 2026-03-31

# Login endpoint
LOGIN_URL = 'https://user.corridordigital.com/v2/account/login?platform=web'

# Content endpoints
CONTENT_CACHE = 'https://content-cache.corridordigital.com'
CONTENT = 'https://content.corridordigital.com'

# Pages API
HOME_PAGE = CONTENT_CACHE + '/pages/v1/home?pageRowSize=50'
SHOWS_PAGE = CONTENT_CACHE + '/pages/v1/shows?pageRowSize=50'

# Season/channel API
SEASON_URL = CONTENT_CACHE + '/channels/v16/season/'

# Video info endpoint
VIDEO_URL = CONTENT + '/v5/video/{video_id}?platform=Web'

# Watch history: GET returns [{mediaId, percentage, startTimeMs, position}, ...]
WATCH_HISTORY_URL = 'https://user.corridordigital.com/v1/watchHistory'

# Video progress report: POST {currentTime, totalTime, durationWatched} (all ms)
# uid = video UUID from video info, video_id = numeric ID
VIDEO_REPORT_URL = 'https://user.corridordigital.com/v1/videoReport/{uid}?platform=Web&videoId={video_id}'

# Device identifier (stored in settings)
DEVICE_ID_SETTING = 'device_id'

# Percentage >= this = mark as watched in Kodi
WATCHED_THRESHOLD = 90
