# coding: utf-8
# Author: Vova Zaytsev <zaytsev@usc.edu>

import os
import re
import gzip
import uuid
import shutil
import imghdr
import string
import requests

from datetime import datetime
from cStringIO import StringIO

from django.db import models
from django.db.models import Q
from api.common import format_iso_datetime
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from djorm_pgfulltext.models import SearchManager
from djorm_pgfulltext.fields import VectorField

try:
    from PIL import Image
except ImportError:
    import Image

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


MAGICAL_TEXT = "#letsdothis"


ALPHABET = string.letters + string.digits
PIC_PATH_SIZE = 8


IDEA_STATUS = {
    "A": "Active",
    "D": "Deleted",
    "C": "Closed",
}

COMMENT_STATUS = {
    "N": "Normal",
    "I": "Important",
    "D": "Deleted",
}


def send_email(to_address, template, context):
    txt_body = render_to_string("email/%s/body.txt" % template, context)
    html_body = render_to_string("email/%s/body.html" % template, context)
    subject = render_to_string("email/%s/subject.txt" % template, context)
    subject = subject.replace("\n", " ")
    msg = EmailMultiAlternatives(subject, txt_body, "#LETSDOTHIS <do.not.reply@mail.letshackthis.com>", (to_address, ))
    msg.attach_alternative(html_body, "text/html")
    msg.send()


class UserProfile(models.Model):

    class Meta:
        db_table = "t_profile"

    user = models.ForeignKey(User, primary_key=True, null=False, unique=True)
    nickname = models.CharField(max_length=64, null=False, blank=False)
    email = models.EmailField(unique=False, null=True, max_length=50)
    email_verified = models.BooleanField(default=False, null=False)
    tagline = models.CharField(max_length=100, null=True, blank=True)
    realm_id = models.CharField(max_length=32, null=False, blank=False)
    realm = models.CharField(max_length=16, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True, null=True)
    pic_id = models.IntegerField(null=True)
    is_verified = models.BooleanField(default=False, null=False)

    def votes(self):
        votes = self.t_votes.values("iid")
        return set((idea["iid"] for idea in votes))

    def gen_pic_path(self):
        dir_name = "%02x" % (self.user_id % 255)
        pic_name = "u__%08x.jpg" % self.user_id
        return dir_name, pic_name

    def json(self, max_ideas=0, ideas=False, activity=False, comments=False, username=False, email=False):

        if ideas:
            ideas = IdeaEntry.objects.select_related("creator") \
                .filter(~Q(status="D")) \
                .filter(creator=self)[:max_ideas]
            ideas = [idea.json(creator=True) for idea in ideas]
        else:
            ideas = None

        if activity:
            activity = self.t_votes.all().select_related("creator")[:max_ideas]
            activity = [idea.json(creator=True) for idea in activity]
        else:
            activity = None

        if username:
            username = self.user.username
        else:
            username = None

        p_json = {
            "uid": self.user_id,
            "username": username,
            "nickname": self.nickname,
            "email": self.email if email else None,
            "is_verified": self.is_verified,
            "tagline": self.tagline,
            "created": format_iso_datetime(self.created),
            "picture": None if self.pic_id is None else "/webapp/usercontent/%s/%s" % self.gen_pic_path(),
            "ideas": ideas,
            "activity": activity,
        }

        if username:
            p_json["username"] = self.user.username

        return p_json


class IdeaEntry(models.Model):

    EMPTY_RE = re.compile("\s+")
    HASHTAG_RE = re.compile("#[a-zA-Z0-9_]+")

    class Meta:
        db_table = "t_idea"
        ordering = ("-num_votes", "-voted", "-created",)

    iid = models.AutoField(primary_key=True, null=False)
    creator = models.ForeignKey(UserProfile, null=False)
    status = models.CharField(max_length=1,
                              default="A",
                              choices=IDEA_STATUS.items(),
                              blank=False,
                              null=False)

    title = models.CharField(max_length=100, null=False, blank=False)
    summary = models.CharField(max_length=1000, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True, null=True)
    voted = models.DateTimeField(auto_now_add=True, null=True)
    updated = models.DateTimeField(auto_now=True, null=True)

    pic_id = models.IntegerField(null=True)
    geo_id = models.IntegerField(null=True)

    votes = models.ManyToManyField(UserProfile, related_name="t_votes")
    members = models.ManyToManyField(UserProfile, related_name="t_members")
    max_members = models.SmallIntegerField(default=-1, null=True)

    num_votes = models.IntegerField(default=0, null=False)
    num_members = models.IntegerField(default=0, null=False)
    num_comments = models.IntegerField(default=0, null=False)

    search_index = VectorField()

    objects = SearchManager(
        fields = ("title", "summary"),
        config = "pg_catalog.english", # this is default
        search_field = "search_index", # this is default
        auto_update_search_field = True
    )


    def add_member(self, profile):
        if profile.user_id != self.creator_id:
            self.members.add(profile)
            self.num_members = self.members.count()
            self.save()

    def add_vote(self, profile):
        if profile.user_id != self.creator_id:
            self.votes.add(profile)
            self.voted = datetime.now()
            self.num_votes = self.votes.count()
            self.save()

    def add_comment(self, profile, text):
        contains_hashtag = MAGICAL_TEXT in text
        members = {m["user_id"] for m in self.members.all().values("user_id")}
        from_member = profile.user_id in members
        from_creator = profile.user_id == self.creator_id
        status = "I" if (from_creator or contains_hashtag or from_member) else "N"
        comment = Comment(creator=profile, idea=self, text=text, status=status)
        comment.save()
        if contains_hashtag:
            self.add_member(profile)
        self.num_comments = Comment.objects.filter(idea=self).count()
        self.save()

        # Send email
        if not from_creator:
            if self.creator.email is not None and len(self.creator.email) > 0:
                # 1) If comment is from new co-hacker
                context = {
                    "creator": self.creator,
                    "initiator": profile,
                    "comment": comment,
                    "idea": self,
                }
                if contains_hashtag and not from_member:
                    send_email(self.creator.email, "new_cohacker", context)
                # 2) If regular comment posted
                else:
                    send_email(self.creator.email, "new_comment", context)

        return comment

    def json(self, creator=False, comments=False, votes=False, members=False, pic=False):

        if creator:
            creator = self.creator.json()
        else:
            creator = self.creator_id

        if comments:
            comments = [comment.json() for comment in Comment.objects.select_related("creator").filter(idea=self)[:25]]
        else:
            comments = None

        if votes:
            votes = [user.json(max_ideas=0,
                               ideas=False,
                               activity=False,
                               comments=False) for user in self.votes.all()[:10]]
        else:
            votes = []

        if members:
            members = [user.json(max_ideas=0,
                                 ideas=False,
                                 activity=False,
                                 comments=False) for user in self.members.all()[:10]]
        else:
            members = None

        if pic and self.pic_id is not None:
            try:
                pic = Picture.objects.get(pid=self.pic_id).path
            except ObjectDoesNotExist:
                pic = None
        else:
            pic = None

        return {

            "iid":          self.iid,
            "pic":          pic,
            "title":        self.title,
            "titleChunks":  IdeaEntry.hashtagify(self.title),
            "creator":      creator,

            "summary":      self.summary,
            "summaryChunks":IdeaEntry.hashtagify(self.summary),
            "created":      format_iso_datetime(self.created),

            "votes":        votes,
            "members":      members,
            "comments":     comments,

            "num_votes":    self.num_votes,
            "num_members":  self.num_members,
            "num_comments": self.num_comments,
        }

    @staticmethod
    def hashtagify(text):
        chunks = []
        prev_pos = 0
        for hashtag in IdeaEntry.HASHTAG_RE.finditer(text):
            h_start, h_end = hashtag.start(), hashtag.end()
            hashtag = text[h_start:h_end]
            chunks.append({
                "t": text[prev_pos:h_start],
            })
            chunks.append({
                "t": hashtag,
                "hw": hashtag[1:],
            })
            prev_pos = h_end
        chunks.append({
            "t": text[prev_pos:],
        })
        return chunks


class Picture(models.Model):

    UPLOADS = "webapp/uploads"
    DOWNLOADS = "webapp/downloads"
    USERCONTENT = "webapp/usercontent"

    class Meta:
        db_table = "t_pic_meta"

    pid = models.AutoField(primary_key=True, null=False)
    path = models.CharField(max_length=64, null=False, blank=False)
    owner = models.ForeignKey(UserProfile, null=True)

    @staticmethod
    def download(pic_url):
        download_path = os.path.join(Picture.DOWNLOADS, uuid.uuid4().hex)
        response = requests.get(pic_url, stream=True)
        with open(download_path, "wb") as pic_file:
            shutil.copyfileobj(response.raw, pic_file)
        return download_path

    @staticmethod
    def upload(data):
        upload_path = os.path.join(Picture.UPLOADS, uuid.uuid4().hex)
        with open(upload_path, "wb") as pic_file:
            pic_file.write(data)
        return upload_path

    @staticmethod
    def store(origin, owner=None, save_to=None, remove_origin=True, resize=False):

        if save_to is None:
            u = uuid.uuid4().hex
            pic_dir = u[:2]
            pic_name = "%s.jpg" % u
        else:
            pic_dir, pic_name = save_to

        path = os.path.join(pic_dir, pic_name)
        pic_meta = Picture(owner=owner, path=path)
        pic_meta.save()

        save_dir = os.path.join(Picture.USERCONTENT, pic_dir)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        save_path = os.path.join(save_dir, pic_name)

        try:
            im = Image.open(origin)
        except IOError:
            with gzip.GzipFile(origin, "r") as stream:
                file_data = stream.read()
            im = Image.open(StringIO(file_data))

        if resize:
            im.thumbnail(resize, Image.ANTIALIAS)
        im.convert("RGB").save(save_path, "JPEG", quality=85)

        if remove_origin:
            os.remove(origin)

        return pic_meta.pid, path


class Comment(models.Model):

    class Meta:
        db_table = "t_comment"
        ordering = ("-created",)

    cid = models.AutoField(primary_key=True, null=False)
    creator = models.ForeignKey(UserProfile, null=False)
    idea = models.ForeignKey(IdeaEntry, null=False)
    status = models.CharField(max_length=1,
                              default="N",
                              choices=COMMENT_STATUS.items(),
                              blank=False,
                              null=False)
    text = models.CharField(max_length=300, null=False, blank=False)
    created = models.DateTimeField(default=datetime.now, null=False)

    def json(self):
        return {
            "cid": self.cid,
            "text": self.text,
            "status": self.status=="I",
            "creator": self.creator.json(max_ideas=0, ideas=False, activity=False, comments=False),
            "created": format_iso_datetime(self.created),
        }
