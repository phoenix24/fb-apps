#!/usr/bin/env python
# coding: utf-8

import os
# dummy config to enable registering django template filters
os.environ[u'DJANGO_SETTINGS_MODULE'] = u'conf'

from django.template.defaultfilters import register
from django.utils import simplejson as json
from functools import wraps
from google.appengine.api import urlfetch
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from random import randrange
from uuid import uuid4
import Cookie
import base64
import cgi
import conf
import datetime
import hashlib
import hmac
import logging
import time
import traceback
import urllib

from facebook import FacebookApiError, Facebook
from models import Pick, User, Match, Utils
from models import PickException
from conf import *

def htmlescape(text):
    """Escape text for use as HTML"""
    return cgi.escape(
        text, True).replace("'", '&#39;').encode('ascii', 'xmlcharrefreplace')


@register.filter(name=u'get_name')
def get_name(dic):
    """Django template filter to render name"""
    return dic["name"]


@register.filter(name=u'get_picture')
def get_picture(dic):
    """Django template filter to render picture"""
    path = "http://graph.facebook.com/%s/picture" % dic["id"]
    return path


def user_required(fn):
    """Decorator to ensure a user is present"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        handler = args[0]
        if handler.user:
            return fn(*args, **kwargs)
        handler.redirect(u'/')
    return wrapper


def admin_required(fn):
    """Decorator to ensure a user is present"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        handler = args[0]
        if handler.user and handler.user.user_id in ADMIN_USER_IDS:
            return fn(*args, **kwargs)
        handler.redirect(u'/')
    return wrapper


class BaseHandler(webapp.RequestHandler):
    facebook = None
    user = None
    csrf_protect = True

    def initialize(self, request, response):
        """General initialization for every request"""
        super(BaseHandler, self).initialize(request, response)

        try:
            self.init_facebook()
            self.init_csrf()
            self.response.headers[u'P3P'] = u'CP=HONK'  # cookies in iframes in IE
        except:
            logging.error('initialize: \n' + traceback.format_exc())
            raise

    def handle_exception(self, exception, debug_mode):
        trace = traceback.format_exc()
        logging.error('handle_exception: \n' + trace)
        self.render(u'error', trace=trace, debug_mode=debug_mode)

    def set_cookie(self, name, value, expires=None):
        """Set a cookie"""
        if value is None:
            value = 'deleted'
            expires = datetime.timedelta(minutes=-50000)
        jar = Cookie.SimpleCookie()
        jar[name] = value
        jar[name]['path'] = u'/'
        if expires:
            if isinstance(expires, datetime.timedelta):
                expires = datetime.datetime.now() + expires
            if isinstance(expires, datetime.datetime):
                expires = expires.strftime('%a, %d %b %Y %H:%M:%S')
            jar[name]['expires'] = expires
        self.response.headers.add_header(*jar.output().split(u': ', 1))

    def render(self, name, **data):
        """Render a template"""
        if not data:
            data = {}
        data[u'js_conf'] = json.dumps({
            u'appId': conf.FACEBOOK_APP_ID,
            u'canvasName': conf.FACEBOOK_CANVAS_NAME,
            u'userName': self.user.name if self.user else None,
            u'userIdOnServer': self.user.user_id if self.user else None,
        })
        data[u'logged_in_user'] = self.user
        data[u'message'] = self.get_message()
        data[u'csrf_token'] = self.csrf_token
        data[u'canvas_name'] = conf.FACEBOOK_CANVAS_NAME
        self.response.out.write(template.render(
            os.path.join(
                os.path.dirname(__file__), 'templates', name + '.html'),
            data))

    def init_facebook(self):
        """Sets up the request specific Facebook and User instance"""
        facebook = Facebook()
        user = None

        # initial facebook request comes in as a POST with a signed_request
        if u'signed_request' in self.request.POST:
            facebook.load_signed_request(self.request.get('signed_request'))
            # we reset the method to GET because a request from facebook with a
            # signed_request uses POST for security reasons, despite it
            # actually being a GET. in webapp causes loss of request.POST data.
            self.request.method = u'GET'
            self.set_cookie(
                'u', facebook.user_cookie, datetime.timedelta(minutes=1440))
        elif 'u' in self.request.cookies:
            facebook.load_signed_request(self.request.cookies.get('u'))

        # try to load or create a user object
        if facebook.user_id:
            user = User.get_by_key_name(facebook.user_id)
            if user:
                # update stored access_token
                if facebook.access_token and \
                        facebook.access_token != user.access_token:
                    user.access_token = facebook.access_token
                    user.put()
                # refresh data if we failed in doing so after a realtime ping
                if user.dirty:
                    user.refresh_data()
                # restore stored access_token if necessary
                if not facebook.access_token:
                    facebook.access_token = user.access_token

            if not user and facebook.access_token:
                me = facebook.api(u'/me', {u'fields': u'picture,friends'})
                user = User(key_name=facebook.user_id,
                    user_id=facebook.user_id,
                    access_token=facebook.access_token,
                    name=me[u'name'],
                    email=me.get(u'email'),  # optional
                    picture=me[u'picture'],
                    friends=[user[u'id'] for user in me[u'friends'][u'data']])
                user.put()

        self.facebook = facebook
        self.user = user

    def init_csrf(self):
        """Issue and handle CSRF token as necessary"""
        self.csrf_token = self.request.cookies.get(u'c')
        if not self.csrf_token:
            self.csrf_token = str(uuid4())[:8]
            self.set_cookie('c', self.csrf_token)
        if self.request.method == u'POST' and self.csrf_protect and \
                self.csrf_token != self.request.POST.get(u'_csrf_token'):
            raise Exception(u'Missing or invalid CSRF token.')

    def set_message(self, **obj):
        """Simple message support"""
        self.set_cookie('m', base64.b64encode(json.dumps(obj)) if obj else None)

    def get_message(self):
        """Get and clear the current message"""
        message = self.request.cookies.get(u'm')
        if message:
            self.set_message()  # clear the current cookie
            return json.loads(base64.b64decode(message))


class RefreshUserHandler(BaseHandler):
    csrf_protect = False

    """Refresh user data using if possible"""
    def post(self, user_id):
        logging.info('Refreshing user data for ' + user_id)
        user = User.get_by_key_name(user_id)
        if not user:
            return
        try:
            user.refresh_data()
        except FacebookApiError:
            user.dirty = True
            user.put()


class WelcomeHandler(BaseHandler):
    """Show recent runs for the user and friends"""
    def get(self):
        if self.user: # and self.user.has_picked() == 0:
            friends = {}
#            friends = self.user.get_friends()
            self.render(u'pick', friends=friends,)
			
        elif self.user and self.user.has_picked() != 0:
            self.redirect(u'/user')
			
        else:
            self.render(u'pick')


class PickHandler(BaseHandler):
    """Add a run"""
    @user_required
    def post(self):
        try:
            choice0 = self.request.POST[u'choice0'].strip()
            choice1 = self.request.POST[u'choice1'].strip()
            choice2 = self.request.POST[u'choice2'].strip()
            choiceid0 = self.request.POST[u'choiceid0'].strip()
            choiceid1 = self.request.POST[u'choiceid1'].strip()
            choiceid2 = self.request.POST[u'choiceid2'].strip()
            
            if not choice0 or not choiceid0:
                raise PickException(u'Hey! feed atleast one valentine pick.')

            if not choice1 or not choiceid1:
                raise PickException(u'Hey! feed atleast one valentine pick.')

            if not choice2 or not choiceid2:
                raise PickException(u'Hey! feed atleast one valentine pick.')

            date = datetime.datetime.now()

            pick = Pick(
                user_id=self.user.user_id,
                user_name=self.user.name,
                choice0=choice0,
                choice1=choice1,
                choice2=choice2,
                choiceid0=choiceid0,
                choiceid1=choiceid1,
                choiceid2=choiceid2,
                date=date,
            )
            pick.put()
#            self.set_message(type=u'success', content=u'Added your pick. ')

        except PickException, e:
            self.set_message(type=u'error', content=unicode(e))
			
        except KeyError:
            self.set_message(type=u'error', content=u'Yo! take a pick.')
			
        except ValueError:
            self.set_message(type=u'error', content=u'Yo! take a pick.')
			
        except Exception, e:
            self.set_message(type=u'error', content=u'Unknown error occured. (' + unicode(e) + u')')
            
        self.redirect(u'/user')


class UserHandler(BaseHandler):
    """Show a specific user's runs, ensure friendship with the logged in user"""
    @user_required
    def get(self):
        rating = self.user.get_rating()
        self.render(u'user',
                    rating=rating,)


class AdminHandler(BaseHandler):
    
    @admin_required
    def get(self):
        logging.info( "#2 ADMIN Deleting Missing Picks;" )
        
        values = {
#           "users" : User.all(),
           "matches" : Match.all(),
#           "picks" : Pick.all().fetch(20),
        }
        self.render(u'admin', values=values)
        
    @admin_required
    def post(self):
        try:
            action = self.request.POST[u'action'].strip()
            
            if not action:
                raise Exception(u'Hey! feed atleast one valentine pick.')
            
            if action == "update_matches":
                Utils.update_matches_all()
            
            if action == "notify_matches":
                Utils.notify_matches_all()
            
            
            
        except Exception, e:
            self.set_message(type=u'error',
                content=u'Unknown error occured. (' + unicode(e) + u')')
            
        self.redirect(u'/admin')
    

def main():
    routes = [
        (r'/', WelcomeHandler),
        (r'/pick', PickHandler),
        (r'/user', UserHandler),
        (r'/admin', AdminHandler),
        (r'/task/refresh-user/(.*)', RefreshUserHandler),
    ]
    application = webapp.WSGIApplication(routes,
        debug=os.environ.get('SERVER_SOFTWARE', '').startswith('Dev'))
#    application = webapp.WSGIApplication(routes, debug=True)
    util.run_wsgi_app(application)

if __name__ == u'__main__':
    main()
