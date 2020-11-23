from flask import Flask, request, render_template, make_response, session, redirect, url_for, g
import redis
from redis.exceptions import ConnectionError
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from flask_session import Session
import bcrypt

app = Flask(__name__)

load_dotenv()
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SESSION_TYPE'] = "redis"
s = Session()
s.init_app(app)

@app.before_request
def before():
    g.is_logged = (session.get("uid") != None)

@app.route('/')
def home():
    return render_template("home.html", is_logged=g.is_logged)

@app.route('/sender/register', methods=['get'])
def register():
    return render_template("register.html", is_logged=g.is_logged)

@app.route('/sender/register', methods=['post'])
def registered():
    r = get_db(1)
    
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
    
    if(r.hget(login, "password") != None):
        return "Uzytkownik istnieje"
    try:
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
    
    r = get_db(1)
    
    try:
        password = r.hget(login, "password")
    except ConnectionError:
        return "Blad serwera"
    
    if(password == None):
        return "Blad logowania"
        
    decoded_password = password.decode()
    if(not check_password(input_password, decoded_password)):
        return "Blad logowania"
    
    session["uid"] = uuid.uuid4()
    session["date"] = (str)(datetime.now())
    session["login"] = login
    
    return redirect(url_for("home"))
    

@app.route('/sender/logout', methods=['get'])
def logout():
    response = make_response(redirect(url_for("home")))
    
    session.pop('uid', None)
    session.pop('date', None)
    session.pop('login', None)
    return response

@app.route('/sender/dashboard', methods=['get'])
def show_dashboard():
     
    if(not g.is_logged):
        return "Nie masz uprawnien"
    
    login = session.get("login")
    r = get_db(2)
    
    try:
        packages_number = r.llen(login)
        packages = r.lrange(login, 0, packages_number - 1)
    except ConnectionError:
        return "Blad serwera"
    
    decoded_packages = [p.decode() for p in packages]
    
    table_dict = {}
    try:
        for dp in decoded_packages:
            data = []
            data.append(r.hget(dp, "receiver").decode())
            data.append(r.hget(dp, "post_id").decode())
            data.append(r.hget(dp, "size").decode())
            table_dict[dp] = data
    except ConnectionError:
        return "Blad serwera"
    
    return render_template("dashboard.html", is_logged=True, labels=table_dict)

@app.route('/sender/dashboard/new', methods=['get'])
def add_to_dashboard():
        
    if(not g.is_logged):
        return "Nie masz uprawnien"
    return render_template("dashboard_new.html", is_logged=True)

@app.route('/sender/dashboard', methods=['post'])
def added_to_dashboard():
    if(not g.is_logged):
        return "Nie masz uprawnien"
    login = session.get("login")
    r = get_db(2)
    
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
    
    try:
        r.hset((str)(package_id), "receiver", receiver)
        r.hset((str)(package_id), "post_id", post_id)
        r.hset((str)(package_id), "size", size)
        r.rpush(login, (str)(package_id))
    except ConnectionError:
        return "Blad serwera"
    
    return redirect(url_for("show_dashboard"))
    
@app.route('/sender/dashboard/<pid>', methods=['delete'])
def removed_from_dashboard(pid):
    if(not g.is_logged):
        return "Nie masz uprawnien"
        
    r = get_db(2)
    login = session.get("login")
    
    try:
        r.hdel(pid, "receiver")
        r.hdel(pid, "post_id")
        r.hdel(pid, "size")
        r.lrem(login, 1, pid)
    except ConnectionError:
        return "Blad serwera", 503
    
    return "", 204

def get_db(db_index):
    r = redis.Redis(
    host='localhost',
    port=6379,
    db=db_index)
    return r
    
def hash(plaintext):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plaintext.encode(), salt)
    return hashed.decode()
 
def check_password(input_password, hashed_password):
    return bcrypt.checkpw(input_password.encode(), hashed_password.encode())

    
if __name__ == '__main__':
    app.run( host="0.0.0.0", port="5000")