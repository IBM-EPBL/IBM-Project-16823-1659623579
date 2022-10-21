from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    
    return render_template('index.html')

@app.route('/display',methods=['GET', 'POST'])
def display():
    username = request.form['uname']
    email = request.form['email']
    phno = request.form['phno']
    print(email)
    return render_template('display.html', uname=username,email=email,phno=phno)
    
if __name__ == "__main__":
    app.run()