import os
import pymongo

TOKEN = os.getenv('DISCORD_TOKEN')
STAGE = os.getenv('STAGE', 'dev')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING')

mongo_client = pymongo.MongoClient("mongodb://mongodb:27017/")
db = mongo_client["discord"]
