from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for, Response  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################

@app.route('/health')
def health():
    return jsonify(dict(status = "OK")), 200

@app.route('/count')
def count():
    try:
        count = db.songs.count_documents({})
        return {"count": count}, 200
    except Exception as e:
        return {"message":"Internal Server Error!"}, 500


@app.route('/song', methods=['GET']) 
def songs(): 
    try:
        all_songs = db.songs.find({})
        return Response(
            json_util.dumps({"songs": list(all_songs)}),
            mimetype="application/json",
            status=200
        )
    except Exception as e:
        return {"message": e}, 500


@app.route('/song/<int:song_id>', methods=['GET'])
def get_song_by_id(song_id):
    try:
        song = db.songs.find_one({"id":song_id})
        if song:
            return Response(
                json_util.dumps(song),
                mimetype= "application/json",
                status=200
            )
        return {"message": f"song with id {song_id} not found"}, 404
    except Exception as e:
        return {"message":"Internal Server Error!"}, 500


@app.route('/song', methods= ['POST'])
def create_song():
    try:
        new_song = request.get_json()
        existing_song = db.songs.find_one({"id": new_song['id']})
        if existing_song:
            return {"Message": f"song witih id {new_song['id']} already present"}, 302
        result = db.songs.insert_one(new_song)
        return Response(
            json_util.dumps({"inserted id": result.inserted_id}),
            mimetype="application/json",
            status=201
        )
    except Exception as e:
        return {"message":"Internal Server Error"}, 500



@app.route('/song/<int:song_id>', methods=['PUT'])
def update_song(song_id):
    try:
        song_data = request.get_json()
        result = db.songs.update_one(
            {"id": song_id}, {"$set":song_data}
        )
        if result.matched_count == 0:
            return {"message":f"song with id {song_id} not found"}, 404
        if result.modified_count == 0:
            return {"message":"song found, but nothing updated"}, 200
        updated_song = db.songs.find_one({"id":song_id})
        return Response(
            json_util.dumps(updated_song),
            mimetype="application/json",
            status=201
        )
    except Exception as e:
        return {"message":{str(e)}}, 500

@app.route('/song/<int:song_id>', methods=['DELETE'])
def delete_song(song_id):
    try:
        result = db.songs.delete_one({"id": song_id})

        if result.deleted_count == 0:
            return {"message":"song not found"}, 404
        return "", 204
    except Exception as e:
        return {"message": "Internal Server Error"}, 500