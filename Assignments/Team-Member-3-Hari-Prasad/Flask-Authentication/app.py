from flask import Flask, render_template, redirect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length
import ibm_db as db
import os

app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

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
    if form.validate_on_submit():
        return redirect('/')

    return render_template('login.html', form=form)

if __name__ == "__main__":
    app.run(debug=True)

# conn = db.connect("database", "username", "password")
# db.exec_immediate(conn, "DROP TABLE IF EXISTS user;")
# db.exec_immediate(conn, "CREATE TABLE user (email varchar(30), username varchar(30), rollNumber int(5), password varchar(30));")