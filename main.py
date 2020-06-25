#!/usr/local/bin/python3

import tweepy
import pymongo
import datetime
import argparse
from dateutil.parser import parse
from dotenv import load_dotenv
from pathlib import Path
import os
import ast
import re

####### Setup Division #######
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

DB_NAME = "chakra"
COLLECTION_NAME = "campaigns"
STRATEGY_TWEETS = "tweet"
STRATEGY_FRIENDS = "friend"
STRATEGY_FOLLOWERS = "follower"

mongoClient = pymongo.MongoClient("mongodb://localhost:27017/")

# if DB_NAME not in mongoClient.list_database_names():
db = mongoClient[DB_NAME]
campaignCollection = db[COLLECTION_NAME]


ConsumerKey = os.getenv("ConsumerKey")
ConsumerSecret = os.getenv("ConsumerSecret")
AccessKey = os.getenv("AccessKey")
AccessSecret = os.getenv("AccessSecret")

auth = tweepy.OAuthHandler(ConsumerKey, ConsumerSecret)
auth.set_access_token(AccessKey, AccessSecret)
##############################

def interpolate(message, user):
    interpolated_message = message.replace('{name}', user["name"])
    return interpolated_message

class Chakra():
    
    def __init__(self, auth):
        self.api = tweepy.API(auth, wait_on_rate_limit=True,
            wait_on_rate_limit_notify=True)
            
    def get_me(self):
        return self.api.me()._json

    def get_id(self, handle):
        return self.api.get_user(handle)._json['id']

    def get_user(self, user_id):
        return self.api.get_user(user_id)._json['name']

    def get_user_json(self, handle):
        return self.api.get_user(handle)._json

    def followers_count(self, user_obj):
        return user_obj._json["followers_count"]
    
    # returns followers_count if user id if passed
    def followers_count_id(self, user_id):
        return self.api.get_user(user_id)._json["followers_count"]

    def followers_info(self, user_id):
        follower_id = []
        follower_name = []
        follower_followers = []
        follower_friends = []
        # index = 0
        for follow_obj in tweepy.Cursor(self.api.followers, id=user_id).items():
            print(follow_obj._json["id"])
            follower_id.append(follow_obj._json["id"])
            follower_name.append(follow_obj._json["name"])
            follower_followers.append(follow_obj._json["followers_count"])
            follower_friends.append(follow_obj._json["friends_count"])
            # if index >= 1:
            #     break
            # index = index + 1
        return follower_id, follower_name, follower_followers, follower_friends

    def get_ranks_from_follower_followers(self, user_id):
        follower_ids, follower_names, follower_followers, _ = self.followers_info(user_id)
        ranked_followers = [ { "id": fol, "sent": False } for _, fol in sorted(zip(follower_followers,follower_ids))]
        return ranked_followers

    def get_ranks_from_follower_friends(self, user_id):
        follower_ids, follower_names, _, follower_friends = self.followers_info(user_id)
        ranked_followers = [ { "id": fol, "sent": False } for _, fol in sorted(zip(follower_friends,follower_ids)) ]
        return ranked_followers
    
    def get_tweet_info(api, tweet_id):
        return api.get_status(tweet_id)._json

    def get_tweets(self, user_id):
        tweets_id = []
        tweet_created_time = []
        for x in tweepy.Cursor(self.api.user_timeline, id = user_id).items():
            tweets_id.append(x._json['id_str'])
            tweet_created_time.append(parse(x._json['created_at']).date())
        return tweets_id, tweet_created_time

    # returns tweets upton certain timestamp say for 180 days from current date
    def get_certain_tweets(self, user_id, from_time = datetime.datetime.now().date() ,duration = 180 ):
        # print(from_time)
        tweets_id = []
        tweet_created_time = []
        for x in tweepy.Cursor(self.api.user_timeline, id = user_id).items():
            created_time = parse(x._json['created_at']).date()
            if (from_time - created_time).days <= duration:
                tweets_id.append(x._json['id_str'])
                tweet_created_time.append(created_time)
            else:
                break
        return tweets_id, tweet_created_time

    def get_retweeters(self, tweet_id):
        return self.api.retweeters(tweet_id)

    def get_ranks_from_retweets(self, user_id):
        rank_followers = {}
        tweets, time = self.get_tweets(user_id)
        for x in tweets:
            for y in self.get_retweeters(x):
                if y in rank_followers:
                    rank_followers[y] = rank_followers[y] + 1
                else:
                    rank_followers[y] = 1
        return rank_followers

    def send_dm(self, user_id, message):
        self.api.send_direct_message(user_id, message)

    def send_mass_dm(self, message, followers_list_with_ids, specificMessageObj = {}):
        for user in followers_list_with_ids:
            self.send_dm(user, message)


class Campaign():
    def __init__(self, db, collection):
        self.db = db
        self.collection = collection

    def create_new_campaign(self, id, name, strategy, followers, started, message):
        doc = {}
        doc["id"] = id
        doc["name"] = name
        doc["strategy"] = strategy
        doc["followers"] = followers
        doc["started"] = started
        doc["message"] = message
        elem = self.collection.find({}, {"name": name})
        x = self.collection.insert_one(doc)
        print(x)
        
    def start_campaign(self, id):
        count = self.collection.count_documents({ "id": id })
        if count > 0:
            self.collection.update_one({ "id": id }, { "$set": { "started": True }})

    def get_status(self, id):
        cp = self.collection.find_one({ "id": id })
        count = sum(1 for i in cp["followers"] if i["sent"])
        return { "sent": count, "total": len(cp["followers"]) }

    def truncate(self):
        self.collection.drop()

    def list_all(self):
        l = self.collection.find({}, { "_id": 0, "id": 1, "name": 1, "strategy": 1, "started": 1, "message": 1 })
        return l

    def get_campaign(self, id):
        c = self.collection.find_one({ "id": id }, { "_id": 0, "followers": 1, "started": 1, "message": 1 })
        return c

    def mark_sent(self, cid, uid):
        self.collection.update_one( { "id": cid, "followers.id": uid }, { "$set": { "followers.$.sent": True } } )

    
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--campaign_name", help="Campaign name")
    parser.add_argument("-s", "--strategy_type", help="Strategy type")
    parser.add_argument("-i", "--id", help="Unique ID")
    parser.add_argument("-m", "--message", help="message template")
    parser.add_argument("-r", "--recipients", help="recipients")
    
    parser.add_argument("-A", "--add", action='store_true')
    parser.add_argument("-S", "--start", action='store_true')
    parser.add_argument("-R", "--run", action='store_true')
    parser.add_argument("-T", "--status", action='store_true')
    parser.add_argument("-DA", "--delete_all", action='store_true')
    parser.add_argument("-L", "--list", action='store_true')
    parser.add_argument("-DM", "--direct_message", action='store_true')
    arguments = parser.parse_args()
    
    # initialize the Chakra engine
    chakraInstance = Chakra(auth)

    # Initialize the Campaign model
    campaign = Campaign(db, campaignCollection)

    if (arguments.add):
        me = chakraInstance.get_me()
        user_id = me["id"]
        if (arguments.campaign_name and arguments.strategy_type and arguments.id and arguments.message):
            if arguments.strategy_type == STRATEGY_TWEETS:
                followers = chakraInstance.get_ranks_from_retweets(user_id)
                campaign.create_new_campaign(arguments.id, arguments.campaign_name, arguments.strategy_type, followers, False, arguments.message)
            elif arguments.strategy_type == STRATEGY_FOLLOWERS:
                followers = chakraInstance.get_ranks_from_follower_followers(user_id)
                print(followers)
                # followers = []
                campaign.create_new_campaign(arguments.id, arguments.campaign_name, arguments.strategy_type, followers, False, arguments.message)
            elif arguments.strategy_type == STRATEGY_FRIENDS:
                followers = chakraInstance.get_ranks_from_follower_friends(user_id)
                campaign.create_new_campaign(arguments.id, arguments.campaign_name, arguments.strategy_type, followers, False, arguments.message)
            else:
                print("invalid strategy")
        else:
            print("inavlid input")

    if (arguments.start):
        if (arguments.id):
            campaign.start_campaign(arguments.id)
        else:
            print("invalid input")

    if (arguments.status):
        if (arguments.id):
            print(campaign.get_status(arguments.id))
        else:
            print("invalid input")

    if (arguments.delete_all):
        campaign.truncate()

    if (arguments.list):
        print([i for i in campaign.list_all()])

    if (arguments.direct_message):
        if (arguments.recipients and arguments.id):
            cp = campaign.get_campaign(arguments.id)
            recipients = ast.literal_eval(arguments.recipients)
            for r in recipients:
                user = chakraInstance.get_user_json(r)
                print(interpolate(cp["message"], user))
                chakraInstance.send_dm(user["id"], interpolate(cp["message"], user))
                campaign.mark_sent(arguments.id, user["id"])
        elif (arguments.id):
            cp = campaign.get_campaign(arguments.id)
            recipients = cp["followers"]
            for r in recipients:
                if r["sent"] == False:
                    user = chakraInstance.get_user_json(r["id"])
                    chakraInstance.send_dm(user["id"], interpolate(cp["message"], user))
                    campaign.mark_sent(arguments.id, user["id"])
            pass
        else:
            print("invalid input")
