#!/usr/bin/env python
# coding: utf-8

import os
# dummy config to enable registering django template filters
os.environ[u'DJANGO_SETTINGS_MODULE'] = u'conf'

from django.template.defaultfilters import register
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

CHOICE_CAT_LST = ["choiceid0", "choiceid1", "choiceid2"]

class User(db.Model):
    user_id = db.StringProperty(required=True)
    access_token = db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    picture = db.StringProperty(required=True)
    email = db.StringProperty()
    friends = db.StringListProperty()
    dirty = db.BooleanProperty()

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
       
    def get_friends(self):
        """Fetch this user's friends using the Facebook Graph API"""
        me = Facebook().api(u'/me',
            {u'fields': u'id,name,picture,friends', u'access_token': self.access_token})
        
        return me["friends"]["data"]
    
    def has_picked(self):
        picks = Pick.gql("WHERE user_id = :1", "750235700").count()
        return picks
    
    
    def get_rating(self):
        """ returns the rating for the user. """
        
        rating = 0
        for choice in CHOICE_CAT_LST:
            picks = Pick.gql("WHERE %s = :1" % choice, self.user_id)
            rating = rating + picks.count()
            
        if rating == 0:
            rating_label = "Devastating!"
            rating_color = "rating0"
            rating_status = "NONE OF YOUR FRIENDS has chosen to be your valentine"
        
        if rating == 1:
            rating_label = "Sweeeet!"
            rating_color = "rating14"
            rating_status = "ONE OF YOUR FRIENDS has chosen to be your valentine"
        
        if rating == 2:
            rating_label = "Sweeeet!"
            rating_color = "rating14"
            rating_status = "TWO OF YOUR FRIENDS has chosen to be your valentine"
            
        if rating == 3:
            rating_label = "Sweeeet!"
            rating_color = "rating14"
            rating_status = "THREE OF YOUR FRIENDS has chosen to be your valentine"
            
        if rating == 4:
            rating_label = "Sweeeet!"
            rating_color = "rating14"
            rating_status = "FOUR OF YOUR FRIENDS has chosen to be your valentine"
        
        if rating >= 5:
            rating_label = "Smoking Hot!"
            rating_color = "rating50"
            rating_status = "Woohoo! Lots of friends want to date you this Valentine's! :D"
        
        return { "rating" : rating,
                 "rating_color" : rating_color,
                 "rating_label" : rating_label,
                 "rating_status" : rating_status,
                }
    
class PickException(Exception):
    pass

class Pick(db.Model):
    date = db.DateTimeProperty(required=True)
    
    user_id = db.StringProperty(required=True)
    user_name = db.StringProperty(required=False, default="")
    
    choice0 = db.StringProperty(required=True)
    choice1 = db.StringProperty(required=True)
    choice2 = db.StringProperty(required=True)
    
    choiceid0 = db.StringProperty(required=True, default="")
    choiceid1 = db.StringProperty(required=True, default="")
    choiceid2 = db.StringProperty(required=True, default="")
    
    
class Match(db.Model):
    user_id1 = db.StringProperty(required=True)
    user_id2 = db.StringProperty(required=True)
    
    notified1 = db.BooleanProperty(default=False)
    notified2 = db.BooleanProperty(default=False)
    
    
    @staticmethod
    def get_match_key(user_id1, user_id2):
        """ generates and returns a match key. """
        user_id1 = int(user_id1)
        user_id2 = int(user_id2)
        
        usr1, usr2 = min(user_id1, user_id2), max(user_id1, user_id2)
        usr1, usr2 = map(str, [usr1, usr2])
        
        return  map(str, [usr1, usr2, "_".join([usr1, usr2])])
    
    
    @staticmethod
    def get_user_match(user_id):
        """ returns the list of user names as matches for the user."""
        try:
            logging.info('#0 finding matches for %s' % user_id)
            matchset = set()
            choiceset = set()
            choices = Pick.gql("WHERE user_id = :1", user_id).fetch(100)
#            choices = Pick.all().filter('user_id = ', user_id).fetch(100)
            
            for ch in CHOICE_CAT_LST:
                choiceset.update( [getattr(choice, ch) for choice in choices] )
            
            for choice in choiceset:
              picks = Pick.gql("WHERE user_id = :1", choice)
              
              pickset = set()
              for pk in CHOICE_CAT_LST:
                pickset.update( [getattr(pks, pk) for pks in picks] )
                
              if user_id in pickset:
                matchset.update( [choice] )
                
            matchset = map(int, matchset)
            user_id = int(user_id)
            
            for match in matchset:
              usr1, usr2, key_name = Match.get_match_key(user_id, match)
    
              mt = Match(key_name = key_name,
                         user_id1 = usr1,
                         user_id2 = usr2)
              mt.put()
              
            logging.info("match found for the user  %s" % user_id)
          
        except Exception, e:
            logging.info("exception ", e)
          
        return matchset
    
      
      
class Utils(object):
    """ application utilities. """
    
    @staticmethod
    def get_rating(user_id):
        rating = 0
        for choice in CHOICE_CAT_LST:
            picks = Pick.gql("WHERE %s = :1" % choice, user_id)
            rating = rating + picks.count()
            
        return rating
    
    
    @staticmethod
    def notify_match(match):
        """ notify the users, from this matches. """
        
        """ match person #1 """
        usr1 = User.get_by_key_name(match.user_id1)
        
        """ match person #2 """
        usr2 = User.get_by_key_name(match.user_id2)
        
        if not match.notified1:# and match.user_id1 in ADMIN_USER_IDS:
            rat1 = Utils.get_rating(match.user_id1) -1
            sent = Utils.send_mail(usr1.user_id, usr1.email, usr2.name, rat1)
            match.notified1 = sent
        
        if not match.notified2:# and match.user_id2 in ADMIN_USER_IDS:
            rat2 = Utils.get_rating(match.user_id2) - 1
            Utils.send_mail(usr2.user_id, usr2.email, usr1.name, rat2)
            match.notified2 = sent
            
        match.put()
    
    
    @staticmethod
    def notify_rating(self):
        pass
    
    
    @staticmethod
    def notify_updates(self):
        pass
    
    
    @staticmethod
    def notify_promotions(self):
        pass
    
    
    @staticmethod
    def notify_matches_all():
        """ notify all the matches. """
        for match in Match.all():
            Utils.notify_match(match)
    
    
    @staticmethod
    def update_matches_all():
        """ update matces for all users. """ 
        logging.info("Yo! updating marches")
        
        for usr in User.all(): #.fetch(limit, offset):
            Match.get_user_match(usr.user_id)
            logging.info("Yep! done matches for : %s" % usr.user_id)
    
    
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
    
    