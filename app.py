from flask import Flask, render_template, request
import os
from datetime import date
from decimal import Decimal
from db import SessionLocal, init_db
from models import Customer

app = Flask(__name__)

customers = {}
init_db() #boot-up schema

# with SessionLocal() as db: #open transaction
#     ada = Customer(
#         name="Under Armour",
#         email="ada@example.com",
#         location="Baltimore, MD")

#     db.add(ada) # stage objects
#     db.commit() #write!

with SessionLocal() as db:
    all_customers = db.query(Customer).all() # simple SELECT *
    # for cust in all_customers:
    #     print(cust.name, cust.email, cust.id, cust.location)

@app.route('/')
def index():
    return render_template('index.html', customers=all_customers)    

@app.route('/newCustomer', methods=['GET', 'POST'])
def newCustomer(): 
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        store_count = request.form['store_count']
        rate = request.form['rate']
        amount = request.form['amount']

        customers[name] = {"location": location, "store_count": store_count, "rate": rate, "amount": amount}
    return render_template('newCustomer.html', customers=customers)   

@app.route('/newInvoice', methods=['GET', 'POST'])
def newInvoice():
    return render_template('newInvoice.html', customers=all_customers)

@app.route('/invoiceConfirmation', methods=['POST'])
def invoiceConfirmation():
    data = request.form['customer']
    print(type)
    customer1 = request.form.get('customer')
    print(customer1)
    #   
    #   print(customer1)
    return render_template('invoiceConfirmation.html', customer=customer1)  

if __name__ == '__main__':      
    app.run(host='0.0.0.0', port=os.environ.get('FLASK_PORT', 5000), debug=os.environ.get('FLASK_DEBUG', True))
