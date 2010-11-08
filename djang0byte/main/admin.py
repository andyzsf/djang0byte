# -*- coding: utf-8 -*-
from django.contrib import admin
from main.models import Post, Blog, Profile, Comment, Answer, AnswerVote


admin.site.register(Post)
admin.site.register(Blog)
admin.site.register(Profile)
admin.site.register(Comment)
admin.site.register(Answer)
admin.site.register(AnswerVote)
