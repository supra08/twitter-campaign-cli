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
import sys
from tabulate import tabulate

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

    def delete(self, id):
        self.collection.delete_one({ "id": id })

    def list_all(self):
        l = self.collection.find({}, { "_id": 0, "id": 1, "name": 1, "strategy": 1, "started": 1, "message": 1 })
        return l

    def get_campaign(self, id):
        c = self.collection.find_one({ "id": id })
        return c

    def mark_sent(self, cid, uid):
        self.collection.update_one( { "id": cid, "followers.id": uid }, { "$set": { "followers.$.sent": True } } )

    def id_exists(self, id):
        count = self.collection.count_documents({ "id": id })
        return (count >= 1)

def parse_arguments():
    parser = argparse.ArgumentParser(prog="Twitter Campaigns CLI")
    parser.add_argument("-f", "--format", help="Output format", default="human")

    subparsers = parser.add_subparsers(help='sub-command help', dest="command")

    add_parser = subparsers.add_parser('add', help="Add New Campaign")
    add_parser.add_argument("-n", "--name", help="Campaign name", required=True)
    add_parser.add_argument("-s", "--strategy_type", help="Strategy type", required=True)
    add_parser.add_argument("-i", "--id", help="Unique ID", required=True)
    add_parser.add_argument("-m", "--message", help="message template", required=True)

    start_parser = subparsers.add_parser('start', help="Start a Campaign")
    start_parser.add_argument("-i", "--id", help="Campaign ID")

    status_parser = subparsers.add_parser('status', help="Status of a Campaign")
    status_parser.add_argument("-i", "--id", help="Campaign ID")

    delete_parser = subparsers.add_parser('delete', help="Delete a (or all) Campaign(s)")
    delete_parser.add_argument("-i", "--id", help="Campaign ID")
    delete_parser.add_argument("-a", "--all", help="Delete all campaigns", action="store_true")

    dm_parser = subparsers.add_parser('dm', help="Direct message for a campaign")
    dm_parser.add_argument("-i", "--id", help="Campaign ID", required=True)
    dm_parser.add_argument("-r", "--recipients", help="recipients", default="all")
    dm_parser.add_argument("-d", "--daemonize", help="Daemonize DM Loop", action="store_true", default=False)

    list_parser = subparsers.add_parser("list", help="List all campaigns")

    return parser.parse_args()

def pretty_print_list(campaigns):

    data = [ (i["id"], i["name"], i["strategy"], i["started"], i["message"], ) for i in campaigns]
    print(tabulate(data, headers=["Id", "Campaign Name", "Strategy", "Started", "Message Template"]))
    print()
    print("Fetched {} campaigns".format(len(data)))

def pretty_print_status(cp, status):

    print("Campaign Name: ", cp["name"])
    print("Active: ", cp["started"])
    print("Status: ", status["sent"], "/", status["total"], "(Completed)" if status["total"] == status["sent"] else "")

    
if __name__ == "__main__":
    arguments = parse_arguments()
    command  = arguments.command

    campaign = Campaign(db, campaignCollection)
    chakraInstance = Chakra(auth)
    pp = not (arguments.format and arguments.format == "json")

    # print banner
    if pp:
        print("    Twitter Campaigns CLI v0.1")
        print("    ==========================")
        print()

    if command == "add":
        # add command
        pp and print("[+] Authenticating.....", end='')
        me = chakraInstance.get_me()
        user_id = me["id"]
        print("Authenticated as", me["name"])

        print("[+] Making a new campaign with name `{}` and id `{}`".format(arguments.name, arguments.id))

        if (campaign.id_exists(arguments.id)):
            pp and print("[!] Campaign with same ID already exists")
            pp and print("[!] Failure")
            exit(1)

        # TODO: Check if same id exists

        if arguments.strategy_type == STRATEGY_TWEETS:
            pp and print("[+] Strategy set to 'User with most retweets first'")
            pp and print("[+] Fetching followers.....", end='')
            followers = chakraInstance.get_ranks_from_retweets(user_id)
            pp and print("fetched {} followers".format(len(followers)))
            campaign.create_new_campaign(arguments.id, arguments.name, arguments.strategy_type, followers, False, arguments.message)
            pp and print("[+] Success")
        elif arguments.strategy_type == STRATEGY_FOLLOWERS:
            pp and print("[+] Strategy set to 'User with most followers first'")
            pp and print("[+] Fetching followers.....", end='')
            followers = chakraInstance.get_ranks_from_follower_followers(user_id)
            pp and print("fetched {} followers".format(len(followers)))
            campaign.create_new_campaign(arguments.id, arguments.name, arguments.strategy_type, followers, False, arguments.message)
            pp and print("[+] Success")
        elif arguments.strategy_type == STRATEGY_FRIENDS:
            pp and print("[+] Strategy set to 'User with most friends first'")
            pp and print("[+] Fetching followers.....", end='')
            followers = chakraInstance.get_ranks_from_follower_friends(user_id)
            pp and print("fetched {} followers".format(len(followers)))
            campaign.create_new_campaign(arguments.id, arguments.name, arguments.strategy_type, followers, False, arguments.message)
            pp and print("[+] Success")
        else:
            pp and print("invalid strategy")

    elif command == "start":
        # TODO: This is just an alias for daemonized DM Loop with check for campaign if its still active
        pass

    elif command == "status":
        # status command
        status = campaign.get_status(arguments.id)
        if not pp:
            print(status)
        else:
            cp = campaign.get_campaign(arguments.id)
            pretty_print_status(cp, status)

    elif command == "delete":
        # delete command
        if arguments.id:
            if (campaign.id_exists(arguments.id)):
                print("[+] Deleting campaign with id", campaign.id)
                campaign.delete(arguments.id)
                print("[+] Success")
            else:
                pp and print("[!] No such campaign exists")
                exit(1)

        elif arguments.all:
            pp and print("[+] Deleting all campaigns....")
            campaign.truncate()
            pp and print("[+] Success")

        else:
            print("[!] Specify either id of campaign or `-a` to delete all campaigns")
            exit(1)

    elif command == "dm":
        if not (campaign.id_exists(arguments.id)):
            pp and print("[!] No such campaign exists!")
            exit(1)

        cp = campaign.get_campaign(arguments.id)
        pp and print("[+] Starting campaign `{}`".format(cp["name"]))

        # TODO: Daemonize loop
        if (arguments.recipients == "all"):
            recipients = cp["followers"]
            for r in recipients:
                if r["sent"] == False:
                    user = chakraInstance.get_user_json(r["id"])
                    chakraInstance.send_dm(user["id"], interpolate(cp["message"], user))
                    campaign.mark_sent(arguments.id, user["id"])
        else:
            recipients = ast.literal_eval(arguments.recipients)
            for r in recipients:
                user = chakraInstance.get_user_json(r)
                chakraInstance.send_dm(user["id"], interpolate(cp["message"], user))
                campaign.mark_sent(arguments.id, user["id"])

        pp and (not arguments.daemonize) and print("[+] Success")

    elif command == "list":
        # list command
        all_campaigns = [i for i in campaign.list_all()]
        if not pp:
            print(all_campaigns)
        else:
            pretty_print_list(all_campaigns)

    else:
        print("[!] No command specified")


    sys.exit(0)
