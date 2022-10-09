from flask import Flask, render_template, request,redirect,url_for,session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length
import ibm_db as db
import re
import os
from dotenv import load_dotenv

load_dotenv()
HOSTNAME=os.getenv('HOSTNAME')
DATABASE=os.getenv('DATABASE')
PORT=os.getenv('PORT')
SECURITY=os.getenv('SECURITY')
UID=os.getenv('UID')
PWD=os.getenv('PWD')
app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY
#conn = db.connect("database=bludb;hostname=;port=32716;security=SSL;sslservercertificate=DigiCertGlobalRootCA.crt;uid=;pwd=",'','')
conn = db.connect("DATABASE="+str(DATABASE)+";HOSTNAME="+str(HOSTNAME)+";PORT="+str(PORT)+";SECURITY="+str(SECURITY)+";SSLServerCertificate=DigiCertGlobalRootCA1.crt;UID="+str(UID)+";PWD="+str(PWD), '', '')
class SignInForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    email = StringField('Email', validators=[InputRequired(), Length(min=5, max=20)], render_kw={"placeholder": "email"})
    rollNumber = StringField('Roll Number', validators=[InputRequired(), Length(min=1, max=20)], render_kw={"placeholder": "Roll Number"})
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "password"})


@app.route('/', methods=['GET', 'POST'])
def signin():
    form = SignInForm()
    if form.validate_on_submit():
        return redirect('/login')
    
    return render_template('signin.html', form=form)

class LoginInForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "password"})

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginInForm()
    global userid
    msg=''
    #if form.validate_on_submit():
    #    return redirect('/')
    if request.method=="POST":
        uname=form.username
        pw=form.password
        sql="SELECT * from users where username=? and password=?"
        stmt=db.prepare(conn,sql)
        db.bind_param(stmt,1,uname)
        db.bind_param(stmt,2,pw)
        db.execute(stmt)
        acct=db.fetch_assoc(stmt)
        if(acct):
            session['Logged In']=True
            session['id']=acct['username']
            userid==acct['username']
            session['username']=acct['username']
            msg="Logged In Succesfully"
            return render_template('welcome.html',msg=msg)
        else : msg="Invalid user/pw"

    return render_template('login.html', form=form)

@app.route('/dashboard', methods=['GET'])
def dashboard():
    return render_template('welcome.html')
if __name__ == "__main__":
    app.run(debug=True)

# 
# db.exec_immediate(conn, "DROP TABLE IF EXISTS user;")
# db.exec_immediate(conn, "CREATE TABLE user (email varchar(30), username varchar(30), rollNumber int(5), password varchar(30));")