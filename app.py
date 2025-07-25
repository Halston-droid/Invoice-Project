from flask import Flask, render_template, request
import os
from datetime import date
from datetime import datetime
from decimal import Decimal
from db import SessionLocal, init_db
from models import Customer
from db import init_db

init_db()

app = Flask(__name__)

customers = {}
init_db() #boot-up schema

@app.route('/')
def index():
    with SessionLocal() as db:
        all_customers = db.query(Customer).all()
    return render_template('index.html', customers=all_customers)    

@app.route('/newCustomer', methods=['GET', 'POST'])
def newCustomer(): 
    if request.method == 'POST':
        new_customer = Customer(
        name = request.form['name'],
        location = request.form['location'],
        store_count = int(request.form['store_count']),
        rate = request.form['rate'],
        amount = Decimal(request.form['amount']),
        email = request.form['email'],
        vendornum = request.form['vendornum'],
        currentPurchaseOrderNum = request.form['currentPurchaseOrderNum'],
        paymentTerm = int(request.form['paymentTerm']),
        currentPO = request.form['currentPO'],
        nextPO = request.form['nextPO'],
        numStores = int(request.form['numStores']),
        unitPrice = Decimal(request.form['unitPrice']),
        totalPrice = Decimal(request.form['totalPrice']),
        fixedPrice = Decimal(request.form['fixedPrice']),
        currentPOtotal = Decimal(request.form['currentPOtotal']),
        currentPOExpDate = datetime.strptime(request.form['currentPOExpDate'], '%m/%d/%Y').date(),
        nextPOtotal = Decimal(request.form['nextPOtotal']),
        nextPOExpDate = datetime.strptime(request.form['nextPOExpDate'], '%m/%d/%Y').date(),
        )

        with SessionLocal() as db:
            db.add(new_customer)
            db.commit()
        return render_template('index.html', customers=[new_customer])
    
    return render_template('newCustomer.html')   

@app.route('/newInvoice', methods=['GET', 'POST'])
def newInvoice():
    with SessionLocal() as db:
        customers = db.query(Customer).all()
    return render_template('newInvoice.html', customers=customers)

@app.route('/invoiceConfirmation', methods=['POST'])
def invoiceConfirmation():
    customer_id = request.form.get('customer_id')
    with SessionLocal() as db:
        customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
    return render_template('invoiceConfirmation.html', customer=customer)  

if __name__ == '__main__':      
    app.run(host='0.0.0.0', port=os.environ.get('FLASK_PORT', 5000), debug=os.environ.get('FLASK_DEBUG', True))
