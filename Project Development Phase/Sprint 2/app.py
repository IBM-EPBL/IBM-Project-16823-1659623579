import ibm_db as db
from flask import Flask, render_template, request, redirect, session
import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

load_dotenv()

HOSTNAME = os.getenv('HOSTNAME')
PORT_NUMBER = os.getenv('PORT_NUMBER')
DATABASE_NAME = os.getenv('DATABASE_NAME')
USERNAME = os.getenv('USER')
PASSWORD = os.getenv('PASSWORD')

connection_string = "DATABASE={0};HOSTNAME={1};PORT={2};SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;PROTOCOL=TCPIP;UID={3};PWD={4};".format(DATABASE_NAME, HOSTNAME, PORT_NUMBER, USERNAME, PASSWORD)
conn = db.connect(connection_string, "", "")

SIGN_UP_PAGE_URL = '/'
LOG_IN_PAGE_URL = '/login'
HOME_PAGE_URL = '/home'

def execute_sql(statement, **params):
    global conn
    stmt = db.prepare(conn, statement)
    
    param_id = 1
    for key, val in params.items():
        db.bind_param(stmt, param_id, val)
        param_id += 1
    
    db.execute(stmt)
    
    result = ''
    try:
        result = db.fetch_assoc(stmt)
    except:
        pass
    
    return result

create_table = "CREATE TABLE IF NOT EXISTS user(email varchar(30), username varchar(30), rollNumber int, password varchar(30))"
execute_sql(statement=create_table)

def send_confirmation_mail(user, email, rollnumber):
    message = Mail(
        from_email="nutritionassistant854@gmail.com",
        to_emails=email,
        subject="YAYY!! Your Account was created successfully!",
        html_content= "<strong>Account Created with username {0}</strong>".format(user)
    )
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
    except Exception as e:
        print(e)

@app.route(SIGN_UP_PAGE_URL, methods=['GET', 'POST'])
def signup():
    msg = ''
    
    if session.get('user'):
        return redirect(HOME_PAGE_URL)

    if request.method == 'POST':
        user = request.form['user']
        email = request.form['email']
        rollnumber = request.form['rollnumber']
        password = request.form['password']
        
        duplicate_check = "SELECT * FROM user WHERE username=?"
        account = execute_sql(statement=duplicate_check, user=user)
        
        if account:
            msg = "There is already an account with this username!"
        else:
            insert_query = "INSERT INTO user values(?, ?, ?, ?)"
            execute_sql(statement=insert_query, email=email, user=user, rollnumber=rollnumber, password=password)

            send_confirmation_mail(user, email, rollnumber)
            return redirect(LOG_IN_PAGE_URL)
    return render_template('signup.html', msg=msg)

@app.route(LOG_IN_PAGE_URL, methods=['GET', 'POST'])
def login():
    msg = ''
    
    if session.get('user'):
        return redirect(HOME_PAGE_URL)

    if request.method == "POST":

        user = request.form['user']
        password = request.form['password']
        
        duplicate_check = "SELECT * FROM user WHERE username=?"
        account = execute_sql(statement=duplicate_check, user=user)

        print(account)
        if account and account['PASSWORD'] == password:
            session['user'] = user
            return redirect(HOME_PAGE_URL)
        elif account and account['PASSWORD'] != password:
            msg = 'Invalid Password!'
        else:
            msg = "Invalid Username!"
            
    return render_template('login.html', msg=msg)

@app.route(HOME_PAGE_URL, methods=['GET', 'POST'])
def homepage():
    if not session.get('user'):
        return redirect(LOG_IN_PAGE_URL)
    
    msg = ""
    if request.method == "POST":
        if request.form["food"]:
            msg = "Image Recieved!"
        
    return render_template('homepage.html', user=session.get('user'), msg=msg)

@app.route('/logout')
def logout():
    session['user'] = ''
    return redirect(LOG_IN_PAGE_URL)

@app.route('/delete')
def delete():
    if not session.get('user'):
        return redirect(LOG_IN_PAGE_URL)

    user = session['user']
    delete_query = "DELETE FROM user WHERE username=?"
    execute_sql(statement=delete_query, user=user)
    
    session.clear()
    return redirect(SIGN_UP_PAGE_URL)    

if __name__ == '__main__':
    app.run(debug=True)