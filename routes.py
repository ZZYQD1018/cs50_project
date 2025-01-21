from flask import Flask, render_template, request, jsonify, Blueprint, redirect, url_for, flash, current_app
from project.models import Vendor, db, Dataset, Invoice, Budget, BudgetedInvoice, VendorContact, CurrencyRateAgainstUSD, Contract, ProjectCode, UserGroup, Documentation, Event, Tag
from werkzeug.utils import secure_filename
import os
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy import text
import pandas as pd


# Define the blueprint
main = Blueprint('main', __name__)




@main.route('/')
def home():
    today = date.today()

    contracts = db.session.query(Contract, Dataset, Vendor).join(Dataset, Contract.dataset_id == Dataset.id)\
        .filter(Dataset.dataset_status == 'licensed', Contract.is_active == True)\
        .join(Vendor, Vendor.id == Dataset.vendor_id)\
        .all()

    invoices_with_countdown = [
        {
            'contract': contract,
            'vendor': vendor,
            'dataset':dataset,
            'next_renewal_date': calculate_next_renewal(contract, today)[0],
            'renewal_notice_date': calculate_next_renewal(contract, today)[1]
            # 'countdown_days': (invoice.invoice_period_end_date - today).days  # Calculate days difference
        }
        for contract, dataset, vendor in contracts
    ]
    for item in invoices_with_countdown:
        item['renewal_notice_countdown'] = (item['renewal_notice_date'] - today).days
    invoices_with_countdown.sort(key=lambda x: x['renewal_notice_countdown'])
    return render_template('home.html',contracts = invoices_with_countdown, today=today)

def calculate_next_renewal(contract, today):
    commence_date = contract.contract_commence_date  # Assuming this is a datetime object
    frequency = int(contract.renewal_frequency)
    unit = contract.renewal_frequency_unit

    renewal_notice_day_count = contract.renewal_notice_day_count
    renewal_notice_day_type  = contract.renewal_notice_day_type

    # Calculate the smallest future renewal date
    next_renewal_date = commence_date
    while next_renewal_date <= today:
        if unit == 'M':  # Monthly
            next_renewal_date = next_renewal_date + timedelta(days=frequency * 30)  # Approximation for months
        elif unit == 'Q':  # Quarterly
            next_renewal_date = next_renewal_date + timedelta(days=frequency * 3 * 30)  # Approximation for quarters
        elif unit == 'Y':  # Yearly
            next_renewal_date = next_renewal_date + timedelta(days=frequency * 365)  # Approximation for years

    renewal_notice_date = next_renewal_date - timedelta(days=renewal_notice_day_count + 10) 

    return next_renewal_date, renewal_notice_date

@main.route('/vendors', methods=['GET'])
def vendors():
    vendors_list = Vendor.get_all_vendors()
    return render_template('vendors.html', vendors=vendors_list)

@main.route('/vendor/<int:vendor_id>', methods=['GET'])
def vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    datasets = Dataset.query.filter_by(vendor_id=vendor.id).all()  # Get datasets for the specific vendor

    sales_info = VendorContact.query.filter_by(vendor_id = vendor_id,position='Sales').all()
    support_info = VendorContact.query.filter_by(vendor_id = vendor_id,position='Support').all()
    am_info = VendorContact.query.filter_by(vendor_id = vendor_id,position='Account Manager').all()

    return render_template('vendor.html', vendor=vendor, datasets=datasets, acm_contacts = am_info, sales_contacts = sales_info, support_contacts = support_info)

@main.route('/vendor/contact/<int:contact_id>', methods=['GET'])
def get_contact_details(contact_id):
    contact = VendorContact.query.get_or_404(contact_id)
    return jsonify({
        'name': contact.name,
        'email': contact.email,
        'tel': contact.tel
    })

@main.route('/vendor/contact_details/<int:contact_id>', methods=['GET'])
def contact_details(contact_id):
    print('here')
    contact = VendorAccManager.query.get_or_404(contact_id)
    # Add logic to handle this action if necessary
    return render_template('contact_details.html', contact=contact)

@main.route('/vendor/delete_contact/<int:contact_id>', methods=['POST'])
def delete_contact(contact_id):
    contact = VendorAccManager.query.get_or_404(contact_id)
    db.session.delete(contact)
    db.session.commit()
    flash('Contact deleted successfully!', 'success')
    return jsonify({'success': True})


@main.route('/set_status/<int:dataset_id>', methods=['POST'])
def set_status(dataset_id):
    data = request.get_json()
    status = data.get('status')

    # Query dataset from the database
    dataset = Dataset.query.get(dataset_id)
    if dataset:
        dataset.dataset_status = status  # Update the status
        db.session.commit()
        return jsonify(success=True)
    else:
        return jsonify(success=False), 404

@main.route('/set_contract_status/<int:contract_id>', methods=['POST'])
def set_contract_status(contract_id):
    data = request.get_json()
    status = data.get('status')
    if status == 'True':
        status = True
    else:
        status = False
    # Query dataset from the database
    contract = Contract.query.get(contract_id)
    if contract:
        contract.is_active = status
        db.session.commit()
        return jsonify(success=True)
    else:
        return jsonify(success=False), 404

    
@main.route('/dataset/<int:dataset_id>', methods=['GET'])
def dataset(dataset_id):
    active_tab = request.args.get('active_tab', 'dataset-intro')
    dataset = Dataset.query.get_or_404(dataset_id)
    vendor = Vendor.query.filter_by(id = dataset.vendor_id).first()
    all_invoices = Invoice.query.filter_by(dataset_id=dataset_id).all()
    all_contracts = Contract.query.filter_by(dataset_id = dataset_id).all()
    all_documentations = Documentation.query.filter_by(dataset_id =dataset_id).all()
    all_events = Event.query.filter(dataset_id ==dataset_id).all()
    tags = [x.name for x in Tag.query.all()]
    dataset_tags = [x.name for x in dataset.tags]
    return render_template('dataset.html', dataset=dataset, invoices=all_invoices, vendor=vendor, contracts = all_contracts, documentations = all_documentations, active_tab = active_tab, events = all_events, tags = tags, dataset_tags = dataset_tags)


@main.route('/dataset/<int:dataset_id>/save_introduction', methods=['POST'])
def save_content(dataset_id):
    data = request.get_json()
    new_content = data.get('content')
    print(new_content)

    # Update the content in the database
    content = Dataset.query.filter(Dataset.id == dataset_id).first()
    content.introduction = new_content  # Update the existing content
    
    db.session.commit()  # Save changes to the database

    # Return success response
    return jsonify({'status': 'success'})

@main.route('/dataset/<int:dataset_id>/add_contract', methods=['POST'])
def add_contract(dataset_id):
    contract_signing_date = request.form['contract_signing_date']
    contract_signing_date = datetime.strptime(contract_signing_date, '%Y-%m-%d').date()
    contract_commence_date = request.form.get('contract_commence_date',None)
    if contract_commence_date:
        contract_commence_date = datetime.strptime(contract_commence_date, '%Y-%m-%d').date()
    renewal_frequency = request.form.get('renewal_frequency', None)
    renewal_frequency_unit = request.form.get('renewal_frequency_unit', None)
    print(renewal_frequency_unit)
    renewal_notice_day_count = request.form.get('renewal_notice_day_count', None)
    renewal_notice_day_type = request.form.get('renewal_notice_day_type', None)
    is_active = request.form['is_active']
    if is_active == 'True':
        is_active = True
    else:
        is_active = False
    file = request.files['contract_file']
    target_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'contracts',str(dataset_id))
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    if file and file.filename != '':
        filename = secure_filename(file.filename)
        filepath = os.path.join(target_folder, filename)
        file.save(filepath)

        # Add invoice record to the database
        contract = Contract(filename=filename, contract_signing_date=contract_signing_date, filepath=filepath, dataset_id=dataset_id, contract_commence_date = contract_commence_date, renewal_notice_day_count=renewal_notice_day_count, renewal_notice_day_type = renewal_notice_day_type, is_active = is_active, renewal_frequency = renewal_frequency, renewal_frequency_unit = renewal_frequency_unit)
        db.session.add(contract)
        db.session.commit()

        flash('Contract added successfully!', 'success')
    else:
        flash('Failed to add contract. Please select a file.', 'error')
    return redirect(url_for('main.dataset',dataset_id=dataset_id, active_tab = 'contracts'))


@main.route('/dataset/<int:dataset_id>/add_invoice', methods=['POST'])
def add_invoice(dataset_id):
    invoice_date = request.form['invoice_date']
    invoice_period_start_date = request.form['invoice_period_start_date']
    invoice_period_end_date = request.form['invoice_period_end_date']
    frequency = request.form['frequency']
    frequency_unit = request.form['frequency_unit']
    currency = request.form['currency']
    amount = request.form['amount']
    file = request.files['invoice_file']

    try:
        budgeted_year = request.form['budgeted_year']
        budgeted_vendor = request.form['budgeted_vendor']
        budgeted_dataset = request.form['budgeted_dataset']
        print([budgeted_year, budgeted_vendor, budgeted_dataset])

        # Find the budgeted_id based on the selected budgeted_year, vendor, and dataset
        budgeted_item = db.session.query(BudgetedInvoice).filter_by(
            budgeted_year=budgeted_year,
            budgeted_vendor=budgeted_vendor,
            budgeted_dataset=budgeted_dataset
        ).first()

        invoice_date = datetime.strptime(invoice_date, '%Y-%m-%d').date()
        invoice_period_start_date = datetime.strptime(invoice_period_start_date, '%Y-%m-%d').date()
        invoice_period_end_date = datetime.strptime(invoice_period_end_date, '%Y-%m-%d').date()


        target_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(dataset_id))
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(target_folder, filename)
            file.save(filepath)

            # Add invoice record to the database
            invoice = Invoice(filename=filename, invoice_date=invoice_date, filepath=filepath, dataset_id=dataset_id, invoice_period_start_date = invoice_period_start_date, invoice_period_end_date=invoice_period_end_date, frequency=frequency, frequency_unit = frequency_unit, amount = amount, currency=currency, budgeted_invoice_id=budgeted_item.id)
            db.session.add(invoice)
            db.session.commit()

            flash('Invoice added successfully!', 'success')
        else:
            flash('Failed to add invoice. Please select a file.', 'error')
        return redirect(url_for('main.dataset',dataset_id=dataset_id, active_tab = 'invoices'))
    except:
        invoice_date = datetime.strptime(invoice_date, '%Y-%m-%d').date()
        invoice_period_start_date = datetime.strptime(invoice_period_start_date, '%Y-%m-%d').date()
        invoice_period_end_date = datetime.strptime(invoice_period_end_date, '%Y-%m-%d').date()


        target_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'invoices',str(dataset_id))
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(target_folder, filename)
            file.save(filepath)

            # Add invoice record to the database
            invoice = Invoice(filename=filename, invoice_date=invoice_date, filepath=filepath, dataset_id=dataset_id, invoice_period_start_date = invoice_period_start_date, invoice_period_end_date=invoice_period_end_date, frequency=frequency, frequency_unit = frequency_unit, amount = amount, currency=currency)
            db.session.add(invoice)
            db.session.commit()
            flash('Invoice added successfully!', 'success')
        else:
            flash('Failed to add invoice. Please select a file.', 'error')
        return redirect(url_for('main.dataset',dataset_id=dataset_id, active_tab = 'invoices'))


@main.route('/dataset/<int:dataset_id>/add_docuentation', methods=['POST'])
def add_docuentation(dataset_id):
    print(request.form)
    file_type = request.form['file_type']
    file_link = request.form.get('file_link', None)
    comments = request.form.get('comments', None)
    
    target_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'documentations', str(dataset_id))
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    file = request.files.get('doc_file')  # Use .get() to avoid KeyError
    if file and file.filename:
        filename = secure_filename(file.filename)
        filepath = os.path.join(target_folder, filename)
        file.save(filepath)
        print(filepath)
    else:
        filepath = None
        filename=None

    # Add invoice record to the database
    documentation = Documentation(filetype=file_type, filelink=file_link, filename=filename, comments=comments, dataset_id = dataset_id, filepath = filepath)
    db.session.add(documentation)
    db.session.commit()

    return redirect(url_for('main.dataset',dataset_id=dataset_id, active_tab = 'documentations'))


@main.route('/dataset/<int:dataset_id>/add_event', methods=['POST'])
def add_event(dataset_id):
    file_link = request.form.get('event_link', None)
    event_date = request.form.get('event_date', None)
    event_date = pd.to_datetime(event_date)
    comments = request.form.get('comments', None)
    
    target_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'events', str(dataset_id))
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    file = request.files.get('event_file')  # Use .get() to avoid KeyError
    if file and file.filename:
        filename = secure_filename(file.filename)
        filepath = os.path.join(target_folder, filename)
        file.save(filepath)
        print(filepath)
    else:
        filepath = None
        filename=None

    # Add invoice record to the database
    event = Event(eventlink=file_link, filename=filename, comments=comments, dataset_id = dataset_id, filepath = filepath, event_date = event_date)
    db.session.add(event)
    db.session.commit()

    return redirect(url_for('main.dataset',dataset_id=dataset_id, active_tab = 'events'))
    

@main.route('/api/budgeted-years', methods=['GET'])
def get_budgeted_years():
    years = db.session.query(BudgetedInvoice.budgeted_year).distinct().all()
    return jsonify([year[0] for year in years])

@main.route('/api/budgeted-vendors/<year>', methods=['GET'])
def get_budgeted_vendors(year):
    vendors = db.session.query(BudgetedInvoice.budgeted_vendor).filter_by(budgeted_year=year).distinct().all()
    return jsonify([vendor[0] for vendor in vendors])

@main.route('/api/budgeted-datasets', methods=['GET'])
def get_budgeted_datasets():
    year = request.args.get('year')
    vendor = request.args.get('vendor')
    
    if not year or not vendor:
        return jsonify([])

    datasets = db.session.query(BudgetedInvoice.budgeted_dataset).filter_by(
        budgeted_year=year,
        budgeted_vendor=vendor
    ).distinct().all()

    return jsonify([dataset[0] for dataset in datasets])

@main.route('/dataset/<int:dataset_id>/invoice/<int:invoice_id>/delete_invoice', methods=['POST'])
def delete_invoice(invoice_id, dataset_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice:
        db.session.delete(invoice)  # Delete the vendor from the session
        db.session.commit()         # Commit the changes to the database
        os.remove(invoice.filepath)
        flash('Invoice deleted successfully!', 'success')
    else:
        flash('Invoice not found!', 'danger')

    return redirect(url_for('main.dataset',dataset_id=dataset_id, active_tab = 'invoices'))

@main.route('/dataset/<int:dataset_id>/invoice/<int:doc_id>/delete_documentation', methods=['POST'])
def delete_documentation(doc_id, dataset_id):
    doc = Documentation.query.get_or_404(doc_id)
    if doc:
        db.session.delete(doc)  # Delete the vendor from the session
        db.session.commit()         # Commit the changes to the database
        if doc.filepath:
            os.remove(doc.filepath)
        flash('Invoice deleted successfully!', 'success')
    else:
        flash('Invoice not found!', 'danger')

    return redirect(url_for('main.dataset',dataset_id=dataset_id, active_tab = 'documentations'))


@main.route('/dataset/<int:dataset_id>/invoice/<int:event_id>/delete_event', methods=['POST'])
def delete_event(event_id, dataset_id):
    event = Event.query.get_or_404(event_id)
    if event:
        db.session.delete(event)  # Delete the vendor from the session
        db.session.commit()         # Commit the changes to the database
        if event.filepath:
            os.remove(event.filepath)
        flash('Invoice deleted successfully!', 'success')
    else:
        flash('Invoice not found!', 'danger')

    return redirect(url_for('main.dataset',dataset_id=dataset_id, active_tab = 'events'))

@main.route('/dataset/<int:dataset_id>/contract/<int:contract_id>/delete_contract', methods=['POST'])
def delete_contract(contract_id, dataset_id):
    contract = Contract.query.get_or_404(contract_id)
    if contract:
        db.session.delete(contract)  # Delete the vendor from the session
        db.session.commit()         # Commit the changes to the database
        os.remove(contract.filepath)
        flash('Invoice deleted successfully!', 'success')
    else:
        flash('Invoice not found!', 'danger')

    return redirect(url_for('main.dataset',dataset_id=dataset_id, active_tab = 'contracts'))

@main.route('/vendor/<int:vendor_id>/add_dataset', methods=['POST'])
def add_dataset(vendor_id):
    dataset_name = request.form.get('dataset_name')

    existing_dataset = Dataset.query.filter_by(name=dataset_name, vendor_id=vendor_id).first()
    if existing_dataset:
        flash('Dataset name already exists! Please enter a different name.', 'danger')
    else:
        new_dataset = Dataset(name=dataset_name, vendor_id=vendor_id)
        db.session.add(new_dataset)
        db.session.commit()
        flash('New dataset added successfully!', 'success')
    return redirect(url_for('main.vendor', vendor_id=vendor_id))

@main.route('/vendor/<int:vendor_id>/add_vendor_contact', methods=['POST'])
def add_vendor_contact(vendor_id):
    position = request.form['position']
    name = request.form['name']
    email = request.form['email']
    tel = request.form['tel']
    comments = request.form.get('comments')

    new_contact = VendorContact(vendor_id=vendor_id, name=name, email=email, tel=tel, position = position,comments=comments)

    db.session.add(new_contact)
    db.session.commit()

    flash('Vendor contact added successfully!')
    return redirect(url_for('main.vendor', vendor_id=vendor_id))


@main.route('/dataset/<int:dataset_id>/delete_dataset', methods=['POST'])
def delete_dataset(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    vendor_id = dataset.vendor_id

    if dataset:
        db.session.delete(dataset)  # Delete the vendor from the session
        db.session.commit()         # Commit the changes to the database
        flash('Dataset deleted successfully!', 'success')
    else:
        flash('Dataset not found!', 'danger')

    return redirect(url_for('main.vendor', vendor_id=vendor_id))

@main.route('/vendor/<int:vendor_id>/update', methods=['POST'])
def update_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)

    data = request.get_json()
    introduction = data.get('introduction')

    # Update the introduction
    vendor.introduction = introduction
    db.session.commit()

    return jsonify(success=True)

@main.route('/add_vendor', methods=['POST'])
def add_vendor():
    vendor_name = request.form.get('vendor_name')

    # Check if the vendor already exists
    existing_vendor = Vendor.query.filter_by(name=vendor_name).first()
    if existing_vendor:
        flash('Vendor already exists! Please enter a different name.', 'danger')
    else:
        new_vendor = Vendor(name=vendor_name)  # Create a new Vendor instance
        db.session.add(new_vendor)              # Add it to the session
        db.session.commit()                     # Commit to the database
        flash('New vendor added successfully!', 'success')

    return redirect(url_for('main.vendors'))

# Route to delete a vendor
@main.route('/delete_vendor/<int:vendor_id>', methods=['POST'])
def delete_vendor(vendor_id):
    vendor = Vendor.query.get(vendor_id)

    if vendor:
        db.session.delete(vendor)  # Delete the vendor from the session
        db.session.commit()         # Commit the changes to the database
        flash('Vendor deleted successfully!', 'success')
    else:
        flash('Vendor not found!', 'danger')

    return redirect(url_for('main.vendors'))

# Route for Budget page
@main.route('/budgets')
def budgets():
    budgets = Budget.query.all()
    return render_template('budgets.html', title="Budget",budgets = budgets)


@main.route('/add_budget', methods=['POST'])
def add_budget():
    year = request.form.get('year')
    status = request.form.get('status')
    # vendor = request.form.get('budgeted_vendor')
    # dataset = request.form.get('budgeted_dataset')

    # last_invoice_frequency = request.form.get('last_invoice_frequency') if request.form.get('last_invoice_frequency') != '' else None
    # last_invoice_frequency_unit = request.form.get('last_invoice_frequency_unit') if request.form.get('last_invoice_frequency_unit') != '' else None
    # last_invoice_currency = request.form.get('last_invoice_currency') if request.form.get('last_invoice_currency') != '' else None
    # last_invoice_amount = request.form.get('last_invoice_amount') if request.form.get('last_invoice_amount') != '' else None
    new_budget = Budget(year = year, status = status)
    # new_budget = BudgetedInvoice(budgeted_year=year, budgeted_vendor=vendor, budgeted_dataset = dataset, last_invoice_currency = last_invoice_currency, last_invoice_frequency = last_invoice_frequency, last_invoice_frequency_unit = last_invoice_frequency_unit, last_invoice_amount = last_invoice_amount)  # Create a new Vendor instance
    db.session.add(new_budget)              # Add it to the session
    db.session.commit()                     # Commit to the database
    flash('New budget added successfully!', 'success')

    return redirect(url_for('main.budgets'))

@main.route('/add_indi_budget', methods=['POST'])
def add_indi_budget():
    year = request.form.get('year')
    # status = request.form.get('status')
    vendor = request.form.get('budgeted_vendor')
    dataset = request.form.get('budgeted_dataset')

    last_invoice_frequency = request.form.get('last_invoice_frequency') if request.form.get('last_invoice_frequency') != '' else None
    last_invoice_frequency_unit = request.form.get('last_invoice_frequency_unit') if request.form.get('last_invoice_frequency_unit') != '' else None
    last_invoice_currency = request.form.get('last_invoice_currency') if request.form.get('last_invoice_currency') != '' else None
    last_invoice_amount = request.form.get('last_invoice_amount') if request.form.get('last_invoice_amount') != '' else None
    # new_budget = Budget(year = year, status = status)
    new_budget = BudgetedInvoice(budgeted_year=year, budgeted_vendor=vendor, budgeted_dataset = dataset, last_invoice_currency = last_invoice_currency, last_invoice_frequency = last_invoice_frequency, last_invoice_frequency_unit = last_invoice_frequency_unit, last_invoice_amount = last_invoice_amount)  # Create a new Vendor instance
    db.session.add(new_budget)              # Add it to the session
    db.session.commit()                     # Commit to the database
    flash('New budget added successfully!', 'success')

    return redirect(url_for('main.budget', year = year))

@main.route('/budget/<int:year>')
def budget(year):
    budgets = BudgetedInvoice.query.filter_by(budgeted_year = year).all()
    print(budgets)
    return render_template('budget.html', year = year, budgets = budgets)

@main.route('/budget/<int:year>/smart_fill_in_budget', methods=['POST'])
def smart_fill_in_budget(year):
    res = db.session.query(Invoice.invoice_period_end_date,Invoice.frequency, Invoice.frequency_unit, Invoice.currency, Invoice.amount, Dataset.name, Vendor.name)\
        .join(Dataset, Invoice.dataset_id == Dataset.id)\
        .join(Vendor, Vendor.id == Dataset.vendor_id)\
        .filter(
        Dataset.dataset_status == 'licensed'
    ).all()
    df = pd.DataFrame(res, columns=['invoice_period_end_date', 'last_invoice_frequency', 'last_invoice_frequency_unit','last_invoice_currency','last_invoice_amount','budgeted_dataset','budgeted_vendor'])
    print(df)
    df['invoice_period_end_date'] = pd.to_datetime(df['invoice_period_end_date'])
    latest_rows = df.loc[df.groupby(['budgeted_vendor', 'budgeted_dataset'])['invoice_period_end_date'].idxmax()]
    # Reset index if needed
    latest_rows = latest_rows.reset_index(drop=True)
    print(latest_rows)
    data = latest_rows.drop(columns=['invoice_period_end_date'])
    data['budgeted_year'] = year

    # Convert DataFrame to list of dictionaries
    rows = data.to_dict(orient='records')

    try:
        db.session.bulk_insert_mappings(BudgetedInvoice, rows)
        db.session.commit() 
    except Exception as e:
        db.session.rollback()  # Rollback the transaction on error
        print(f"Error: {e}")
    finally:
        db.session.close()  # Always close the session

    return redirect(url_for('main.budget', year = year))

@main.route('/budget/<int:year>/delete_budgeted_item/<int:item_id>', methods=['POST'])
def delete_budgeted_item(item_id, year):
    budgeted_item = BudgetedInvoice.query.get_or_404(item_id)
    if budgeted_item:
        db.session.delete(budgeted_item)  # Delete the vendor from the session
        db.session.commit()         # Commit the changes to the database
        flash('Budgeted item deleted successfully!', 'success')
    else:
        flash('Budgeted item not found!', 'danger')

    return redirect(url_for('main.budget', year = year))

@main.route('/budget/set_budget', methods=['POST'])
def set_budget():
    data = request.get_json()  # Get the JSON data sent from the client
    item_id = data.get('item_id')
    budgeted_invoice_frequency = data.get('budgeted_invoice_frequency')
    budgeted_invoice_frequency_unit = data.get('budgeted_invoice_frequency_unit')
    budgeted_invoice_currency = data.get('budgeted_invoice_currency')
    budgeted_invoice_amount = data.get('budgeted_invoice_amount')
    print(item_id)
    print(data)

    # Here you would update the data in the database using SQLAlchemy or direct SQL queries
    try:
        # Assuming you have a model named `Data` where you can update the record
        # Example:
        row = BudgetedInvoice.query.filter_by(id = item_id).first()
        if row:
            row.budgeted_invoice_frequency = budgeted_invoice_frequency
            row.budgeted_invoice_frequency_unit = budgeted_invoice_frequency_unit
            row.budgeted_invoice_currency = budgeted_invoice_currency
            row.budgeted_invoice_amount = budgeted_invoice_amount
            db.session.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@main.route('/api/fetch-all-vendors', methods=['GET'])
def get_all_vendors():
    vendors = db.session.query(Vendor.name).distinct().all()
    return jsonify([vendor[0] for vendor in vendors])

@main.route('/api/fetch-all-vendors-for-a-vendor/<vendor>', methods=['GET'])
def get_all_datasets_of_a_vendor(vendor):
    datasets = db.session.query(Dataset.name).join(Vendor).filter(Vendor.name == vendor).all()
    print(jsonify([dataset[0] for dataset in datasets]))
    return jsonify([dataset[0] for dataset in datasets])


@main.route('/budget_analysis/<int:year>', methods=['GET', 'POST'])
def analysis(year):
    budgeted_items = (
    db.session.query(
            BudgetedInvoice.id.label('budgeted_id'),
            BudgetedInvoice.budgeted_invoice_amount.label('budgeted_amount'),
            BudgetedInvoice.budgeted_invoice_currency.label('budgeted_currency'),
            BudgetedInvoice.budgeted_vendor.label('budgeted_vendor'),
            BudgetedInvoice.budgeted_dataset.label('budgeted_dataset'),
            Invoice.id.label('invoice_id'),
            Invoice.currency.label('invoice_currency'),
            Invoice.amount.label('invoice_amount'),
            Invoice.filename.label('filename'),
            Invoice.dataset_id.label('dataset_id')
        )
        .join(Invoice, Invoice.budgeted_invoice_id == BudgetedInvoice.id)
        .filter(BudgetedInvoice.budgeted_year == year)
    ).all()
    budgeted_items_df= pd.DataFrame(budgeted_items, columns=['budgeted_id','budgeted_amount', 'budgeted_currency', 'budgeted_vendor','budgeted_dataset','invoice_id','invoice_currency','invoice_amount','filename','dataset_id'])
    unique_curs = set(budgeted_items_df['budgeted_currency']).union(set(budgeted_items_df['invoice_currency']))

    fx_rates = db.session.query(CurrencyRateAgainstUSD.currency, CurrencyRateAgainstUSD.rate).filter(CurrencyRateAgainstUSD.year == year, CurrencyRateAgainstUSD.currency.in_(unique_curs)).all()
    fx_rates_df = pd.DataFrame(fx_rates, columns = ['currency','rate'])

    all_fx_ates = db.session.query(CurrencyRateAgainstUSD.currency, CurrencyRateAgainstUSD.rate).filter(CurrencyRateAgainstUSD.year == year).all()

    if len(unique_curs- set(fx_rates_df['currency'])) - 1 != 0:
        return render_template('budget_analysis.html', year = year,rates = all_fx_ates)

    budgeted_items_df_merged = pd.merge(budgeted_items_df, fx_rates_df, left_on='budgeted_currency', right_on = 'currency', how='left')
    # Calculate the new column based on the condition
    budgeted_items_df_merged['budgeted_amount_converted'] = budgeted_items_df_merged.apply(
        lambda row: row['budgeted_amount'] if row['budgeted_currency'] == 'USD' else row['rate'] * row['budgeted_amount'],
        axis=1
    )

    budgeted_items_df_merged = pd.merge(budgeted_items_df_merged, fx_rates_df, left_on='invoice_currency', right_on = 'currency', how='left')
    # Calculate the new column based on the condition
    budgeted_items_df_merged['invoice_amount_converted'] = budgeted_items_df_merged.apply(
        lambda row: row['invoice_amount'] if row['invoice_currency'] == 'USD' else row['rate_y'] * row['invoice_amount'],
        axis=1
    )

    # Step 1: Group the data by 'id' and keep the unique budgeted_amount and list of actual_amounts
    table_data = (
        budgeted_items_df_merged.groupby('budgeted_id')
          .agg(budgeted_amount=('budgeted_amount_converted', 'first'), 
               budgeted_vendor=('budgeted_vendor', 'first'),
               budgeted_dataset=('budgeted_dataset', 'first'),
               actual_amounts=('invoice_amount_converted', list),
               file_list=('filename', list))
          .to_dict(orient='index')
    )

    total_budgeted = budgeted_items_df_merged.groupby('budgeted_id')['budgeted_amount_converted'].sum()
    total_actual = budgeted_items_df_merged.groupby('budgeted_id')['invoice_amount_converted'].sum()
    total_difference = total_budgeted - total_actual

    return render_template('budget_analysis.html', year = year, total_budgeted = total_budgeted, total_actual = total_actual, total_difference = total_difference, budget_info_table = table_data, rates = all_fx_ates)

@main.route('/rates/<int:year>')
def rates(year):
    # year = request.args.get('year', default=datetime.now().year, type=int)
    existing_rates = db.session.query(CurrencyRateAgainstUSD).filter(CurrencyRateAgainstUSD.year == year).all()
    return render_template('rates.html', rates=existing_rates, year=year)

@main.route('/update_rate', methods=['POST'])
def update_rate():
    currency = request.form['currency']
    new_rate = request.form['rate']
    year = request.form['year']
    
    if not currency or not new_rate or not year:
        return jsonify({'status': 'error', 'message': 'Currency, rate, and year are required!'})
    
    try:
        existing_rate = db.session.query(CurrencyRateAgainstUSD).filter(CurrencyRateAgainstUSD.year == year, CurrencyRateAgainstUSD.currency == currency).first()
        existing_rate.rate = new_rate
        db.session.commit()
        return jsonify({'status': 'success', 'message': f'Rate for {currency} in {year} added successfully!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@main.route('/add_rate/<int:year>', methods=['POST'])
def add_rate(year):
    currency = request.form['currency'].upper()
    rate = request.form['rate']

    existing_rate = db.session.query(CurrencyRateAgainstUSD).filter(CurrencyRateAgainstUSD.year == year, CurrencyRateAgainstUSD.currency == currency).first()
    if existing_rate:
        existing_rate.rate = rate
        db.session.commit()
        return redirect(url_for('main.analysis', year=year))
    else:
        try:
            new_rate = CurrencyRateAgainstUSD(rate = rate, year = year,currency = currency)
            db.session.add(new_rate)
            db.session.commit()
            return redirect(url_for('main.analysis', year=year))
        except Exception as e:
            return f"Error adding rate: {str(e)}"


@main.route('/admins', methods=['GET'])
def admins():
    project_codes = ProjectCode.query.all()
    user_groups = UserGroup.query.all()
    dataset_tags = Tag.query.all()
    return render_template('admins.html', project_codes=project_codes, user_groups = user_groups, dataset_tags = dataset_tags)


@main.route('/add_project_code', methods=['POST'])
def add_project_code():
    project_code = request.form['project_code']
    definition = request.form['definition']
    try:
        product_code_item = ProjectCode(code = project_code, definition=definition)
        db.session.add(product_code_item)
        db.session.commit()
        flash('Project code added successfully!', 'success')
    except Exception as e:
        flash(f'Failed to add project code: {e}', 'error')
    return redirect(url_for('main.admins'))

@main.route('/add_user_group', methods=['POST'])
def add_user_group():
    user_group = request.form['user_group']
    definition = request.form['definition']
    try:
        user_group_item = UserGroup(group_name = user_group, definition=definition)
        db.session.add(user_group_item)
        db.session.commit()
        flash('User group added successfully!', 'success')
    except Exception as e:
        flash(f'Failed to add user group: {e}', 'error')
    return redirect(url_for('main.admins'))


@main.route('/add_new_dataset_tag', methods=['POST'])
def add_new_dataset_tag():
    tag_name = request.form['tag_name']
    definition = request.form['definition']
    try:
        dataset_tag = Tag(name = tag_name, definition=definition)
        db.session.add(dataset_tag)
        db.session.commit()
        flash('User group added successfully!', 'success')
    except Exception as e:
        flash(f'Failed to add user group: {e}', 'error')
    return redirect(url_for('main.admins'))

@main.route('/save-tags/<int:dataset_id>', methods=['POST'])
def save_tags(dataset_id):
    selected_tags = request.json.get('selected_tags', [])
    dataset = Dataset.query.get_or_404(dataset_id)
    
    # Clear all existing tags for the dataset
    dataset.tags.clear()
    
    # Add the newly selected tags
    for tag in selected_tags:
        tag_obj = Tag.query.filter_by(name=tag).first()
        if tag_obj:
            dataset.tags.append(tag_obj)
    
    # Commit the changes to the database
    db.session.commit()
    
    print(f"Saved tags: {selected_tags}")
    return jsonify({"message": "Tags saved successfully!"})

@main.route('/datasets', methods=['GET'])
def datasets():
    datasets = Dataset.query.all()
    tags = [x.name for x in Tag.query.all()]
    return render_template('datasets.html', tags=tags)

@main.route('/filter_datasets')
def filter_datasets():
    tags = request.args.getlist('tag')  # Retrieve multiple 'tag' query parameters
    if tags:
        # Query datasets that have all the selected tags
        filtered_datasets = (
            Dataset.query
            .join(Dataset.tags)
            .join(Dataset.vendor)  # Join the Vendor table to get vendor info
            .filter(Tag.name.in_(tags))
            .group_by(Dataset.id)
            .having(db.func.count(Tag.id) == len(tags))  # Ensure all tags match
            .all()
        )
    else:
        # If no tags are selected, return all datasets
        filtered_datasets = Dataset.query.join(Dataset.vendor).all()

    # Serialize datasets for JSON response
    return jsonify([
        {
            'id': d.id,
            'name': d.name,
            'vendor': d.vendor.name,  # Access the vendor name through the 'vendor' relationship
            'status': d.dataset_status,  # Assuming dataset_status is the correct field name
            'tags': [t.name for t in d.tags]
        }
        for d in filtered_datasets
    ])