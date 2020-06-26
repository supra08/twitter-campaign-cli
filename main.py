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
import json
from tabulate import tabulate
import time

from chakra import Chakra
from campaign import Campaign
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
    start_parser.add_argument("-i", "--id", help="Campaign ID", required=True)

    status_parser = subparsers.add_parser('status', help="Status of a Campaign")
    status_parser.add_argument("-i", "--id", help="Campaign ID", required=True)

    delete_parser = subparsers.add_parser('delete', help="Delete a (or all) Campaign(s)")
    delete_parser.add_argument("-i", "--id", help="Campaign ID")
    delete_parser.add_argument("-a", "--all", help="Delete all campaigns", action="store_true")

    dm_parser = subparsers.add_parser('dm', help="Direct message for a campaign")
    dm_parser.add_argument("-i", "--id", help="Campaign ID", required=True)
    dm_parser.add_argument("-r", "--recipients", help="recipients", default="all")
    dm_parser.add_argument("-d", "--daemonize", help="Daemonize DM Loop", action="store_true", default=False)

    list_parser = subparsers.add_parser("list", help="List all campaigns")

    reset_parser = subparsers.add_parser('reset', help="Reset a campaign")
    reset_parser.add_argument("-i", "--id", help="Campaign ID", required=True)

    stop_parser = subparsers.add_parser('stop', help="Stop a campaign")
    stop_parser.add_argument("-i", "--id", help="Campaign ID", required=True)
    
    edit_parser = subparsers.add_parser('edit', help="Edit a campaign")
    edit_parser.add_argument("-i", "--id", help="Campaign ID", required=True)
    edit_parser.add_argument("-m", "--message", help="message template")
    edit_parser.add_argument("-n", "--name", help="Campaign name")
    edit_parser.add_argument("-s", "--strategy_type", help="Strategy type")

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
        if not (campaign.id_exists(arguments.id)):
            pp and print("[!] No such campaign exists!")
            exit(1)

        cp = campaign.get_campaign(arguments.id)
        
        if (cp["started"]):
            print("[+] Campaign Already Started")
            exit(1)
        
        campaign.start_campaign(arguments.id)
        pp and print("[+] Starting campaign `{}`".format(cp["name"]))

        n = os.fork()
        if n == 0 and pp:
            print("[+] Daemonized with PID", os.getpid())
        elif pp:
            print("[+] Success")

        if n == 0:
            # pymongo is fork-unsafe
            mongoClient = pymongo.MongoClient("mongodb://localhost:27017/")
            db = mongoClient[DB_NAME]
            campaignCollection = db[COLLECTION_NAME]
            campaign = Campaign(db, campaignCollection)

            recipients = cp["followers"]
            for r in recipients:
                if not campaign.is_started(cp["id"]):
                    exit(0)

                if r["sent"] == False:
                    user = chakraInstance.get_user_json(r["id"])
                    chakraInstance.send_dm(user["id"], interpolate(cp["message"], user))
                    campaign.mark_sent(arguments.id, user["id"])

    elif command == "status":
        # status command
        status = campaign.get_status(arguments.id)
        if not pp:
            print(json.dumps(status))
        else:
            cp = campaign.get_campaign(arguments.id)
            pretty_print_status(cp, status)

    elif command == "delete":
        # delete command
        if arguments.id:
            if (campaign.id_exists(arguments.id)):
                print("[+] Deleting campaign with id", arguments.id)
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
        campaign.start_campaign(arguments.id)
        pp and print("[+] Starting campaign `{}`".format(cp["name"]))

        n = 0
        if arguments.daemonize:
            n = os.fork()
            if n == 0 and pp:
                print("[+] Daemonized with PID", os.getpid())
            elif pp:
                print("[+] Success")


        if n == 0:
            # pymongo is fork-unsafe
            mongoClient = pymongo.MongoClient("mongodb://localhost:27017/")
            db = mongoClient[DB_NAME]
            campaignCollection = db[COLLECTION_NAME]
            campaign = Campaign(db, campaignCollection)

            if (arguments.recipients == "all"):
                recipients = cp["followers"]
                for r in recipients:
                    if not campaign.is_started(cp["id"]):
                        exit(0)

                    if r["sent"] == False:
                        user = chakraInstance.get_user_json(r["id"])
                        chakraInstance.send_dm(user["id"], interpolate(cp["message"], user))
                        campaign.mark_sent(arguments.id, user["id"])
            else:
                recipients = ast.literal_eval(arguments.recipients)
                for r in recipients:
                    if not campaign.is_started(cp["id"]):
                        exit(0)
           
                    user = chakraInstance.get_user_json(r)
                    chakraInstance.send_dm(user["id"], interpolate(cp["message"], user))
                    campaign.mark_sent(arguments.id, user["id"])

        if not arguments.daemonize:
            print("[+] Success")

    elif command == "list":
        # list command
        all_campaigns = [i for i in campaign.list_all()]
        if not pp:
            print(all_campaigns)
        else:
            pretty_print_list(all_campaigns)

    elif command == "reset":
        if not (campaign.id_exists(arguments.id)):
            pp and print("[!] No such campaign exists!")
            exit(1)

        campaign.reset_sent(arguments.id)
        pp and print("[+] Success")

    elif command == "stop":
        if not (campaign.id_exists(arguments.id)):
            pp and print("[!] No such campaign exists!")
            exit(1)

        campaign.stop_campaign(arguments.id)

    elif command == "edit":
        if not (campaign.id_exists(arguments.id)):
            pp and print("[!] No such campaign exists!")
            exit(1)
        
        if (arguments.name):
            campaign.edit_name(arguments.id, arguments.name)
        
        if (arguments.message):
            campaign.edit_message(arguments.id, arguments.message)

    else:
        print("[!] No command specified")
        exit(1)


    sys.exit(0)
