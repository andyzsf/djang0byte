# -*- coding: utf-8 -*-
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
from django_push.publisher import ping_hub

from treebeard.ns_tree import NS_Node
from django.contrib.auth.models import User
from django.db import models
import tagging
from tagging.fields import TagField
from tagging.models import Tag
from timezones.fields import TimeZoneField
from main.utils import new_notify_email
from settings import TIME_ZONE, VALID_TAGS, VALID_ATTRS, NEWPOST_RATE, NEWBLOG_RATE, NEWCOMMENT_RATE, RATEPOST_RATE, DEFAULT_AVATAR, PUSH_HUB, FEED_URL, RATEBLOG_RATE
from settings import RATECOM_RATE, RATEUSER_RATE, POST_RATE_COEFFICIENT, BLOG_RATE_COEFFICIENT, COMMENT_RATE_COEFFICIENT, PUBSUB, ONLINE_TIME
from utils import file_upload_path, Access, get_status, new_notify_email
from parser import utils
from django.utils.translation import gettext as _
import parser.utils
from urlparse import urlparse
import datetime
from django.db.models import Q

class BlogType(models.Model):
    """Types of blog"""
    name = models.CharField(max_length=30, verbose_name=_('Name'))
    display_default = models.BooleanField(default=True, verbose_name=_('Display in "all"?'))
    is_qa = models.BooleanField(default=False, verbose_name=_('Is Q&A?'))

    @staticmethod
    def check(name):
        """Check for exist

        Keyword arguments:
        name -- String

        Returns: Boolean

        """
        try:
            bt = BlogType.objects.get(name=name)
            return True
        except BlogType.DoesNotExist:
            return False

    def get_blogs(self):
        """Return blogs in type"""
        return Blog.objects.filter(type=self)

    def __unicode__(self):
        """Return self name"""
        return self.name

    class Meta:
        verbose_name = _("Blog type")
        verbose_name_plural = _("Blogs types")


class Blog(models.Model):
    """Blog entrys"""
    name = models.CharField(max_length=30, verbose_name=_('Blog name'))
    owner = models.ForeignKey(User, verbose_name=_('Owner of blog'))
    description = models.TextField(verbose_name=_('Blog description'))
    rate = models.IntegerField(default=0, verbose_name=_('Blog rate'))
    rate_count = models.IntegerField(default=0, verbose_name=_('Count of raters'))
    type = models.ForeignKey(BlogType, verbose_name=_('Blog type'))
    default = models.BooleanField(default=False, verbose_name=_('Does not need join?'))
    avatar = models.ImageField(upload_to=file_upload_path, blank=True, null=True, verbose_name=_('Blog picture'))

    
    def get_users(self):
        """Get users in this blog"""
        return UserInBlog.objects.select_related('user').filter(blog=self)
    
    def check_user(self, user):
        """Check user in blog
        
        Keyword arguments:
        user -- User
        
        Returns: Boolean
        
        """
        try:
            userInBlog = UserInBlog.objects.get(user=user, blog=self)
            return True
        except UserInBlog.DoesNotExist:
            return False
        
    def get_posts(self):
        """Get posts in blog"""
        return Post.objects.filter(blog=self)
        
    def rate_blog(self, user, value):
        """Rate blog
        
        Keyword arguments:
        user -- User
        value -- Integer
        
        Returns: Boolean
        
        """
        if BlogRate.objects.filter(blog=self, user=user).count():
            return False
        else:
            self.rate += value
            self.rate_count += 1
            self.save()
            BlogRate.objects.create(
                blog=self,
                user=user,
            )
            Profile.objects.filter(
                user=self.owner
            ).update(
                blogs_rate=models.F('blogs_rate') + value
            )
            return True
                
    def add_or_remove_user(self, user):
        """add or remove user from blog
        
        Keyword arguments:
        user -- User
        
        Returns: None
        
        """
        user_in_blog, created = UserInBlog.objects.get_or_create(
            user=user,
            blog=self,
        )
        if not created:
            user_in_blog.delete()

    def get_avatar(self):
        try:
            return self.avatar.url
        except ValueError:
            return False

    @staticmethod
    def create_list(profile, selected = None, append=None):
        blogs = [uib.blog for uib in profile.get_blogs()]
        blogs += Blog.objects.filter(default=True)
        if append:
            append.selected = True
            blogs.append(append)
        d = {}
        for x in blogs:
            if selected == x.id:
                x.selected = True
            d[x]=x
        blogs = d.values()
        return blogs
                
    def __unicode__(self):
        """Return blog name"""
        return self.name

    class Meta:
        verbose_name = _("Blog")
        verbose_name_plural = _("Blogs")


class City(models.Model):
    """All of cities"""
    name = models.CharField(max_length=60, verbose_name=_('Name of city'))
    count = models.IntegerField(verbose_name=_('Users from this city'), default=0)

    @staticmethod
    def get_city(name):
        """Get city from name (create if it doesn't exis)

        Keyword arguments:
        name -- String

        Returns: City

        """
        city, created = City.objects.get_or_create(
            name=name,
        )
        city.count += 1
        city.save()
        return city

    def __unicode__(self):
        """Return name"""
        return self.name

    def get_count(self):
        return Profile.objects.filter(city=self).count()

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")


class Draft(models.Model):
    """Drafts model"""
    TYPE_POST = 0
    TYPE_LINK = 1
    TYPE_TRANSLATE = 2
    TYPE_ANSWER = 3
    TYPE_MULTIPLE_ANSWER = 4
    POST_TYPE = (
        (TYPE_POST, _('Post')),
        (TYPE_LINK, _('Link')),
        (TYPE_TRANSLATE, _('Translate')),
        (TYPE_ANSWER, _('Answer')),
        (TYPE_MULTIPLE_ANSWER, _('Multiple Answer')),
    )

    author = models.ForeignKey(User, verbose_name=_('Author'))
    blog = models.ForeignKey(Blog, blank=True, null=True, verbose_name=_('Blog'))
    title = models.CharField(max_length=300, verbose_name=_('Post title'), default=_('No name'))
    text = models.TextField(blank=True, verbose_name=_('Main text'))
    type = models.IntegerField(choices=POST_TYPE, default=0, verbose_name=_('Type of post'))
    addition = models.CharField(max_length=500, blank=True, verbose_name=_('Addition field'))
    raw_tags = models.CharField(max_length=500, blank=True, null=True, default='')
    is_draft = models.BooleanField(default=True)

    def set_blog(self, blog, force=False):
        """Set blog to post

        Keyword arguments:
        blog -- Blog

        Returns: Blog

        """
        if not int(blog):
            self.blog = None
        else:
            self.blog = Blog.objects.get(id=blog)
            if not (self.blog.default or self.blog.check_user(self.author) or force):
                 self.blog = None
        return self.blog

    def set_data(self, data):
        """Set data to drfat

        Keyword arguments:
        data -- Array

        Returns: None

        """
        for attr in data:
            if attr not in ('blog', 'tags'):
                setattr(self, attr, data[attr])
        try:
            self.set_blog(data['blog'])
        except KeyError:
            self.set_blog(0)
        self.raw_tags = data['tags']

    def save(self, edit=False, rate=False, parsed=False):
        """Save function wrapper

        Keyword arguments:
        edit -- Boolean

        Returns: None

        """
        if not rate:
            if not self.title:
                self.title = _('No name')
            if not parsed:
                self.text = utils.parse(self.text, VALID_TAGS, VALID_ATTRS)
        super(Draft, self).save()

class Post(Draft):
    """Posts table"""
    date = models.DateTimeField(default=datetime.datetime.now(), editable=False, verbose_name=_('Date'))
    rate = models.IntegerField(default=0, verbose_name=_('Post rate'))
    rate_count = models.IntegerField(default=0, verbose_name=_('Count of raters'))
    preview = models.TextField(blank=True, verbose_name=_('Preview text'))
    tags = TagField(verbose_name=_('Tags'), blank=True, null=True)
    disable_reply = models.BooleanField(default=False, verbose_name=_('Disable reply'))
    disable_rate = models.BooleanField(default=False, verbose_name=_('Disable rate'))
    pinch = models.BooleanField(default=False, verbose_name=_('Pinch post'))
    solved = models.BooleanField(default=False, verbose_name=_('Is solved'))
    right_answer = models.ForeignKey('Comment', blank=True, null=True, related_name='right_answer', verbose_name=_('Right answer'))

    class Meta:
        ordering = ('-id', )

    @classmethod
    def from_draft(cls, draft):
        """Create post from draft

        Keyword arguments:
        draft -- Draft

        Returns: Post

        """
        cls = cls()
        for attr in ('author', 'blog', 'title', 'type', 'text', 'addition', 'raw_tags'):
            setattr(cls, attr, getattr(draft, attr))
        cls.save()
        draft.delete()
        return cls
    
    def set_data(self, data):
        """Set data to post

        Keyword arguments:
        data -- Array

        Returns: None

        """
        Draft.set_data(self, data)
        self.save()


    def get_comment(self):
        """Return first level comments in post"""
        try:
            comments = Comment.objects.filter(post=self, depth=1)[0]
            return comments.get_descendants().select_related('author', 'post', 'post__author')
        except IndexError:
            return None


    def create_comment_root(self):
        """Create comment root for post"""
        comment_root = Comment.add_root(post=self, created=datetime.datetime.now())
        return comment_root
        
    def _get_content(self, type=0):
        """Return post content, 0 - preview, 1 - post
        
        Keyword arguments:
        type -- Integer
        
        Returns: Text
        
        """
        if self.type > 2:
            return Answer.objects.filter(post=self)
        elif not type:
            return self.preview
        else:
            return self.text
	  
    def get_content(self, type=0):
        """_get_content wrapper
        
        Keyword arguments:
        type -- Integer
        
        Returns: Text
        
        """
        return self._get_content(type)
	  
    def get_full_content(self, type=1):
        """Return preview
        
        Keyword arguments:
        type -- Integer
        
        Returns: Text
        
        """
        return self._get_content(1)
	  
    def rate_post(self, user, value):
        """Rate post
        
        Keyword arguments:
        user -- User
        value -- Integer
        
        Returns: Integer
        
        """
        if self.disable_rate or  PostRate.objects.filter(post=self, user=user).count():
            return False
        else:
            self.rate += value
            self.rate_count += 1
            self.save(rate=True)
            PostRate.objects.create(
                post=self,
                user=user,
            )
            Profile.objects.filter(
                user=self.author
            ).update(
                posts_rate=models.F('posts_rate') + value
            )
            return True
            
    def get_tags(self):
        """Return post tags"""
        return Tag.objects.get_for_object(self)
    
    def set_tags(self, tag_list):
        """Set tags for post
        
        Keyword arguments:
        tag_list -- Tag
        
        Returns: None
        
        """
        if not ',' in tag_list:
            tag_list += ','
        Tag.objects.update_tags(self, tag_list)
        
        
    def save(self, edit=True, convert=False, retry=False, rate=False):
        """Parse html and save"""
        if rate:
            tags = ', '.join(x.name for x in self.get_tags())
            super(Post, self).save(rate=True)
            self.set_tags(tags)
            return 0
        self.is_draft = False
        if self.type < 3 and not convert and not retry:
            self.preview, self.text = utils.cut(self.text)
            self.preview = utils.parse(self.preview, VALID_TAGS, VALID_ATTRS)
            self.text = utils.parse(self.text, VALID_TAGS, VALID_ATTRS)
        if not edit:
            if not convert:
                try:
                    if PUBSUB:
                        ping_hub(FEED_URL, hub_url=PUSH_HUB)
                except:
                    pass
                self.date = datetime.datetime.now()
                Notify.new_post_notify(self)
        super(Post, self).save(parsed=True) # Call the "real" save() method

    def is_answer(self, user = None, force = False):
        """Check post type is answer and return questions

        Keyword arguments:
        user -- request.user

        Returns: Array/Boolean

        """
        if self.type < 3:
            return False
        try:
            if force:
                raise
            return self._is_answer
        except:
            try:
                answer = Answer.objects.filter(post=self).all()
                sum = answer.order_by('-count')[0].count
                action = lambda count: int(300 * float(count)/float(sum or 1))
                self._is_answer = [{
                    'count': answ.count,
                    'value': answ.value,
                    'width': action(answ.count),
                    'id': answ.id
                } for answ in answer]
                if user is not None:
                    self.is_result = user.is_authenticated() and not Answer.check(self, user)
                return self._is_answer
            except (Answer.DoesNotExist, IndexError):
                self._is_answer = False
                self.is_result = False
                return False


    def have_cut(self):
        """Check if 'cut' exsisted"""
        return self.text != self.preview


    def __unicode__(self):
        """Return post title"""
        return self.title

    class Meta:
        verbose_name = _("Post")
        verbose_name_plural = _("Posts")
 
    
class Comment(NS_Node):
    """Comments table"""
    post = models.ForeignKey(Post, verbose_name=_('Post'))
    author = models.ForeignKey(User, null=True, blank=True, verbose_name=_('Author'))
    text = models.TextField(blank=True, verbose_name=_('Text'))
    rate = models.IntegerField(default=0, verbose_name=_('Comment rate'))
    rate_count = models.IntegerField(default=0, verbose_name=_('Count of raters'))
    
    # Exception Value: Cannot use None as a query value
    created = models.DateTimeField(editable=False, verbose_name=_('Creation date'))
    
    
    node_order_by = ['created']
    
    def __unicode__(self):
        """Return comment content"""
        return self.text
    
    def save(self):
        """Parse html and save"""
        utils.parse(self.text, VALID_TAGS, VALID_ATTRS)
        super(Comment, self).save() # Call the "real" save() method
    
    @models.permalink
    def get_absolute_url(self):
        return ('node-view', ('ns', str(self.id), ))
    
    def get_margin(self):
        """Get margin from comment tree"""
        return (self.depth - 2) * 20

    @staticmethod
    def get_last(obj, date):
        """Get lasts comment

        Keyword arguments:
        obj -- Comment
        date -- datetime

        Returns: Comment QuerySet
        """
        while True:
            try:
                obj = obj.get_children().filter(created__lt=date).order_by('-created')[0]
            except IndexError:
                return obj


    def get_placceholder(self):
        """Get comment holder"""
        return Comment.get_last(self.get_parent(), self.created)
        #return self.get_parent()

    def get_parent_id(self):
        """Get parent comment id"""
        try:
            return self.get_parent().id
        except:
            return self.id
        
    def rate_comment(self, user, value):
        """Rate Comment
        
        Keyword arguments:
        user -- User
        value -- Integer
        
        Returns: Boolean
        
        """
        if CommentRate.objects.filter(comment=self, user=user).count():
            return False
        else:
            self.rate += value
            self.rate_count += 1
            CommentRate.objects.create(
                user=user,
                comment=self,
            )
            Profile.objects.filter(
                user=self.author
            ).update(
                comments_rate=models.F('comments_rate') + value
            )
            self.save()
            return True

    class Meta:
        ordering = ['id']
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")


class UserInBlog(models.Model):
    """Compared list of users and blogs"""
    user = models.ForeignKey(User)
    blog = models.ForeignKey(Blog)

    def __unicode__(self):
        return self.blog.name

    def id(self):
        """Over write id method"""
        return self.blog.id

    class Meta:
        verbose_name = _("User in blog list")
        verbose_name_plural = _("Users in blogs list")


class BlogWithUser(UserInBlog):
    """Abstract class"""
    def __unicode__(self):
        return self.parent.user.username

    class Meta:
        abstract = True


class Profile(models.Model):
    """User profile"""
    user = models.ForeignKey(User, unique=True, verbose_name=_('User'))
    city = models.ForeignKey(City, blank=True, null=True, verbose_name=_('City'))
    icq = models.CharField(max_length=10, blank=True, verbose_name=_('Icq'))
    jabber = models.EmailField(max_length=60, blank=True, verbose_name=_('Jabber'))
    site = models.URLField(blank=True, verbose_name=_('Web site'))
    rate = models.IntegerField(default=0, verbose_name=_('Personal rate'))
    rate_count = models.IntegerField(default=0, verbose_name=_('Count of raters'))
    posts_rate = models.IntegerField(default=0, verbose_name=_('Rate earned by posts'))
    comments_rate = models.IntegerField(default=0, verbose_name=_('Rate earned by comments'))
    blogs_rate = models.IntegerField(default=0, verbose_name=_('Rate earned by blogs'))
    timezone = TimeZoneField(default=TIME_ZONE, verbose_name=_('Timezone'))
    avatar = models.ImageField(upload_to=file_upload_path, blank=True, null=True, verbose_name=_('User picture'))
    hide_mail = models.BooleanField(default=True, verbose_name=_('Show email?'))
    reply_post = models.BooleanField(default=True, verbose_name=_('Send notify about reply to post?'))
    reply_comment = models.BooleanField(default=True, verbose_name=_('Send notify about reply to comment?'))
    reply_pm = models.BooleanField(default=True, verbose_name=_('Send notify about PM?'))
    reply_mention = models.BooleanField(default=True, verbose_name=_('Send notify about mention?'))
    reply_spy = models.BooleanField(default=True, verbose_name=_('Send notify about spy?'))
    about = models.TextField(blank=True, verbose_name=_('About'))
    other = models.TextField(blank=True, verbose_name=_('Field for addition'))

    def get_posts(self):
        """Get posts by user"""
        return Post.objects.filter(author=self.user)

    def get_city(self):
        """Get user city"""
        if self.city:
            return self.city.name
        else:
            return False
        
    def get_friends(self, friend_with_me = False):
        """Get user friends"""
        if friend_with_me:
            return Friends.objects.select_related('user').filter(friend=self.user)
        return Friends.objects.select_related('friend').filter(user=self)

    def get_blogs(self):
        """Get blogs contain it"""
        return UserInBlog.objects.select_related('blog').filter(user=self.user)
        
    def rate_user(self, user, value):
        """Rate user
        
        Keyword arguments:
        user -- User
        value -- Integer
        
        Returns: Integer
        
        """
        if not UserRate.objects.get(user=self):
            self.rate += value
            self.rate_count += 1
            rate = UserRate()
            rate.profile = self
            rate.user = user
            rate.save()
            return(True)
        else:
            return(False)

    def get_rate(self):
        """Get user rate"""
        return(self.rate + self.posts_rate * POST_RATE_COEFFICIENT
               + self.blogs_rate * BLOG_RATE_COEFFICIENT
               + self.comments_rate * COMMENT_RATE_COEFFICIENT)

    def check_access(self, type):
        """Check user access

        Keyword arguments:
        type -- Access:

        Returns: Boolean

        """
        rate = self.get_rate()
        if type == Access.new_blog and rate >= NEWBLOG_RATE:
            return True
        elif type == Access.new_comment and rate >= NEWCOMMENT_RATE:
            return True
        elif type == Access.new_post and rate >= NEWPOST_RATE:
            return True
        elif type == Access.rate_comment and rate >= RATECOM_RATE:
            return True
        elif type == Access.rate_blog and rate >= RATEBLOG_RATE:
            return True
        elif type == Access.rate_post and rate >= RATEPOST_RATE:
            return True
        elif type == Access.rate_user and rate >= RATEUSER_RATE:
            return True
        else:
            return False

    def post_count(self):
        """Return post count"""
        return int(Post.objects.filter(author=self.user).count() or 0)

    def comment_count(self):
        """Return comment count"""
        return int(Comment.objects.filter(author=self.user).count())

    def get_avatar(self):
        """Get url of user avatar"""
        try:
            return self.avatar.url
        except ValueError:
            return DEFAULT_AVATAR

    def get_me_on(self):
        """Return array of sites, where user is registered"""
        try:
            return self._getmeon
        except:
            pass
        try:
            class num:
                val = -1
                def inc(self):
                    self.val += 1
                    return True
            num = num()
            meon = MeOn.objects.filter(user=self.user)
            statused = Statused.objects.filter(user=self.user).all()
            for site in statused:
                meon = meon.exclude(url=site.url)
            action = lambda site: num.inc() and {
                'url': site.url,
                'title': site.title,
                'statused': False,
                'show': False,
                'num': num.val
            }
            action_statused = lambda site: site.get_status() and num.inc() and {
                'url': site.url,
                'title': site.title,
                'statused': True,
                'show': site.show,
                'num': num.val
            }
            self._getmeon = ([action(site) for site in meon] +
                   [action_statused(site) for site in statused])
            return self._getmeon
        except MeOn.DoesNotExist:
            return False

    def get_status(self):
        """Get array of user statuses from other sites"""
        try:
            return self._status
        except:
            self._status = [{
                'obj': service ,
                'text': service.get_status()
            } for service in Statused.objects.filter(user=self.user, show=True)]
            return self._status

    def is_my_friend(self, user):
        """Check friends

        Keyword arguments:
        user -- User

        Returns: Integer
        """
        if user.is_authenticated():
            try:
                Friends.objects.get(user=user,friend=self.user)
                is_my_friend = 1
            except Friends.DoesNotExist:
                is_my_friend = 0
        else:
            is_my_friend = -1
        return is_my_friend

    def update_last_visit(self):
        """Update last site visit time"""
        try:
            view = LastVisit.objects.get(user=self.user)
            view.date = datetime.datetime.now()
            view.save()
        except LastVisit.DoesNotExist:
            view = LastVisit(user=self.user)
            view.save()

    def is_online(self):
        """Check online status"""
        try:
            LastVisit.objects.get(
                user=self.user,
                date__gt=datetime.datetime.now() - datetime.timedelta(seconds=ONLINE_TIME)
            )
            return True
        except LastVisit.DoesNotExist:
            return False

    def get_block(self):
        """Get bans and blocks"""
        try:
            block = Blocks.objects.get(who=self.user)
            if block.check():
                return block
            else:
                return None
        except Blocks.DoesNotExist:
            return None

    def __unicode__(self):
        """Return username"""
        return self.user.username

    class Meta:
        verbose_name = _("User profile")
        verbose_name_plural = _("User profiles")


class Friends(models.Model):
    """Friends table"""
    friend = models.ForeignKey(User, verbose_name=_('Friend'))
    user = models.ForeignKey(Profile, verbose_name=_('User'))

    def __unicode__(self):
        """Return friend name"""
        return self.friend.username

    class Meta:
        verbose_name = _("Friend")
        verbose_name_plural = _("Friends")


class Answer(models.Model):
    """Answers class"""
    post = models.ForeignKey(Post, verbose_name=_('Post'))
    count = models.IntegerField(default=0, verbose_name=_('Count of choose'))
    value = models.TextField(verbose_name=_('Answer variant'))
    
    def fix(self, user):
        """Fixate votes and block next vote
        
        Keyword arguments:
        user -- User
        
        Returns: None
        
        """
        vote = AnswerVote()
        vote.answer = self.post
        vote.user = user
        vote.save()
    
    def _vote(self, user, multiple=False):
        """Vote to answer
        
        Keyword arguments:
        user -- User
        multiple -- Boolean
        
        Returns: Boolean
        
        """
        if not multiple:
            self.fix(user)
        self.count += 1
        self.save()
        
    @staticmethod
    def check(post, user):
        """Check vote access
        
        Keyword arguments:
        post -- Post
        user -- User
        
        Returns: Boolean
        
        """
        try:
            vote = AnswerVote.objects.filter(answer=post, user=user)[0]     
            return False
        except 	IndexError:
            return True
	    
    def vote(self, user, multiple=False):
        """Vote to answer
        
        Keyword arguments:
        user -- User
        multiple -- Boolean
        
        Returns: Boolean
        
        """
        if Answer.check(self.post, user) or multiple:
            self._vote(user)
            return True
        else:
            return False
            
    def __unicode__(self):
        """Return value"""
        return self.value

    class Meta:
        verbose_name = _("Answer variant")
        verbose_name_plural = _("Answers variants")

	    
class AnswerVote(models.Model):
    """Votes for answer"""
    answer = models.ForeignKey(Post, verbose_name=_('Answer'))
    user = models.ForeignKey(User, verbose_name=_('User'))

    class Meta:
        verbose_name = _("Vote to answer log")
        verbose_name_plural = _("Answers votes log")
    
class Favourite(models.Model):
    """Favourite posts table"""
    post = models.ForeignKey(Post, verbose_name=_('Post'))
    user = models.ForeignKey(User, verbose_name=_('User'))

    class Meta:
        verbose_name = _("Favourite post")
        verbose_name_plural = _("Favourite posts")


class Spy(models.Model):
    """Spyed posts table"""
    post = models.ForeignKey(Post, verbose_name=_('Post'))
    user = models.ForeignKey(User, verbose_name=_('User'))

    class Meta:
        verbose_name = _("Post spying")
        verbose_name_plural = _("Post spyings")


class PostRate(models.Model):
    """Post rates"""
    post = models.ForeignKey(Post, verbose_name=_('Post'))
    user = models.ForeignKey(User, verbose_name=_('User'))

    class Meta:
        verbose_name = _("Post rate log")
        verbose_name_plural = _("Post rates log")

    
class CommentRate(models.Model):
    """Comment rates"""
    comment = models.ForeignKey(Comment, verbose_name=_('Comment'))
    user = models.ForeignKey(User, verbose_name=_('User'))

    class Meta:
        verbose_name = _("Comment rate log")
        verbose_name_plural = _("Comment rates log")


class BlogRate(models.Model):
    """Blog rates"""
    blog = models.ForeignKey(Blog, verbose_name=_('Blog'))
    user = models.ForeignKey(User, verbose_name=_('User'))

    class Meta:
        verbose_name = _("Blog rate log")
        verbose_name_plural = _("Blog rates log")


class UserRate(models.Model):
    """User rates"""
    profile = models.ForeignKey(Profile, verbose_name=_('Profile'))#voted
    user = models.ForeignKey(User, verbose_name=_('User'))#who vote

    class Meta:
        verbose_name = _("User rate log")
        verbose_name_plural = _("User rates log")


class Notify(models.Model):
    """Class contain notifys for 'lenta'"""
    user = models.ForeignKey(User, verbose_name=_('User'))
    post = models.ForeignKey(Post, verbose_name=_('Post'), blank=True, null=True)
    comment = models.ForeignKey(Comment, verbose_name=_('Comment'), blank=True, null=True)
    
    @classmethod
    def new_notify(self, is_post, alien, user):
        """Create notify
        
        Keyword arguments:
        is_post -- Boolean
        alien -- Post or Comment
        user - User
        
        Returns: Notify
        
        """
        self = Notify()
        self.user = user
        if is_post:
            self.post = alien
        else:
            self.comment = alien
        self.save()
        return self
            
    @staticmethod
    def new_post_notify(post):
        """Notify for new post
        
        Keyword arguments:
        post -- Post
        
        Returns: None
        
        """
        users = list(Profile.objects.get(user=post.author).get_friends(True))
        #TODO: rewrite this shit
        users = [user.user.user for user in users]
        if post.blog != None:
            users += [blog_user.user for blog_user in post.blog.get_users()]
        d = {}
        for x in users:
            if x != post.author: 
                d[x]=x
        users = d.values()
        for user in users:
            Notify.new_notify(True, post, user)
    
    @staticmethod
    def new_comment_notify(comment):
        """Notify for new comment
        
        Keyword arguments:
        comment -- Comment
        
        Returns: None
        
        """
        if comment.depth == 2:
            try:
                Notify.objects.get(comment=comment, user=comment.post.author)
            except Notify.DoesNotExist:
                print 'fuckfuckdie!'
                Notify.new_notify(False, comment, comment.post.author)
                if comment.post.author.get_profile().reply_post:
                    new_notify_email(comment, 'post_reply', comment.post.author)
                spy = Spy.objects.select_related('user').filter(post=comment.post)
                try:
                    for spy_elem in spy:
                        try:
                            Notify.objects.get(comment=comment, user=spy_elem.user)
                        except Notify.DoesNotExist:
                            Notify.new_notify(False, comment, spy_elem.user)
                            if spy_elem.user.get_profile().reply_spy:
                                new_notify_email(comment, 'spy_reply', spy_elem.user)
                except TypeError:
                    pass
        else:
            try:
                Notify.objects.get(comment=comment, user=comment.get_parent().author)
            except Notify.DoesNotExist:
                Notify.new_notify(False, comment, comment.get_parent().author)
                if comment.get_parent().author.get_profile().reply_comment:
                    new_notify_email(comment, 'comment_reply', comment.get_parent().author)

    @staticmethod
    def new_mention_notify(user, post = None, comment = None):
        """Create notify when user mentioned

        Keyword arguments:
        user -- User
        post -- Post
        comment - Comment

        Returns: Boolean
        """
        try:
            if post.author.username == user:
                return False
        except:
            if comment.author.username == user:
                return False
        try:
            usr = User.objects.get(username=user)
            try:
                Notify.objects.get(post=post, comment=comment, user=usr)
            except Notify.DoesNotExist:
                if usr.get_profile().reply_mention:
                    if post:
                       new_notify_email(post, 'post_mention', usr)
                    else:
                       new_notify_email(comment, 'mention', usr)
                if post:
                    notify = Notify(post=post, user=usr)
                else:
                    notify = Notify(comment=comment, user=usr)
                notify.save()
                return True
        except User.DoesNotExist:
            pass


    def get_type(self):
        """Return notify type"""
        if self.post is not None:
            return 'post'
        else:
            return 'comment'

    def get_post(self):
        """Posts by notify iterator"""
        yield self.post

    def get_comment(self):
        """Comments by notify iterator"""
        yield self.comment

    def get_date(self):
        """Get date of this notify."""
        if self.post is not None:
            return self.post.date
        else:
            return self.comment.created

    def __unicode__(self):
        """Return notify description"""
        if self.post is not None:
            return "post %s -- %s" % (self.post, self.user)
        else:
            return "comment %s -- %s" % (self.comment, self.user)

    class Meta:
        verbose_name = _("Notify")
        verbose_name_plural = _("Notify messages")


class TextPage(models.Model):
    """Page contain a text"""
    url = models.CharField(verbose_name=_('Page url'), max_length=30)
    name = models.CharField(verbose_name=_('Page name'), max_length=30)
    content = models.TextField(verbose_name=_('Content'), blank=True)

    class Meta:
        verbose_name = _("Page")
        verbose_name_plural = _("Text pages")

    def __unicode__(self):
        """Get page content

        Keyword arguments:
        self -- TextPage

        Returns: String

        """
        return self.name


class MeOn(models.Model):
    """User on other site record"""
    url = models.URLField(verbose_name=_("Page url"))
    title = models.CharField(verbose_name=_("Title"), max_length=30)
    user = models.ForeignKey(User, verbose_name=_("User"))

    def is_statused(self):
        """Match url for statused service"""
        parsed = urlparse(self.url)
        for name in Statused.SERVICE_TYPE:
            if name[1] in parsed.netloc.split('.'):
                if name in ('lastfm', 'last'):
                    return {
                        'service': name[0],
                        'username': parsed.path.split('/')[2]
                    }
                else:
                    return {
                        'service': name[0],
                        'username': parsed.path.split('/')[1]
                    }
        return False

    def parse(self, show):
        """Check type and save

        Keyword arguments:
        show -- Boolean

        Returns: Boolean
        """
        type = self.is_statused()
        if 'http' not in self.url:
            self.url = 'http://' + self.url
        if type and len(type) == 2:
            service = Statused()
            service.url = self.url
            service.user = self.user
            service.title = self.title
            service.type = type['service']
            service.name = type['username']
            if show:
                service.show = True
            else:
                service.show = False
            service.save()
            return True
        else:
            self.save()
            return False


    class Meta:
        verbose_name = _("User on other site")
        verbose_name_plural = _("Users on other sites")

class Statused(MeOn):
    """Service with status users"""
    TYPE_LASTFM = 0
    TYPE_TWITTER = 1
    TYPE_JUICK = 2
    SERVICE_TYPE = (
        (TYPE_LASTFM, 'lastfm'),
        (TYPE_TWITTER, 'twitter'),
        (TYPE_JUICK, 'juick')
    )

    show = models.BooleanField(default=True)
    type = models.IntegerField(choices=SERVICE_TYPE, default=0, verbose_name=_('Name of service'))
    name = models.CharField(max_length=30, verbose_name=_('User name in service'))

    def get_status(self):
        """Get status"""
        if not self.type:
            return get_status('http://ws.audioscrobbler.com/1.0/user/%s/recenttracks.rss' % (self.name))
        elif self.type == 1:
            return get_status('http://twitter.com/statuses/user_timeline/%s.rss' % (self.name))
        else:
            return get_status('http://rss.juick.com/%s/blog' % (self.name))

class LastView(models.Model):
    """Post last view time, for checking new comments"""
    date = models.DateTimeField(auto_now=True)
    post = models.ForeignKey(Post)
    user = models.ForeignKey(User)

    def update(self):
        """Update view time"""
        self.date = datetime.datetime.now()
        self.save()

class LastVisit(models.Model):
    """User visit time model"""
    date = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User)

    @staticmethod
    def get_online(time=ONLINE_TIME):
        """Get online users by specified time

        Keyword arguments:
        time -- Integer

        Returns: LastVisit QuerySet        
        """
        return LastVisit.objects.filter(
            date__gt=datetime.datetime.now() - datetime.timedelta(seconds=time)
        ).select_related('user')

    def __unicode__(self):
        return self.user.username

class LentaLastView(models.Model):
    """Last view of lenta time model"""

    date = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User)

    def get_unseen_count(self):
        """Get count of unseen entries in lenta for specific user."""
        return Notify.objects.filter(
            Q(post__date__gt=self.date) | Q(comment__created__gt=self.date),
            user=self.user,
        ).count()

    @classmethod
    def update_last_view(cls, user):
        """Update last time user saw lenta"""
        try:
            view = cls.objects.get(user=user)
            view.date = datetime.datetime.now()
            view.save()
        except cls.DoesNotExist:
            view = cls(user=user)
            view.save()

class Blocks(models.Model):
    """Bans and blocks model"""
    who = models.ForeignKey(User, verbose_name=_("Enemy"))
    date = models.DateTimeField(verbose_name=_('End date'))
    reason = models.TextField(verbose_name=_("Reason"))

    def check(self):
        """Check if ban ended"""
        if datetime.datetime.now() > self.date:
            self.delete()
            return False
        else:
            return True

    def __unicode__(self):
        return "%s: %s" % (self.who.username, self.reason)

    class Meta:
        verbose_name = _("Ban")
        verbose_name_plural = _("Bans")