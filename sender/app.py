from flask import Flask, request, render_template, make_response, redirect, url_for, g
import redis
from redis.exceptions import ConnectionError
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import bcrypt
import jwt
import requests
import uuid

load_dotenv()
TOKEN_EXP_DELTA_MINUTES = 5 #in minutes
WEB_SERVICE_ENDPOINT = "https://blooming-mesa-32203.herokuapp.com"
REDIS_HOST = "ec2-3-121-188-229.eu-central-1.compute.amazonaws.com"
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

PACKAGE_STATUS_WAITING = "waiting"
PACKAGE_STATUS_ON_THE_WAY = "on the way"
PACKAGE_STATUS_RECEIVED = "received"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

@app.before_request
def before():
    token = request.cookies.get("token")
    if(token == None):
        g.is_logged = False
    else:
        try:
            result = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            g.is_logged = True
        except (jwt.exceptions.InvalidSignatureError, jwt.exceptions.DecodeError, jwt.exceptions.ExpiredSignatureError) as e:
            g.is_logged = False
    
@app.route('/')
def home():
    return render_template("home.html", is_logged=g.is_logged)

@app.route('/sender/register', methods=['get'])
def register():
    return render_template("register.html", is_logged=g.is_logged)

@app.route('/sender/register', methods=['post'])
def registered():
    r = get_db()
    
    login = request.form.get('login')
    password = request.form.get('password')
    password2 = request.form.get('password2')
    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')
    email = request.form.get('email')
    address = request.form.get('address')
    
    if(
        login == "" or 
        password == "" or
        password2 == "" or
        firstname == "" or
        lastname == "" or
        email == "" or
        address == ""
        ):
            return "Pola nie moga byc puste"
            
    if(password != password2):
        return "Hasla nie moga byc rozne"
    
    
    hashed_password = hash(password)
    
    try:
        if(r.hget(login, "password") != None):
            return "Uzytkownik istnieje"
            
        r.hset(login, "password", hashed_password)
        r.hset(login, "firstname", firstname)
        r.hset(login, "lastname", lastname)
        r.hset(login, "email", email)
        r.hset(login, "address", address)
    except ConnectionError:
        return "Blad serwera"
    
    return "Zarejestrowano pomyślnie"
    
@app.route('/sender/login', methods=['get'])
def login():
    return render_template("login.html", is_logged=g.is_logged)
    
@app.route('/sender/login', methods=['post'])
def logged():
    login = request.form.get('login')
    input_password = request.form.get('password')
    
    r = get_db()
    
    try:
        password = r.hget(login, "password")
    except ConnectionError:
        return "Blad serwera", 503
    
    if(password == None):
        return "Blad logowania", 422
        
    decoded_password = password.decode()
    if(not check_password(input_password, decoded_password)):
        return "Blad logowania", 422
    
    payload = {
        'login': login,
        'exp': datetime.utcnow() + timedelta(minutes=TOKEN_EXP_DELTA_MINUTES)
    }
    jwt_token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    
    resp = make_response(redirect(url_for("home")))
    resp.set_cookie('token', jwt_token, httponly=True)
    
    
    return resp
    

@app.route('/sender/logout', methods=['get'])
def logout():
    resp = make_response(redirect(url_for("home")))
    resp.set_cookie("token", "", expires=0)
    return resp

@app.route('/sender/dashboard', methods=['get'])
def show_dashboard():
    if(not g.is_logged):
        return "Nie masz uprawnien", 401
    
    token = request.cookies.get("token")
    headers = {
        "Authorization": "Bearer " + (str)(token),
        "Origin": request.host
    }
    
    resp = requests.get(WEB_SERVICE_ENDPOINT + "/sender/dashboard", headers=headers)
    
    if(resp.status_code == 401):
        return "Blad autoryzacji", 401
    if(resp.status_code == 403):
        return "Brak dostepu", 403
    if(resp.status_code == 503):
        return "Blad serwera", 503
        
    dashboard = resp.json().get("_embedded")
    table_dict = {}
    delete_links = {}
    
    if(dashboard != None):
        for d in dashboard:
            package_id = dashboard[d]["packageId"]
            receiver = dashboard[d]["receiver"]
            post_id = dashboard[d]["postId"]
            size = dashboard[d]["size"]
            status = dashboard[d]["status"]
            delete_link = dashboard[d]["_links"]["delete"]["href"]
            table_dict[package_id] = [receiver, post_id, size, map_package_status(status)]
            delete_links[package_id] = delete_link
            print(delete_link)

    return render_template("dashboard.html", is_logged=True, labels=table_dict, links=delete_links)

@app.route('/sender/dashboard/new', methods=['get'])
def add_to_dashboard():
        
    if(not g.is_logged):
        return "Nie masz uprawnien", 401
    return render_template("dashboard_new.html", is_logged=True)

@app.route('/sender/dashboard', methods=['post'])
def added_to_dashboard():
    if(not g.is_logged):
        return "Nie masz uprawnien", 401
    
    package_id = uuid.uuid4()
    receiver = request.form.get('receiver')
    post_id = request.form.get('postId')
    size = request.form.get('size')
    
    if(
        receiver == "" or 
        post_id == "" or
        size == ""
        ):
            return "Pola nie moga byc puste"
    
    token = request.cookies.get("token")
    headers = {
        "Authorization": "Bearer " + (str)(token),
        "Origin": request.host
    }
    data = {
        "receiver": receiver,
        "postId": post_id,
        "size": size
    }
    resp = requests.post(WEB_SERVICE_ENDPOINT + "/sender/dashboard", json=data, headers=headers)
    
    if(resp.status_code == 401):
        return "Blad autoryzacji", 401
    if(resp.status_code == 403):
        return "Brak dostepu", 403
    if(resp.status_code == 422):
        return "Pola nie moga byc puste", 422
    if(resp.status_code == 503):
        return "Blad serwera", 503
    
    return redirect(url_for("show_dashboard"))
    
@app.route('/sender/dashboard/<pid>', methods=['delete'])
def removed_from_dashboard(pid):
    if(not g.is_logged):
        return "Nie masz uprawnien", 401
    
    token = request.cookies.get("token")
    headers = {
        "Authorization": "Bearer " + (str)(token),
        "Origin": request.host
    }
    
    resource_url = "/sender/dashboard/" + (str)(pid)

    resp = requests.delete(WEB_SERVICE_ENDPOINT + resource_url, headers=headers)
    
    if(resp.status_code == 401):
        return "Blad autoryzacji", 401
    if(resp.status_code == 403):
        return "Brak dostepu", 403
    if(resp.status_code == 503):
        return "Blad serwera", 503
    
    return "", 204

def get_db():
    r = redis.Redis(
    host=REDIS_HOST,
    password=REDIS_PASSWORD,
    port=6379,
    db=5)
    return r
    
def hash(plaintext):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plaintext.encode(), salt)
    return hashed.decode()
 
def check_password(input_password, hashed_password):
    return bcrypt.checkpw(input_password.encode(), hashed_password.encode())

def map_package_status(status):
    if(status == PACKAGE_STATUS_WAITING):
        return "Oczekujace"
    if(status == PACKAGE_STATUS_ON_THE_WAY):
        return "W drodze"
    if(status == PACKAGE_STATUS_RECEIVED):
        return "Dostarczono"
  
if __name__ == '__main__':
    app.run( host="0.0.0.0", port="5001")