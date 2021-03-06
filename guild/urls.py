# coding: utf-8
# Author: Vova Zaytsev <zaytsev@usc.edu>

from django.conf.urls import url
from django.conf.urls import patterns

from django.conf import settings
from django.conf.urls.static import static

from api import views as api
from app import views as app

urlpatterns = patterns("",

    url(r"^$",                      app.debug_page),

    url(r"api/idea/get/$",          api.idea_get),
    url(r"api/idea/list/$",         api.idea_list),
    url(r"api/idea/vote/$",         api.idea_vote),
    url(r"api/idea/part/$",         api.idea_part),
    url(r"api/idea/create/$",       api.idea_create),
    url(r"api/idea/update/$",       api.idea_update),
    url(r"api/idea/remove/$",       api.idea_remove),

    url(r"api/pic/upload/$",        api.pic_upload),
    url(r"api/pic/remove/$",        api.pic_remove),

    url(r"api/profile/get/$",       api.profile_get),
    url(r"api/profile/create/$",    api.profile_create),
    url(r"api/profile/update/$",    api.profile_update),

    url(r"api/comment/get/$",       api.comment_get),
    url(r"api/comment/create/$",    api.comment_create),
    url(r"api/comment/delete/$",    api.comment_remove),

)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
