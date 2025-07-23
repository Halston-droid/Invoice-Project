from flask import Flask, render_template, request
import os
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')    

@app.route('/greet', methods=['POST'])
def greet():
    name = request.form['name'] 
    location = request.form['location']
    amount = request.form['amount']
    return render_template('greet.html', name=name, location=location, amount=amount)   

@app.route('/visual', methods=['POST'])
def visual():
    visual = request.form['visual']
    return render_template('visual.html', visual=visual)


if __name__ == '__main__':      
    app.run(host='0.0.0.0', port=os.environ.get('FLASK_PORT', 5000), debug=os.environ.get('FLASK_DEBUG', True))


 