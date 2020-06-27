from flask import Flask, url_for, request, jsonify
from flask import session, render_template, redirect
from authlib.integrations.flask_client import OAuth, OAuthError
import oauth2, hmac, hashlib, urllib, urllib3
from requests_oauthlib import OAuth1Session
from campaign import Campaign
from chakra import Chakra
from user import User
import tweepy
from main import db, campaignCollection, userCollection
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
import os
from flask_cors import CORS

ConsumerKey= os.getenv("ConsumerKey")
ConsumerSecret= os.getenv("ConsumerSecret")
TWITTER_REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
TWITTER_ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"

app = Flask(__name__)
cors = CORS(app)

request_token = {}

campaign = Campaign(db, campaignCollection)
user = User(db, userCollection)

class AuthConfig():
    def __init__(self):
        self.ChakraInstance = ''

    def set_chakra(self, auth):
        self.ChakraInstance = Chakra(auth)

    def get_chakra(self):
        return self.ChakraInstance

    def del_chakra(self):
        del self.ChakraInstance

# authConfig = authConfig()

# @app.route('/')
# def homepage():
#     user = session.get('user')
#     return jsonify(
#         status="success"
#     )

@app.route("/request_token")
def request_oauth_token():
    request_token = OAuth1Session(
        client_key=ConsumerKey, client_secret=ConsumerSecret, callback_uri="http://localhost:3000/"
    )
    data = request_token.get(TWITTER_REQUEST_TOKEN_URL)
    if data.status_code == 200:
        request_token = str.split(data.text, '&')
        oauth_token = str.split(request_token[0], '=')[1]
        oauth_callback_confirmed = str.split(request_token[2], '=')[1]
        return {
            "oauth_token": oauth_token,
            "oauth_callback_confirmed": oauth_callback_confirmed,
        }
    else:
        return {
            "oauth_token": None,
            "oauth_callback_confirmed": "false",
        }

@app.route("/access_token")
def request_access_token():
    oauth_token = OAuth1Session(
        client_key=ConsumerKey,
        client_secret=ConsumerSecret,
        resource_owner_key=request.args.get("oauth_token"),
    )
    data = {"oauth_verifier": request.args.get("oauth_verifier")}
    response = oauth_token.post(TWITTER_ACCESS_TOKEN_URL, data=data)
    access_token = str.split(response.text, '&')
    AccessKey = str.split(access_token[0], '=')[1]
    AccessSecret = str.split(access_token[1], '=')[1]
    user_id = str.split(access_token[2], '=')[1]
    screen_name = str.split(access_token[3], '=')[1]
    if (user.find_user(user_id) != None):
        user.delete_user(user_id)
        user.create_new_user(AccessKey, AccessSecret, user_id)
    else:
        user.create_new_user(AccessKey, AccessSecret, user_id)
    # user.create_new_user(AccessKey, AccessSecret, user_id)
    auth = tweepy.OAuthHandler(ConsumerKey, ConsumerSecret)
    auth.set_access_token(AccessKey, AccessSecret)
    authConfig = AuthConfig()
    authConfig.set_chakra(auth)
    chakraInstance = authConfig.get_chakra()
    me = chakraInstance.get_me()
    return jsonify(
        user_id=user_id,
        screen_name=screen_name,
        me=me,
        status="success"
    )

@app.route('/logout')
def logout():
    user_id = request.args.get('user_id')
    user.delete_user(user_id)
    return jsonify(
        status="true"
    )


@app.route('/campaigns', methods=['GET'])
def get_campaigns():
    user_id = request.args.get('user_id')
    campaign_list = campaign.list_all(user_id)
    all_campaigns = [i for i in campaign_list]
    return jsonify(
        status="success",
        campaign_list=all_campaigns
    )

@app.route('/campaign', methods=['POST'])
def create_campaign():
    req = request.get_json()
    name = req['name']
    id = req['id']
    user_id = req['user_id']
    strategy = req['strategy']
    userObj = user.find_user(user_id)
    if (userObj == None):
        return jsonify(
            status="failed"
        )
    auth = tweepy.OAuthHandler(ConsumerKey, ConsumerSecret)
    auth.set_access_token(userObj['access_key'], userObj['access_secret'])
    authConfig = AuthConfig()
    authConfig.set_chakra(auth)
    chakraInstance = authConfig.get_chakra()
    # chakraInstance = authConfig.get_chakra()
    # followers = chakraInstance.get_ranks_from_retweets(id)
    followers = []
    started = True
    message = req['message']
    campaign.create_new_campaign(id, name, strategy, followers, started, message, user_id)
    return jsonify(
        status="success",
    )

@app.route('/start', methods=['POST'])
def start_campaign():
    req = request.get_json()
    id = req['id']
    campaign.start_campaign(id)
    return jsonify(
        status="success"
    )

@app.route('/stop', methods=['POST'])
def stop_campaign():
    req = request.get_json()
    id = req['id']
    campaign.stop_campaign(id)
    return jsonify(
        status="success"
    )

@app.route('/campaign', methods=['GET'])
def get_campaign():
    id = request.args.get('id')
    campaignInfo = campaign.get_campaign(id)
    return jsonify(
        campaign_info=campaignInfo,
        status="success"
    )

@app.route('/campaign', methods=['DELETE'])
def delete_campaign():
    req = request.get_json()
    id = req['id']
    campaign.delete(id)
    return jsonify(
        status="success"
    )

############################ Maybe used later ##################################
# @app.route('/login')
# def login():
#     redirect_uri= "http://localhost:5000/"
#     resp, content = oauth2.Client(consumer).request('https://api.twitter.com/oauth/request_token', "GET")
#     content = urllib.parse.quote_from_bytes(content, safe="=&")
#     global request_token
#     request_token = dict(urllib.parse.parse_qsl(content))
#     redirect_uri = ("%s?oauth_token=%s" % ('https://api.twitter.com/oauth/authorize', request_token['oauth_token']))
#     return jsonify(
#         status="success",
#         redirect_uri=redirect_uri
#     )

# @app.route('/auth')
# def auth():
#     token = oauth2.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
#     token.set_verifier(flask.request.args.get('oauth_verifier'))
#     client = oauth2.Client(consumer, token)
#     resp, content = client.request('https://api.twitter.com/oauth/access_token', "POST")
#     content = urllib.parse.quote_from_bytes(content, safe="=&")
#     access_token = dict(urllib.parse.parse_qsl(content))
#     global AccessKey, AccessSecret
#     AccessKey = access_token['oauth_token']
#     AccessSecret = access_token['oauth_token_secret']
#     auth = tweepy.OAuthHandler(ConsumerKey, ConsumerSecret)
#     auth.set_access_token(AccessKey, AccessSecret)
#     global authConfig
#     authConfig.set_chakra(auth)
#     return jsonify(
#         status="success"
#     )
##################################################################################

if __name__ == "__main__":
    app.run()



