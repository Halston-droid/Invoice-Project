from flask import Flask, render_template, request
import os
app = Flask(__name__)

customers = {"Under Armour": {"location": "Baltimore, MD", "store_count": 50, "rate": "$20 per store", "amount": 1000},
             "Cesears": {"location": "Reno, NV", "store_count": 100, "rate": "$100 per store", "amount": 10000}}

@app.route('/')
def index():
    return render_template('index.html')    

@app.route('/newCustomer', methods=['GET', 'POST'])
def newCustomer(): 
    if request.method == 'POST':
        pass
    return render_template('newCustomer.html')   

@app.route('/newInvoice', methods=['GET', 'POST'])
def newInvoice():
    return render_template('newInvoice.html', customers=customers)

@app.route('/invoiceConfirmation', methods=['POST'])
def invoiceConfirmation():
      customer_name = request.form.get('customer')
      amount = customers[customer_name]['amount']
      return render_template('invoiceConfirmation.html', customer_name=customer_name, amount=amount)  

if __name__ == '__main__':      
    app.run(host='0.0.0.0', port=os.environ.get('FLASK_PORT', 5000), debug=os.environ.get('FLASK_DEBUG', True))
