from flask import Flask, render_template, request, make_response, redirect, url_for, jsonify
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from db import SessionLocal, init_db
from models import Customer, Invoice
from db import init_db, initialize_invoice_tracker, InvoiceNumberTracker
from  flask import redirect, url_for
import pandas as pd
from flask import make_response
from weasyprint import HTML
from io  import BytesIO, StringIO
from xhtml2pdf import pisa
import pandas as pd
import json
from sqlalchemy.orm import joinedload   
from collections import defaultdict
import csv

SERVICE_DESCRIPTIONS = {'Change Order' : 'Change Order Description', 
                        'Change Order and Issue Reporting' : 'Change Order Issue Reporting Description',
                        'Project Fee' : 'Project Fee Description',
                        'Provisional Credit' : 'Provisional Credit Description',
                        }

init_db()
initialize_invoice_tracker()

app = Flask(__name__)

def calculate_total(rate, store_count, multiplier):
    # Convert inputs to floats if needed and handle None
    values = []
    for v in [rate, store_count, multiplier]:
        try:
            val = float(v)
        except (TypeError, ValueError):
            val = 0
        if val != 0:
            values.append(val)
    if not values:
        return 0
    total = 1
    for v in values:
        total *= v
    return total

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

@app.route('/invoiceConfirmation', methods=['POST'])
def invoiceConfirmation():

    customer_id = request.form.get('customer_id')

    with SessionLocal() as db:
        customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()

    if not customer:
        return "Customer not found", 404

    invoice_date = request.form.get("invoiceDate") #Gets date from the form on the homepage

    formatted_invoice_date = ""
    if invoice_date:
        try:
            dt = datetime.strptime(invoice_date, "%Y-%m-%d")
            formatted_invoice_date = dt.strftime("%m/%d/%Y")  # Convert to MM/DD/YYYY
        except ValueError:
            formatted_invoice_date = ""

    invoice_total = request.form.get("invoice_total", 0)

    try:
        invoice_total = float(invoice_total)
    except ValueError:
        invoice_total = 0.0

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
    
    # makes total dynamic
    rate = float(customer.rate) if customer.rate else 0
    store_count = int(customer.store_count) if customer.store_count else 0
    multiplier = float(customer.multiplier) if customer.multiplier else 0

    calculated_total = calculate_total(rate, store_count, multiplier)
    other_total = sum(amount for _, amount, _ in other_services_with_details)
    total_amount = calculated_total + other_total

    # Generates QA invoice number
    with SessionLocal() as db:
        tracker = db.query(InvoiceNumberTracker).first()
        if not tracker:
            return "Invoice tracker not initialized", 500

        tracker.last_number += 1
        qa_invoice_num = f"QA{tracker.last_number}"
        db.add(tracker)
        db.commit()


    # Convert string date to actual Date object
    actual_invoice_date = None
    due_date = None

    
    if invoice_date:
        try:
            actual_invoice_date = datetime.strptime(invoice_date, "%Y-%m-%d").date()
            # Compute due date using payment term
            payment_term = customer.paymentTerm or 0
            due_date = actual_invoice_date + timedelta(days=payment_term)
        except ValueError:
            pass

    # --- Step 4: Render confirmation template ---
    rendered_html = render_template(
        'invoiceConfirmation_pdf.html',  # Use the correct template filename
        customer=customer,
        services=services_with_descriptions,
        other_services=other_services_with_details,
        invoice_date=formatted_invoice_date,
        qa_invoice_num=qa_invoice_num,
        due_date=due_date.strftime("%m/%d/%Y") if due_date else None,
        total = invoice_total
    )

    # Calculate total amount from services and other services
    total_amount = sum(service_amounts.values()) + sum(amount for _, amount, _ in other_services_with_details)

   # Prepare folders and save PDF
    base_folder = 'Invoices'

    # Save Cesears invoices to subfolder
    if 'Cesears' in customer.name:
        save_folder = os.path.join(base_folder, 'Cesears')
    else:
        save_folder = base_folder

    os.makedirs(save_folder, exist_ok=True)

    safe_name = customer.name.replace(' ', '_').replace('/', '_')
    filename = f"invoice_{safe_name}_{qa_invoice_num}.pdf"
    filepath = os.path.join(save_folder, filename)

    with SessionLocal() as db:
        customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
        if not customer:
            return "Customer not found", 404

        # Create and save new invoice
        new_invoice = Invoice(
            customer_id=customer.id,
            invoice_date=actual_invoice_date,
            amount=total_amount,
            qa_invoice_num=qa_invoice_num,
            paid=False  # default to unpaid
        )
        db.add(new_invoice)
        db.commit()


    # Generate PDF
    pdf_file = BytesIO()
    pisa_status = pisa.CreatePDF(rendered_html, dest=pdf_file)

    if pisa_status.err:
        return "Failed to generate PDF", 500

    # Save PDF to file
    with open(filepath, 'wb') as f:
        f.write(pdf_file.getvalue())

    return f"Invoice saved to {filepath}"



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
                invoice_name=row['invoice_name'],
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
            
    def safe_int(val, default):
        try:
            if val is None or val.strip() == '':
                return default
            return int(val)
        except Exception:
            return default
            
    def safe_decimal(val, default):
        try:
            if val is None or val.strip() == '':
                return default
            return Decimal(val)
        except Exception:
            return default

            
    with SessionLocal() as db:
        customers = db.query(Customer).all()
        for cust in customers:

            rate_val = form_data.get(f'rate_{cust.id}', cust.rate)
            store_count_val = form_data.get(f'store_count_{cust.id}', cust.store_count)
            multiplier_val = form_data.get(f'multiplier_{cust.id}', cust.multiplier)
            try:
                cust.rate = float(rate_val) if rate_val not in (None, '') else 0
            except Exception:
                cust.rate = 0

            try:
                cust.store_count = int(store_count_val) if store_count_val not in (None, '') else 0
            except Exception:
                cust.store_count = 0

            try:
                cust.multiplier = float(multiplier_val) if multiplier_val not in (None, '') else 0
            except Exception:
                cust.multiplier = 0    

            cust.total = Decimal(calculate_total(cust.rate, cust.store_count, cust.multiplier))
        
            cust.name = form_data.get(f'name_{cust.id}', cust.name)
            cust.location = form_data.get(f'location_{cust.id}', cust.location)
            cust.email = form_data.get(f'email_{cust.id}', cust.email)
            cust.store_count = safe_int(form_data.get(f'store_count_{cust.id}'), cust.store_count)
            cust.rate = form_data.get(f'rate_{cust.id}', cust.rate)
            cust.amount = safe_decimal(form_data.get(f'amount_{cust.id}'), cust.amount)
            cust.vendornum = form_data.get(f'vendornum_{cust.id}', cust.vendornum)
            cust.currentPurchaseOrderNum = form_data.get(f'currentPurchaseOrderNum_{cust.id}', cust.currentPurchaseOrderNum)
            cust.paymentTerm = safe_int(form_data.get(f'paymentTerm_{cust.id}'), cust.paymentTerm)
            cust.currentPO = form_data.get(f'currentPO_{cust.id}', cust.currentPO)
            cust.nextPO = form_data.get(f'nextPO_{cust.id}', cust.nextPO)
            cust.unitPrice = safe_decimal(form_data.get(f'unitPrice_{cust.id}'), cust.unitPrice)
            cust.totalPrice = safe_decimal(form_data.get(f'totalPrice_{cust.id}'), cust.totalPrice)
            cust.fixedPrice = safe_decimal(form_data.get(f'fixedPrice_{cust.id}'), cust.fixedPrice)
            cust.total = safe_decimal(form_data.get(f'total_{cust.id}'), cust.total)
            cust.multiplier = safe_decimal(form_data.get(f'multiplier_{cust.id}'), cust.multiplier)
            cust.currentPOtotal = safe_decimal(form_data.get(f'currentPOtotal_{cust.id}'), cust.currentPOtotal)

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

            cust.invoiced = f"invoiced_{cust.id}" in request.form
            cust.emailed = f"emailed_{cust.id}" in request.form
            cust.online = f"online_{cust.id}" in request.form
            cust.backup_required = f"backup_required_{cust.id}" in request.form

        db.commit() 
    return redirect(url_for('index'))

@app.route('/customerInfo/<int:customer_id>', methods=['GET', 'POST'])
def customerInfo(customer_id):
    # Get total passed as query parameter (string)
    total_from_query = request.args.get('total', None)

    with SessionLocal() as db:
        cust = db.query(Customer).filter(Customer.id == customer_id).first()
        if not cust:
            return "Customer not found", 404

        if request.method == 'POST':
            form = request.form

            # Update simple fields here (your existing logic)
            simple_fields = [
                "location", "email", "store_count", "rate", "amount", "vendornum", "currentPurchaseOrderNum",
                "paymentTerm", "currentPO", "nextPO", "unitPrice", "totalPrice", "fixedPrice", "currentPOtotal",
                "nextPOtotal"
            ]
            for field in simple_fields:
                if field in form:
                    value = form.get(field)
                    if field in ["store_count", "paymentTerm"]:
                        try:
                            value = int(value)
                        except:
                            value = None
                    elif field in ["amount", "rate", "unitPrice", "totalPrice", "fixedPrice", "currentPOtotal", "nextPOtotal"]:
                        try:
                            value = float(value)
                        except:
                            value = None
                    setattr(cust, field, value)

            # Date fields
            for date_field in ["currentPOExpDate", "nextPOExpDate"]:
                if date_field in form:
                    date_str = form.get(date_field)
                    if date_str:
                        try:
                            setattr(cust, date_field, datetime.strptime(date_str, '%Y-%m-%d'))
                        except:
                            setattr(cust, date_field, None)
                    else:
                        setattr(cust, date_field, None)

            # Update services if present
            if any(key.startswith('service_types') for key in form.keys()):
                selected_services = form.getlist('service_types[]')
                cust.service_types = ",".join(selected_services) if selected_services else None

                service_amounts_dict = {}
                for service in selected_services:
                    amt = form.get(f'service_amounts[{service}]')
                    try:
                        service_amounts_dict[service] = str(Decimal(amt)) if amt else "0"
                    except:
                        service_amounts_dict[service] = "0"
                cust.service_amounts = json.dumps(service_amounts_dict) if service_amounts_dict else None

                other_services = form.getlist("other_services[]")
                other_amounts = form.getlist("other_service_amounts[]")
                other_service_details = form.getlist("other_service_detail_descriptions[]")

                cust.other_service_descriptions = "||".join(other_services) if other_services else None
                cust.other_service_amounts = ",".join(other_amounts) if other_amounts else None
                cust.other_service_detail_descriptions = "||".join(other_service_details) if other_service_details else None

            db.add(cust)
            db.commit()

            return {"status": "success"}

        # --- GET Request: Prepare data ---
        service_amounts = {}
        if cust.service_amounts:
            try:
                service_amounts = json.loads(cust.service_amounts)
            except json.JSONDecodeError:
                service_amounts = {}

        other_services = cust.other_service_descriptions.split("||") if cust.other_service_descriptions else []
        other_amounts = cust.other_service_amounts.split(",") if cust.other_service_amounts else []
        other_service_details = cust.other_service_detail_descriptions.split("||") if cust.other_service_detail_descriptions else []

        # Use total from query param if present, else fallback to DB value
        displayed_total = total_from_query if total_from_query is not None else str(cust.total)

        return render_template(
            'customerInfo.html',
            cust=cust,
            service_amounts=service_amounts,
            other_services=other_services,
            other_amounts=other_amounts,
            other_service_descriptions=other_services,
            other_service_detail_descriptions=other_service_details,
            displayed_total=displayed_total
        )

@app.route("/paymentStatus", methods=["GET", "POST"])
def paymentStatus():
    filter_name = request.args.get("filter_name", "")

    with SessionLocal() as db:
        query = db.query(Customer).options(joinedload(Customer.invoices))
        if filter_name:
            query = query.filter(Customer.name.ilike(f"%{filter_name}%"))
        customers = query.all()

        # Compute amount including "other services"
        for cust in customers:
            # Parse other_service_amounts CSV string once per customer
            other_services = cust.other_service_amounts or ""
            try:
                other_service_values = [float(x) for x in other_services.split(",") if x.strip()]
            except ValueError:
                other_service_values = []

            for inv in cust.invoices:
                base_amount = float(inv.amount or 0)
                inv.amount_with_services = base_amount + sum(other_service_values)
                # Ensure amount_paid exists
                if not hasattr(inv, "amount_paid") or inv.amount_paid is None:
                    inv.amount_paid = 0

    return render_template("paymentStatus.html", customers=customers, filter_name=filter_name)



@app.route('/reports')
def reports():
    with SessionLocal() as db:
        invoices = db.query(Invoice).all()
        customers = {c.id: c.name for c in db.query(Customer).all()}

        grouped = defaultdict(list)
        for inv in invoices:
            if inv.invoice_date:
                key = inv.invoice_date.strftime('%Y-%m')  # "2025-08"
                invoice_number = inv.qa_invoice_num if inv.qa_invoice_num else f"Q&A-{inv.customer_id:04d}"
                grouped[key].append({
                    "invoice_number": invoice_number,
                    "customer_name": customers.get(inv.customer_id, "Unknown"),
                    "invoice_date": inv.invoice_date.strftime('%Y-%m-%d'),
                    "total": str(inv.amount),
                    "status": "Paid" if inv.paid else "Unpaid"
                })

        months = sorted(grouped, reverse=True)

    return render_template("reports.html", monthly_reports=grouped, months=months)

@app.route('/download_csv', methods=['POST'])
def download_csv():
    month = request.form.get('month')
    if not month:
        return "Missing month", 400

    with SessionLocal() as db:
        invoices = db.query(Invoice).filter(Invoice.invoice_date.like(f"{month}-%")).all()
        customers = {c.id: c.name for c in db.query(Customer).all()}

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Invoice #", "Customer", "Date", "Total", "Status"])

        for inv in invoices:
            writer.writerow([
                inv.qa_invoice_num if inv.qa_invoice_num else f"Q&A-{inv.customer_id:04d}",
                customers.get(inv.customer_id, "Unknown"),
                inv.invoice_date.strftime("%Y-%m-%d") if inv.invoice_date else "N/A",
                str(inv.amount),
                "Paid" if inv.paid else "Unpaid"
            ])


        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={month}_invoices.csv"
        response.headers["Content-Type"] = "text/csv"
        return response
    

@app.route("/update_payment_status", methods=["POST"])
def update_payment_status():
    data = request.get_json()
    invoice_id = data.get("invoice_id")
    field = data.get("field")
    value = data.get("value")

    with SessionLocal() as db:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return jsonify(success=False, error="Invoice not found"), 404

        if field == "paid":
            # Convert string/boolean JSON value to Python bool
            invoice.paid = value in [True, "true", "True", 1, "1"]
        elif field == "amount_paid":
            try:
                invoice.amount_paid = Decimal(value) if value else 0
            except Exception:
                invoice.amount_paid = 0

        db.commit()

    return jsonify(success=True)



if __name__ == '__main__':      
    app.run(host='0.0.0.0', port=os.environ.get('FLASK_PORT', 5000), debug=os.environ.get('FLASK_DEBUG', True))