from flask import Flask, render_template, request, make_response
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
import json

SERVICE_DESCRIPTIONS = {'Change Order' : 'Change Order Description', 
                        'Change Order and Issue Reporting' : 'Change Order Issue Reporting Description',
                        'Project Fee' : 'Project Fee Description',
                        'Provisional Credit' : 'Provisional Credit Description',
                        }

init_db()

app = Flask(__name__)


@app.template_filter('fromjson')
def fromjson_filter(s):
    if not s:
        return {}
    return json.loads(s)

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

    # --- Step 1: Try getting selected services from form ---
    selected_services = request.form.getlist('service_types[]')
    service_amounts = {}

    if selected_services:
        for service in selected_services:
            key = f'service_amounts[{service}]'
            amount_str = request.form.get(key, '0.00')
            try:
                service_amounts[service] = float(amount_str)
            except ValueError:
                service_amounts[service] = 0.00
    else:
        # Fallback: Load from database
        if customer.service_amounts:
            try:
                service_amounts = {k: float(v) for k, v in json.loads(customer.service_amounts).items()}
            except Exception:
                service_amounts = {}

    # Step 2: Try getting other services from form
    other_services = request.form.getlist('other_services[]')
    other_amounts = request.form.getlist('other_service_amounts[]')
    other_details = request.form.getlist('other_service_detail_descriptions[]')  # <- ADD THIS

    other_services_with_details = []

    if other_services:
        for name, amt_str, detail in zip(other_services, other_amounts, other_details):
            if name.strip():
                try:
                    amt = float(amt_str)
                except ValueError:
                    amt = 0.00
                other_services_with_details.append((name, amt, detail))
    else:
        # Fallback: Load from database
        descriptions = customer.other_service_descriptions.split("||") if customer.other_service_descriptions else []
        amounts = customer.other_service_amounts.split(",") if customer.other_service_amounts else []
        details = customer.other_service_detail_descriptions.split("||") if customer.other_service_detail_descriptions else []

        for name, amt_str, detail in zip(descriptions, amounts, details):
            if name.strip():
                try:
                    amt = float(amt_str)
                except ValueError:
                    amt = 0.00
                other_services_with_details.append((name, amt, detail))


    # Step 3: attach hardcoded descriptions to services
    services_with_descriptions = []
    for name, amount in service_amounts.items():
        description = SERVICE_DESCRIPTIONS.get(name, '')  # fallback to blank
        services_with_descriptions.append({
            'name': name,
            'amount': amount,
            'description': description
        })


    # --- Step 4: Render confirmation template ---
    rendered_html = render_template(
        'invoiceConfirmation_pdf.html',  # Use the correct template filename
        customer=customer,
        services=services_with_descriptions,
        other_services=other_services_with_details
    )

    # Generate PDF
    pdf_file = BytesIO()
    pisa_status = pisa.CreatePDF(rendered_html, dest=pdf_file)

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
                nextPOExpDate=parse_date(row['nextPOExpDate']),
                total = Decimal(row['total']),
                multiplier = Decimal(row['multiplier'])
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
            date_str = form_data.get(f'currentPOExpDate_{cust.id}')

            if date_str is not None and date_str != '':
                currentDate = parse_date_(date_str)
                cust.currentPOExpDate = currentDate.date() if currentDate else None
            # else leave cust.currentPOExpDate as is, no change

            # same for nextPOExpDate
            date_str = form_data.get(f'nextPOExpDate_{cust.id}')
            if date_str is not None and date_str != '':
                nextDate = parse_date_(date_str)
                cust.nextPOExpDate = nextDate.date() if nextDate else None

        db.commit() 
    return redirect(url_for('index'))

@app.route('/customerInfo/<int:customer_id>', methods=['GET', 'POST'])
def customerInfo(customer_id):
    with SessionLocal() as db:
        cust = db.query(Customer).filter(Customer.id == customer_id).first()
        if not cust:
            return "Customer not found", 404

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

        if request.method == 'POST':
            form = request.form

            # Update customer fields (existing code omitted for brevity)...

            # Handle selected services
            selected_services = form.getlist('service_types[]')
            cust.service_types = ",".join(selected_services) if selected_services else None

            # Prepare service amounts
            service_amounts_dict = {}
            for service in selected_services:
                amt = form.get(f'service_amounts[{service}]')
                try:
                    service_amounts_dict[service] = str(Decimal(amt)) if amt else "0"
                except:
                    service_amounts_dict[service] = "0"
            cust.service_amounts = json.dumps(service_amounts_dict) if service_amounts_dict else None

            # Handle "Other" services (including new detail descriptions)
            other_services = form.getlist("other_services[]")
            other_amounts = form.getlist("other_service_amounts[]")
            other_service_details = form.getlist("other_service_detail_descriptions[]")

            # Save to DB (choose which "other service descriptions" you want to save)
            cust.other_service_descriptions = "||".join(other_services) if other_services else None
            cust.other_service_amounts = ",".join(other_amounts) if other_amounts else None
            cust.other_service_detail_descriptions = "||".join(other_service_details) if other_service_details else None

            db.add(cust)
            db.commit()

            return redirect(url_for('customerInfo', customer_id=customer_id))

        # ----- GET request: prepare service data for display -----
        service_amounts = {}
        if cust.service_amounts:
            try:
                service_amounts = json.loads(cust.service_amounts)
            except json.JSONDecodeError:
                service_amounts = {}

        other_services = cust.other_service_descriptions.split("||") if cust.other_service_descriptions else []
        other_amounts = cust.other_service_amounts.split(",") if cust.other_service_amounts else []
        other_service_details = cust.other_service_detail_descriptions.split("||") if cust.other_service_detail_descriptions else []

        return render_template(
            'customerInfo.html',
            cust=cust,
            service_amounts=service_amounts,
            other_services=other_services,
            other_amounts=other_amounts,
            other_service_descriptions=other_services,        # pass 'other_services' here (not undefined var)
            other_service_detail_descriptions=other_service_details
        )


if __name__ == '__main__':      
    app.run(host='0.0.0.0', port=os.environ.get('FLASK_PORT', 5000), debug=os.environ.get('FLASK_DEBUG', True))