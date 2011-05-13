#!/usr/bin/env python
# coding: utf-8

import os
# dummy config to enable registering django template filters
os.environ[u'DJANGO_SETTINGS_MODULE'] = u'conf'

from django.template.defaultfilters import register
from django.utils import simplejson as json
from functools import wraps
from google.appengine.api import urlfetch
#from google.appengine.api.labs import taskqueue
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

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

from conf import *
from facebook import FacebookApiError, Facebook
from models import User, Utils, Match, Bet

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


class AdminHandler(BaseHandler):
    """ handles the basic app administration. """
    
    @admin_required
    def get(self):
        logging.info( "#1 admin, settings. " )
        
        matches = Match.all()
        
        self.render(u'admin',
                    matches = matches)
        
    @admin_required
    def post(self):
        date = self.request.POST[u'date'].strip()
        time = self.request.POST[u'time'].strip()
        team1 = self.request.POST[u'team1'].strip()
        team2 = self.request.POST[u'team2'].strip()
        location = self.request.POST[u'location'].strip()
        timestamp = datetime.datetime(2011, 02, 16, 20, 30, 15)
        
        key_name = "%s_%s_%s" % (team1, team2, timestamp.strftime("%Y_%m_%d_%H_%M_%S"))
        
        match = Match(team1 = team1,
                      team2 = team2,
                      key_name = key_name,
                      timestamp = timestamp,
                      )
        match.put()
        
        self.redirect(u'/admin')
        
        
class IndexHandler(BaseHandler):
    """Show recent runs for the user and friends"""
    def get(self):
        
        if self.user:
            self.render(u'bet', )
        else:
            self.render(u'index')
            
    
class BetHandler(BaseHandler):
    
    @user_required
    def get(self):
        self.render(u'bet', )
    
    @user_required
    def post(self):
        match1 = self.request.POST[u'match1'].strip()
        match2 = self.request.POST[u'match2'].strip()
        
        logging.info("match1 : " + match1)
        logging.info("match2 : " + match2)
        
        self.render(u'user', values = { "match1" : match1, "match2" : match2 })
        


class UserHandler(BaseHandler):
    """Show a specific user's runs, ensure friendship with the logged in user"""
    
    
    @user_required
    def get(self):
        
        self.render(u'user', )

class LeaderBoardHandler(BaseHandler):
    """ returns the leaderboard. """
    
    @user_required
    def get(self):
        self.render(u'leaderboard')

class ScheduleHandler(BaseHandler):
    """ returns the match schedule. """
    
    @user_required
    def get(self):
        self.render(u'schedule')

def main():
    routes = [
        (r'/', IndexHandler),
        (r'/bet', BetHandler),
        (r'/user', UserHandler),
        (r'/schedule', ScheduleHandler),
        (r'/leaderboard', LeaderBoardHandler),
        (r'/admin', AdminHandler),
    ]
    application = webapp.WSGIApplication(routes,
        debug=os.environ.get('SERVER_SOFTWARE', '').startswith('Dev'))
#    application = webapp.WSGIApplication(routes, debug=True)
    util.run_wsgi_app(application)

if __name__ == u'__main__':
    main()
