from flask import Flask, render_template, request
import os
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')    

@app.route('/newCustomer', methods=['POST'])
def newCustomer():
    name = request.form['newCustomer'] 
    return render_template('newCustomer.html', name=name)   

@app.route('/visual', methods=['POST'])
def newInvoice():
    visual = request.form['visual']
    return render_template('newInvoice.html', visual=visual)


if __name__ == '__main__':      
    app.run(host='0.0.0.0', port=os.environ.get('FLASK_PORT', 5000), debug=os.environ.get('FLASK_DEBUG', True))


 