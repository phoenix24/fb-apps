#!/usr/bin/env python
# coding: utf-8

import os
# dummy config to enable registering django template filters
os.environ[u'DJANGO_SETTINGS_MODULE'] = u'conf'

from django.template.defaultfilters import register, default
from django.utils import simplejson as json
from functools import wraps
from google.appengine.api import urlfetch, xmpp, mail
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import util, template
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
from conf import *
import urllib2
    
    
class Utils(object):
    """ application utilities. """
    
    
    @staticmethod
    def send_mail(user_id, emailid, message, rating):
        
        sent = False
        try:
            #need to add email validation.
            sender_address = EMAILID_FACEBOOK
            user_address = urllib2.unquote(emailid)
            
            body = EMAILID_FACEBOOK_MATCH_BODY % (message, rating)
            subject = EMAILID_FACEBOOK_MATCH_SUBJECT
            
            """ shoot the notification mail. """
            logging.info("sending %s  to %s (%s) : %s" % (sender_address, user_address, user_id, message))
            mail.send_mail(sender_address, user_address, subject, body)
            
            sent = True
        
        except Exception, e:
            logging.info("error occured while sending email.", e)
            sent = False
        
        return sent
    
    
class User(db.Model):
    date = db.DateTimeProperty()
    user_id = db.StringProperty(required=True)
    access_token = db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    email = db.StringProperty()
    dirty = db.BooleanProperty()
    points = db.IntegerProperty(default=5)
    
    def refresh_data(self):
        """Refresh this user's data using the Facebook Graph API"""
        me = Facebook().api(u'/me',
            {u'fields': u'picture,friends', u'access_token': self.access_token})
        
        self.dirty = False
        self.name = me[u'name']
        self.email = me.get(u'email')
        self.picture = me[u'picture']
        self.friends = [user[u'id'] for user in me[u'friends'][u'data']]
        return self.put()
       
    
class Match(db.Model):
    """ stores the match listing. """
    location = db.StringProperty(default="NA")
    timestamp = db.DateTimeProperty(required=True)
    team1 = db.StringProperty(default="NA", required=True)
    team2 = db.StringProperty(default="NA", required=True)
    result = db.StringProperty(default="NA")
    points = db.IntegerProperty(default=1)
    
    
class Bet(db.Model):
    """ stores all the bets placed by the user."""
    date = db.DateTimeProperty(required=True)
    bet = db.StringProperty(required=True, default="team1")
    points = db.IntegerProperty(default=3)
    
