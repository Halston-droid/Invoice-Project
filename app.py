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
from flask import make_response
from weasyprint import HTML
from io  import BytesIO
from xhtml2pdf import pisa
import pandas as pd

init_db()

app = Flask(__name__)

init_db() 

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
def newInvoice(customer_id=None):
    with SessionLocal() as db:
        customers = db.query(Customer).all()
    selected_customer = None
    if customer_id:
        selected_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    return render_template('newInvoice.html', customers=customers, selected_customer=selected_customer)

@app.route('/invoiceConfirmation', methods=['POST'])
def invoiceConfirmation():
    customer_id = request.form.get('customer_id')
    
    with SessionLocal() as db:
        customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()

    if not customer:
        return "Customer not found", 404

    # Build the HTML content dynamically
    invoice_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h1 {{ text-align: center; }}
            p {{ margin: 5px 0; }}
        </style>
    </head>
    <body>
        <h1>Invoice Confirmation</h1>
        <p><strong>Q&A Payment Solutions Inc</strong><br>
        EIN: 68-0679829<br>
        #105 - 325 1933 State Route 35 Wall NJ 07719<br>
        O: 732-449-3579<br>
        E: accounts@qandapaymentsolutions.com</p>

        <p><strong>Customer:</strong> {customer.name}</p>
        <p><strong>Location:</strong> {customer.location}</p>
        <p><strong>Email:</strong> {customer.email}</p>
        <p><strong>Store Count:</strong> {customer.store_count}</p>
        <p><strong>Rate:</strong> {customer.rate}</p>
        <p><strong>Vendor Number:</strong> {customer.vendornum}</p>
        <p><strong>Current Purchase Order Number:</strong> {customer.currentPurchaseOrderNum}</p>
        <p><strong>Payment Term:</strong> {customer.paymentTerm}</p>
        <p><strong>Current PO:</strong> {customer.currentPO}</p>
        <p><strong>Next PO:</strong> {customer.nextPO}</p>
        <p><strong>Unit Price:</strong> {customer.unitPrice}</p>
        <p><strong>Total Price:</strong> {customer.totalPrice}</p>
        <p><strong>Fixed Price:</strong> {customer.fixedPrice}</p>
        <p><strong>Current PO Total:</strong> {customer.currentPOtotal}</p>
        <p><strong>Current PO Expiration Date:</strong> {customer.currentPOExpDate}</p>
        <p><strong>Next PO Total:</strong> {customer.nextPOtotal}</p>
        <p><strong>Next PO Expiration Date:</strong> {customer.nextPOExpDate}</p>
    </body>
    </html>
    """

    # Generate PDF
    pdf_file = BytesIO()
    pisa_status = pisa.CreatePDF(invoice_content, dest=pdf_file)

    if pisa_status.err:
        return "Failed to generate PDF", 500

    pdf_file.seek(0)
    response = make_response(pdf_file.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{customer.name}.pdf'
    return response


@app.route('/import_excel', methods=['POST'])
def import_excel():
    file = request.files.get('file')

    if not file or file.filename == '':
            return "No file uploaded", 400

    # Read Excel into DataFrame
    df = pd.read_excel(file, engine='openpyxl')

    # Helper to convert dates
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

@app.route('/update_customers', methods=['POST'])
def update_customers():
    form_data = request.form
    def parse_date_(val):
        if pd.isnull(val) or val == '':
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
        customers = db.query(Customer).all()
        for cust in customers:
            cust.name = form_data.get(f'name_{cust.id}', cust.name)
            cust.location = form_data.get(f'location_{cust.id}', cust.location)
            cust.email = form_data.get(f'email_{cust.id}', cust.email)
            cust.store_count = int(form_data.get(f'store_count_{cust.id}', cust.store_count))
            cust.rate = form_data.get(f'rate_{cust.id}', cust.rate)
            cust.amount = Decimal(form_data.get(f'amount_{cust.id}', cust.amount))
            cust.vendornum = form_data.get(f'vendornum_{cust.id}', cust.vendornum)
            cust.currentPurchaseOrderNum = form_data.get(f'currentPurchaseOrderNum_{cust.id}', cust.currentPurchaseOrderNum)
            cust.paymentTerm = int(form_data.get(f'paymentTerm_{cust.id}', cust.paymentTerm))
            cust.currentPO = form_data.get(f'currentPO_{cust.id}', cust.currentPO)
            cust.nextPO = form_data.get(f'nextPO_{cust.id}', cust.nextPO)
            cust.unitPrice = Decimal(form_data.get(f'unitPrice_{cust.id}', cust.unitPrice))
            cust.totalPrice = Decimal(form_data.get(f'totalPrice_{cust.id}', cust.totalPrice))
            cust.fixedPrice = Decimal(form_data.get(f'fixedPrice_{cust.id}', cust.fixedPrice))
            cust.currentPOtotal = Decimal(form_data.get(f'currentPOtotal_{cust.id}', cust.currentPOtotal))
            currentDate = parse_date_(form_data.get(f'currentPOExpDate_{cust.id}', ''))
            cust.currentPOExpDate = currentDate.date() if currentDate else None
            cust.nextPOtotal = Decimal(form_data.get(f'nextPOtotal_{cust.id}', cust.nextPOtotal))
            nextDate = parse_date_(form_data.get(f'nextPOExpDate_{cust.id}', ''))
            cust.nextPOExpDate = nextDate.date() if nextDate else None
        db.commit() 
    return redirect(url_for('index'))

@app.route('/customerInfo/<int:customer_id>', methods=['GET', 'POST'])
def customerInfo(customer_id):
    with SessionLocal() as db:
        cust = db.query(Customer).filter(Customer.id == customer_id).first()

        if request.method == 'POST':
            form = request.form

            def parse_date_(val):
                if pd.isnull(val) or val == '':
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

            cust.location = form.get('location')
            cust.email = form.get('email')
            cust.store_count = int(form.get('store_count'))
            cust.rate = form.get('rate')
            cust.amount = Decimal(form.get('amount'))
            cust.vendornum = form.get('vendornum')
            cust.currentPurchaseOrderNum = form.get('currentPurchaseOrderNum')
            cust.paymentTerm = int(form.get('paymentTerm'))
            cust.currentPO = form.get('currentPO')
            cust.nextPO = form.get('nextPO')
            cust.numStores = int(form.get('numStores'))
            cust.unitPrice = Decimal(form.get('unitPrice'))
            cust.totalPrice = Decimal(form.get('totalPrice'))
            cust.fixedPrice = Decimal(form.get('fixedPrice'))
            cust.currentPOtotal = Decimal(form.get('currentPOtotal'))

            currentDate = parse_date_(form.get('currentPOExpDate'))
            cust.currentPOExpDate = currentDate.date() if currentDate else None

            cust.nextPOtotal = Decimal(form.get('nextPOtotal'))

            nextDate = parse_date_(form.get('nextPOExpDate'))
            cust.nextPOExpDate = nextDate.date() if nextDate else None

            db.commit()
            return redirect(url_for('customerInfo', customer_id=customer_id))

        return render_template('customerInfo.html', cust=cust)


if __name__ == '__main__':      
    app.run(host='0.0.0.0', port=os.environ.get('FLASK_PORT', 5000), debug=os.environ.get('FLASK_DEBUG', True))
