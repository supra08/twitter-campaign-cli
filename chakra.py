import tweepy
import datetime

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
