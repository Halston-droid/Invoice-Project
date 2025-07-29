from flask import Flask, render_template, request
import os
from datetime import date
from datetime import datetime
from decimal import Decimal
from db import SessionLocal, init_db
from models import Customer
from db import init_db
from  flask import redirect, url_for
import pandas as pd

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
            amount = request.form['amount'],
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
            currentPOExpDate = datetime.strptime(request.form['currentPOExpDate'], '%Y-%m-%d').date(),
            nextPOtotal = Decimal(request.form['nextPOtotal']),
            nextPOExpDate = datetime.strptime(request.form['nextPOExpDate'], '%Y-%m-%d').date(),
        )

        with SessionLocal() as db:
            db.add(new_customer)
            db.commit()
            all_customers = db.query(Customer).all()

        return render_template('index.html', customers=all_customers)
    
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


@app.route('/import_excel', methods=['POST'])
def import_excel():
    file = request.files.get('file')

    if not file or file.filename == '':
            return "No file uploaded", 400

    # Read Excel into DataFrame
    df = pd.read_excel(file, engine='openpyxl')

    # Helper to safely convert dates
    def parse_date(val):
        if pd.isnull(val):
            return None
        if isinstance(val, datetime):
            return val
        try:
            return datetime.strptime(str(val), '%Y-%m-%d')
        except ValueError:
            try:
                return datetime.strptime(str(val), '%m/%d/%Y')
            except Exception:
                return None

    with SessionLocal() as db:
        for _, row in df.iterrows():
            customer = Customer(
                name=row['name'],
                location=row['location'],
                store_count=int(row['store_count']),
                rate=row['rate'],
                amount=Decimal(row['amount']),
                email=row['email'],
                vendornum=row['vendornum'],
                currentPurchaseOrderNum=row['currentPurchaseOrderNum'],
                paymentTerm=int(row['paymentTerm']),
                currentPO=row['currentPO'],
                nextPO=row['nextPO'],
                numStores=int(row['numStores']),
                unitPrice=Decimal(row['unitPrice']),
                totalPrice=Decimal(row['totalPrice']),
                fixedPrice=Decimal(row['fixedPrice']),
                currentPOtotal=Decimal(row['currentPOtotal']),
                currentPOExpDate=parse_date(row['currentPOExpDate']),
                nextPOtotal=Decimal(row['nextPOtotal']),
                nextPOExpDate=parse_date(row['nextPOExpDate'])
            )
            db.add(customer)
        db.commit()

    return redirect(url_for('index'))


if __name__ == '__main__':      
    app.run(host='0.0.0.0', port=os.environ.get('FLASK_PORT', 5000), debug=os.environ.get('FLASK_DEBUG', True))
