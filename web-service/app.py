import redis
from redis.exceptions import ConnectionError
import uuid
from dotenv import load_dotenv
import os
import jwt

from flask import Flask, request
from flask_hal import HAL, Document, link, HALResponse
from flask_hal.document import Embedded
from flask_cors import CORS

load_dotenv()
REDIS_HOST = "ec2-3-121-188-229.eu-central-1.compute.amazonaws.com"
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
HAL(app)
CORS(app)

@app.route('/sender/dashboard', methods=['get'])
def show_dashboard():

    token = get_token()
    if(token == None):
        return "Blad autoryzacji", 401
    login = token["login"]
    
    result = check_origin(request.origin)
    if(not result):
        return "Brak dostepu", 403
    
    r = get_db()
    
    try:
        if(login != "courier"):
            packages_number = r.llen(login)
            packages = r.lrange(login, 0, packages_number - 1)
        else:
            packages = []
            keys = r.keys()
            for key in keys:
                if(r.type(key) == b"hash"):
                    packages.append(key)
    except ConnectionError:
        return "Blad serwera", 503
        
    decoded_packages = [p.decode() for p in packages]
    
    dashboard = {}
    i = 1
    try:
        for dp in decoded_packages:
            receiver = r.hget(dp, "receiver").decode()
            post_id = r.hget(dp, "post_id").decode()
            size = r.hget(dp, "size").decode()
            status = r.hget(dp, "status").decode()
            package_name = "package" + (str)(i)
            dashboard[package_name] = Embedded(
                data={
                    "packageId": dp,
                    "receiver": receiver,
                    "postId": post_id,
                    "size": size,
                    "status": status
                },
                links=link.Collection(
                    link.Link("delete", "/sender/dashboard/" + (str)(dp)),
                    link.Link("update", "/sender/dashboard/" + (str)(dp))
                )
            )
            i = i + 1
    except ConnectionError:
        return "Blad serwera", 503
          
    headers = {
        "Access-Control-Allow-Origin": request.origin
    }
    return HALResponse(response=Document(
        data={"name": "dashboard"}, 
        embedded=dashboard).to_json(), 
        headers=headers, 
        content_type="application/hal+json")

@app.route('/sender/dashboard', methods=['post'])
def add_to_dashboard():

    token = get_token()
    if(token == None):
        return "Blad autoryzacji", 401
    login = token["login"]
    
    result = check_origin(request.origin)
    if(not result):
        return "Brak dostepu", 403
    
    r = get_db()
    
    package_id = uuid.uuid4()
    receiver = request.json.get('receiver')
    post_id = request.json.get('postId')
    size = request.json.get('size')
    
    if(
       receiver == "" or 
       post_id == "" or
       size == ""
       ):
           return "Pola nie moga byc puste", 422
    
    try:
        r.hset((str)(package_id), "receiver", receiver)
        r.hset((str)(package_id), "post_id", post_id)
        r.hset((str)(package_id), "size", size)
        r.hset((str)(package_id), "status", "waiting")
        r.rpush(login, (str)(package_id))
    except ConnectionError:
        return "Blad serwera", 503
        
    
    links = link.Collection(
        link.Link("delete", "/sender/dashboard/" + (str)(package_id)),
        link.Link("update", "/sender/dashboard/" + (str)(package_id))
    )
    package_info = {
        "packageId": (str)(package_id),
        "receiver": receiver,
        "postId": post_id,
        "size": size,
        "status": "waiting"
    }
    headers = {
        "Access-Control-Allow-Origin": request.origin
    }
    return HALResponse(response=Document(
        embedded={"newPackage": Embedded(data=package_info, links=links)}).to_json(), 
        headers=headers, 
        content_type="application/hal+json")
    
@app.route('/sender/dashboard/<pid>', methods=['delete'])
def remove_from_dashboard(pid):

    token = get_token()
    if(token == None):
        return "Blad autoryzacji", 401
    login = token["login"]
    
    result = check_origin(request.origin)
    if(not result):
        return "Brak dostepu", 403
    
    r = get_db()
    
    try:
        r.hdel(pid, "receiver")
        r.hdel(pid, "post_id")
        r.hdel(pid, "size")
        r.hdel(pid, "status")
        r.lrem(login, 1, pid)
    except ConnectionError:
        return "Blad serwera", 503
    
    return "Usunieto"

@app.route('/sender/dashboard/<pid>', methods=['put'])
def update_dashboard(pid):

    token = get_token()
    if(token == None):
        return "Blad autoryzacji", 401
        
    result = check_origin(request.origin)
    if(not result):
        return "Brak dostepu", 403
    
    r = get_db()
    
    package_id = pid
    receiver = request.json.get('receiver')
    post_id = request.json.get('postId')
    size = request.json.get('size')
    status = request.json.get('status')
    
    if(package_id.encode() not in r.keys()):
        return "Paczka nie istnieje", 404
    
    try:
        if(receiver != None and receiver != ""):
            r.hset((str)(package_id), "receiver", receiver)
            
        if(post_id != None and post_id != ""):
            r.hset((str)(package_id), "post_id", post_id)
            
        if(size != None and size != ""):
            r.hset((str)(package_id), "size", size)
            
        if(status != None and status != ""):
            r.hset((str)(package_id), "status", status)
    except ConnectionError:
        return "Blad serwera", 503      
    
    return "Zaktualizowano"

def get_db():
    r = redis.Redis(
    host=REDIS_HOST,
    password=REDIS_PASSWORD,
    port=6379,
    db=6)
    return r
    
def get_token():
    
    try:
        auth = request.headers["Authorization"]
    except KeyError:
        return None
        
    encoded_token = auth.split()[1]
      
    try:
        decoded_token = jwt.decode(encoded_token, app.config['SECRET_KEY'], algorithms=['HS256'])
    except (jwt.exceptions.InvalidSignatureError, jwt.exceptions.DecodeError, jwt.exceptions.ExpiredSignatureError) as e:
        return None
        
    return decoded_token

def check_origin(origin):
    if(origin != None and (origin.endswith(".herokuapp.com") or ("localhost" in origin))):
        return True
    return False
    
if __name__ == '__main__':
    app.run( host="0.0.0.0", port="5000")