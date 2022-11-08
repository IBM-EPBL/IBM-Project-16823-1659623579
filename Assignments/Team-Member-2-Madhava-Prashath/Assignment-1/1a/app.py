from flask import Flask, render_template, request
import os

app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

@app.route('/', methods=['GET', 'POST'])
def signin():
    return render_template('signin.html')

@app.route('/display', methods=['GET', 'POST'])
def welcome():
    user = request.form['user']
    email = request.form['email']
    phone = request.form['phone']
    return render_template('display.html', user=user, email=email, phone=phone)


if __name__ == '__main__':
    app.run(debug=True)