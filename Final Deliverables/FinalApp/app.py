import ibm_db as db
from flask import Flask, render_template, request, redirect, session, abort
import os
import pathlib
import requests
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import resources_pb2, service_pb2, service_pb2_grpc
from clarifai_grpc.grpc.api.status import status_code_pb2
from werkzeug.utils import secure_filename
from datetime import date
import json
import pandas as pd
UPLOAD_FOLDER='/uploads'

# Configure Flask app
app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

# Load .env file
load_dotenv()

# Connect to the Database
HOSTNAME = os.getenv('HOSTNAME')
PORT_NUMBER = os.getenv('PORT_NUMBER')
DATABASE_NAME = os.getenv('DATABASE_NAME')
USERNAME = os.getenv('USER')
PASSWORD = os.getenv('PASSWORD')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_AUTH_CLIENT_ID')
NUTRITION_API_KEY = os.getenv('NUTRITION_API')

connection_string = "DATABASE={0};HOSTNAME={1};PORT={2};SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;PROTOCOL=TCPIP;UID={3};PWD={4};".format(DATABASE_NAME, HOSTNAME, PORT_NUMBER, USERNAME, PASSWORD)
conn = db.connect(connection_string, "", "")

# Frequently used variables
SIGN_UP_PAGE_URL = '/'
LOG_IN_PAGE_URL = '/login'
HOME_PAGE_URL = '/home'
GOOGLE_LOGIN_PAGE_URL = '/google_login'
PROFILE_PAGE_URL = '/profile'
CHANGE_PASSWORD_URL = '/changepwd'
FOOD_URL = '/food'
HISTORY_PAGE_URL = '/history'

# Google Auth Configuration
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)

#Clarifai api
C_USER_ID = os.getenv('C_USER_ID')
# Your PAT (Personal Access Token) can be found in the portal under Authentification
C_PAT = os.getenv('C_PAT')
C_APP_ID = 'main'
C_MODEL_ID = 'food-item-recognition'
IMAGE_URL = 'https://samples.clarifai.com/metro-north.jpg'

# Helper Function to execute SQL queries
def execute_sql(statement, **params):
    global conn
    stmt = db.prepare(conn, statement)
    
    param_id = 1
    for key, val in params.items():
        db.bind_param(stmt, param_id, val)
        param_id += 1
    
    result = ''
    try:
        db.execute(stmt)
        result = db.fetch_assoc(stmt)
    except:
        pass
    
    return result

def execute_Multisql(statement):
    print(statement)
    result = []
    global conn
    stmt = db.exec_immediate(conn, statement)
    dictionary = db.fetch_assoc(stmt)
    result.append(dictionary)
    while dictionary != False:
        dictionary = db.fetch_assoc(stmt)
        result.append(dictionary)
    # param_id = 1
    # for key, val in params.items():
    #     db.bind_param(stmt, param_id, val)
    #     param_id += 1
    
    # result = []
    # try:
    #     dictionary = db.fetch_assoc(stmt)
    #     print(dictionary)
    #     while dictionary != False:
    #         print(dictionary)
    #         result.append(dictionary)
    #         dictionary = db.fetch_assoc(stmt)
    # except:
    #     print('error in multisql')
    #     pass
    
    return result

# Creates user table if not exists
create_table = "CREATE TABLE IF NOT EXISTS user(email varchar(30), username varchar(30) NOT NULL, password varchar(30) , PRIMARY KEY(username))"
execute_sql(statement=create_table)
create_table = "CREATE TABLE IF NOT EXISTS stats(id integer NOT NULL, username varchar(30), uploadedOn DATE , result VARCHAR(32074), PRIMARY KEY(id), FOREIGN KEY(username) REFERENCES user(username) ON DELETE CASCADE)"
execute_sql(statement=create_table)

# Helper function to send confirmation mail on sign in
def send_confirmation_mail(user, email):
    message = Mail(
        from_email="nutritionassistant854@gmail.com",
        to_emails=email,
        subject="YAYY!! Your Account was created successfully!",
        html_content= "<strong>Account Created with username {0}</strong>".format(user)
    )
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e)

# Sign up page
@app.route(SIGN_UP_PAGE_URL, methods=['GET', 'POST'])
def signup():
    msg = ''
    
    if session.get('user'):
        return redirect(HOME_PAGE_URL)

    if request.method == 'POST':
        user = request.form['user']
        email = request.form['email']
        password = request.form['password']
        
        duplicate_check = "SELECT * FROM user WHERE username=?"
        account = execute_sql(statement=duplicate_check, user=user)
        
        if account:
            msg = "There is already an account with this username!"
        else:
            insert_query = "INSERT INTO user values(?, ?, ?)"
            execute_sql(statement=insert_query, email=email, user=user, password=password)

            send_confirmation_mail(user, email)
            return redirect(LOG_IN_PAGE_URL)
    return render_template('signup.html', msg=msg)

# Login page
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

# Login using Gmail
@app.route(GOOGLE_LOGIN_PAGE_URL , methods=['GET','POST'])
def google_login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

# Configuring user credentials after gmail login
@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if session["state"] != request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID,
        clock_skew_in_seconds=10
    )
    
    session["user"] = id_info.get("email")
    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    return redirect(HOME_PAGE_URL)

#Clarify and nutrion application 
@app.route(FOOD_URL,methods=['GET','POST'])
def foodpage():
    if not session.get('user'):
        return redirect(LOG_IN_PAGE_URL)
    msg=''
    user = session.get('user')
    channel = ClarifaiChannel.get_grpc_channel()
    stub = service_pb2_grpc.V2Stub(channel)

    metadata = (('authorization', 'Key ' + C_PAT),)

    userDataObject = resources_pb2.UserAppIDSet(user_id=C_USER_ID, app_id='main')
    
    #print(FILE_NAME)
    with open(FILE_NAME, "rb") as f:
        file_bytes = f.read()

    post_model_outputs_response = stub.PostModelOutputs(
        service_pb2.PostModelOutputsRequest(
            user_app_id=userDataObject,
            model_id=C_MODEL_ID,
            
            inputs=[
                resources_pb2.Input(
                    data=resources_pb2.Data(
                        image=resources_pb2.Image(
                        base64=file_bytes
                    )
                    )
                )
            ]
        ),
        metadata=metadata
    )

    if post_model_outputs_response.status.code != status_code_pb2.SUCCESS:
        print(post_model_outputs_response.status)
        raise Exception("Post model outputs failed, status: " + post_model_outputs_response.status.description)

    # Since we have one input, one output will exist here.
    output = post_model_outputs_response.outputs[0]
    query = ''
    #print("Predicted concepts:")
    for concept in output.data.concepts:
        #print("%s %.2f" % (concept.name, concept.value))
        if(concept.value>0.3):
            if len(query) > 0 and query[-1] != '&':
                query += " and "
            query += concept.name

    # Uncomment this line to print the full Response JSON
    #print(post_model_outputs_response)
    
    api_url = 'https://api.calorieninjas.com/v1/nutrition?query='
    
    response = requests.get(api_url + query, headers={'X-Api-Key': NUTRITION_API_KEY})
    if response.status_code != requests.codes.ok:
        print("Error:", response.status_code, response.text)
        abort(500)

    obj = json.loads(response.text)
    totalDict = {}
    for item in obj['items']:
        for key, value in item.items():
            if type(value) == str: 
                continue
            if totalDict.get(key, -1) != -1:
                totalDict[key] += value
            else:
                totalDict[key] = 0
    data = json.dumps(totalDict, indent=2)
    
    df = pd.DataFrame(obj["items"])
    df.insert(0, "Ingredients", query.split(" and "))
    df.drop('name', axis=1, inplace=True)
    df.drop('serving_size_g', axis=1, inplace=True)

    df.loc['Total']=df.sum(axis=0, numeric_only=True)
    df.iloc[-1, df.columns.get_loc('Ingredients')] = ''

    sqlst = "SELECT count(*) from stats"
    id = execute_sql(statement=sqlst)
    newId = int(id['1'])+1
    today = date.today()
    sqlst = "INSERT INTO stats values(?,?,?,?)"
    execute_sql(statement=sqlst , id = newId , username = user , date = today , result = data)


    return render_template('foodpage.html', msg=df.to_html())

# History
@app.route(HISTORY_PAGE_URL , methods=['GET','POST'])
def history():
    if not session.get('user'):
        return redirect(LOG_IN_PAGE_URL)
    msg = ''
    user = session.get('user')
    sqlst = f"SELECT * from stats where username = '{user}' ORDER BY id desc limit 10"
    result = execute_Multisql(statement = sqlst)
    #print(type(result))
    print(result)
    # outputStats = result['RESULT']
    # dateUploaded = result['UPLOADEDON']
    # #print(outputStats)
    totalDict = {}
    for item in result:
        if type(item) == bool:
            continue
        nutritionValues = json.loads(item['RESULT'])
        print(nutritionValues)
        tempdict = {}
        for key, value in nutritionValues.items():
            if tempdict.get(key, -1) != -1:
                tempdict[key] += value
            else:
                tempdict[key] = value
        for key, value in tempdict.items():
            if totalDict.get(key, -1) == -1:
                totalDict[key] = [value]
            else:
                totalDict[key].append(value)
    print(totalDict)
    # dictString = json.loads(outputStats)
    df = pd.DataFrame(totalDict)
    #df.insert(0, "Date", dateUploaded)

    
    return render_template('history.html', msg=df.to_html())
    

# Home page
@app.route(HOME_PAGE_URL, methods=['GET', 'POST'])
def homepage():
    if not session.get('user'):
        return redirect(LOG_IN_PAGE_URL)
    global FILE_NAME
    msg = ''
    if request.method == 'POST':
        if request.files['food']:
            img=request.files['food']
            #print(img.filename)
            #print("ABCD",)
            FILE_NAME=os.path.join('./uploads/',secure_filename(img.filename))
            print(FILE_NAME)
            img.save(FILE_NAME)
            
            msg = 'Image Uploaded Successfully!'
            return redirect(FOOD_URL)
        else:
            msg = "Image wasn't uploaded, Try again!"
        
    return render_template('homepage.html', user=session.get('user'), msg=msg)

# Profile page
@app.route(PROFILE_PAGE_URL, methods=['GET', 'POST'])
def profile():
    if not session.get('user'):
        return redirect(LOG_IN_PAGE_URL)
    
    sqlst = "select email from user where username=?"
    user = session.get('user')
    email = execute_sql(statement=sqlst, user=user)
    
    return render_template('profile.html', user=user, email=email['EMAIL'])

#change password
@app.route(CHANGE_PASSWORD_URL, methods=['GET', 'POST'])
def changepwd():
    if not session.get('user'):
        return redirect(LOG_IN_PAGE_URL)

    msg = ''
    user = ''
    email = ''
    if request.method == 'POST':
        user = session.get('user')
        oldpass = request.form['oldpass']
        newpass = request.form['newpass']

        sqlst = 'SELECT password from user where username = ?'
        dbpass = execute_sql(statement = sqlst , username = user)['PASSWORD']
        sqlst = 'SELECT email from user where username = ?'
        email = execute_sql(statement = sqlst ,username = user)['EMAIL']

        if dbpass == oldpass:
            sqlst = 'UPDATE user SET password = ? where username = ?'
            execute_sql(statement = sqlst , password = newpass , username = user)
            msg = 'Updated Successfully!'
        else:
            msg = 'Old Password Incorrect!'
        
        return render_template('profile.html', user=user, email=email, msg=msg)

    return render_template('passwordChange.html')


# Logout user
@app.route('/logout')
def logout():
    session['user'] = ''
    return redirect(LOG_IN_PAGE_URL)

# Delete user account
@app.route('/delete')
def delete():
    if not session.get('user'):
        return redirect(LOG_IN_PAGE_URL)

    user = session['user']
    delete_query = "DELETE FROM stats where username=?"
    execute_sql(statement=delete_query, username=user)
    delete_query = "DELETE FROM user WHERE username=?"
    execute_sql(statement=delete_query, username=user)
    
    session.clear()
    return redirect(SIGN_UP_PAGE_URL)    

# Run the application
if __name__ == '__main__':
    app.run(debug=True)