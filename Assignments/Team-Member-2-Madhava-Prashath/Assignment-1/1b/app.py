from flask import Flask, render_template # First package from pypi.org
import os
import requests # Second Package from pypi.org
import pandas as pd # Third Package from pypi.org
import pyjokes # Fourth Package from pypi.org
import emoji # Fifth Package from pypi.org

app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

@app.route('/', methods=['GET', 'POST'])
def page():
    response = requests.get("https://type.fit/api/quotes")
    text = response.json()
    quote = pd.DataFrame(text).to_html()
    
    joke = pyjokes.get_joke()
    smilie = emoji.emojize(':panda:')
    return render_template('page.html', smilie=smilie, joke=joke, quote=quote)

if __name__ == '__main__':
    app.run(debug=True)