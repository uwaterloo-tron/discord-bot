import os
# import pymongo
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
STAGE = os.getenv('STAGE', 'dev')

# mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
# db = mongo_client["discord"]
