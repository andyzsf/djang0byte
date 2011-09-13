KEYWORD_MIN_COUNT = 50
PUBSUB = False
EMAIL_HOST = 'localhost'
DEFAULT_FROM_EMAIL = 'webmaster@localhost'
ACCOUNT_ACTIVATION_DAYS = 7
AUTH_PROFILE_MODULE = "main.profile"
VALID_TAGS = 'p i em strong b u a h3 pre br img table tr td div pre span cut fcut iframe user spoiler del ol ul li'
VALID_ATTRS = 'href src lang alt class name id style title'
DEFAULT_BLOG_TYPE = 'main'
NEWPOST_RATE = 0
NEWBLOG_RATE = 0
NEWCOMMENT_RATE = 0
RATEPOST_RATE = 0
RATECOM_RATE = 0
RATEUSER_RATE = 0
RATEBLOG_RATE = 0
POST_RATE_COEFFICIENT = 0.3
BLOG_RATE_COEFFICIENT = 0.2
COMMENT_RATE_COEFFICIENT = 0.1
DEFAULT_CACHE_TIME = 0
MENU_CACHE_TIME = 0
SIDEBAR_CACHE_TIME = 0
DEFAULT_AVATAR = '/media/style/figure.gif'
LOGIN_REDIRECT_URL = '/'
RECAPTCHA_PUBLIC_KEY = '6LeLNMISAAAAAI2FBbNBnjf_ms6a5werjXbTbNCk '
RECAPTCHA_PRIVATE_KEY = '6LeLNMISAAAAAMassCnG27qheWXn7Fr_ePSvMP6r '
SITENAME = 'Djang0byte is a capital of'
POST_RATE_TO_MAIN = 0
PUSH_HUB = u'http://pubsubhubbub.appspot.com/'
FEED_URL = u'http://localhost/rss/'
DOMAIN_NAME = 'localhost'
COMPRESS_PARSER = 'compressor.parser.LxmlParser'
COMPRESS = True
COMPRESS_ROOT = "media/"
COMPRESS_YUI_BINARY = '/usr/bin/yui-compressor'
COMPRESS_CSS_FILTERS = ['compressor.filters.yui.YUICSSFilter',]
API_KEY = "API_KEY"
FULLNAME = 'Full site name'
ONLINE_TIME = 600
INTERNAL_IPS = ('127.0.0.1:8000',)



SECRET_KEY = 'r25ofx1lr43d%0yzcwfeog5nxed0^!fe4ck)w!r6et@qejhx*7'
MEDIA_ROOT = ''
SITE_ID = 1
DEBUG = True
TEMPLATE_DEBUG = DEBUG
JOHNNY_MIDDLEWARE_KEY_PREFIX = 'my_project1_jonny_cache_key'
ADMINS = (
     ('Mega Admin', 'email@email.email'),
)

MANAGERS = ADMINS
DATABASE_ENGINE = ''#'postgresql_psycopg2'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.
