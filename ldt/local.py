# coding: utf-8
# Author: Vova Zaytsev <zaytsev@usc.edu>

import os
import json
import datetime


def project_dir(dir_name):
    return os.path.join(os.path.dirname(__file__), "..", dir_name)\
        .replace("\\", "//")

# with open(project_dir("conf/dev.json"), "rb") as fp:
#     CONF = json.load(fp)


SECRET_KEY = "h8(e(u3#k)l802(4mfh^f&&jp!@p*s#98tf++l#z-e83(#$x@*"
DEBUG = True
TEMPLATE_DEBUG = True
ALLOWED_HOSTS = ["localhost"]


INSTALLED_APPS = (
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
    "rest_framework",
    "feed",
    "api",
    "app",
)

MIDDLEWARE_CLASSES = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

ROOT_URLCONF = "ldt.urls"
WSGI_APPLICATION = "ldt.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": project_dir("sqilte.db"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_ROOT = "/webapp/"
STATIC_URL = "/webapp/"
STATICFILES_DIRS = (project_dir("webapp"),)
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)
TEMPLATE_LOADERS = (
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
)

TEMPLATE_DIRS = (
    "webapp/templates",
)

LOGGING = {
    "version": 1,

    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
        },
        "simple": {
            "format": "%(levelname)s %(message)s"
        },
    },

    "handlers": {

        "main-log-file": {
            "level": "INFO",
            "class": "logging.handlers.WatchedFileHandler",
            "filename": "logs/app.txt",
            "formatter": "verbose",
        },

        "ldt-log-file": {
            "level": "INFO",
            "class": "logging.handlers.WatchedFileHandler",
            "filename": "logs/ldt.txt",
            "formatter": "verbose",
        },

        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },

    },

    "loggers": {

        "django": {
            "handlers": ["main-log-file", "console"],
            "level": "DEBUG",
            "propagate": True,
        },

        "ldt": {
            "handlers": ["ldt-log-file"],
            "level": "DEBUG",
            "propagate": True
        },
    },
}

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly",
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "api.auth.Auth0Authentication",
    ),
}


# 8 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024