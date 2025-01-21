# your_project/models.py
from project import db

class Vendor(db.Model):
    __tablename__ = 'vendor'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    introduction = db.Column(db.Text, nullable=True)  # Ensure this line is present
    datasets = db.relationship('Dataset', backref='vendor', lazy =True)

    @classmethod
    def get_all_vendors(cls):
        return cls.query.all()

dataset_tags = db.Table(
    'dataset_tags',
    db.Column('dataset_id', db.Integer, db.ForeignKey('dataset.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class Dataset(db.Model):
    __tablename__ = 'dataset'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    dataset_status = db.Column(db.String(10), nullable=True)
    introduction = db.Column(db.String(500), nullable=True)
    user_group = db.Column(db.String(20),db.ForeignKey('UserGroup.group_name'), nullable=True)

    tags = db.relationship('Tag', secondary=dataset_tags, backref=db.backref('datasets', lazy='dynamic'))

class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    definition = db.Column(db.String(255), nullable=True)

class ProjectCode(db.Model):
    __tablename__ = 'ProjectCode'
    code = db.Column(db.String(5), nullable=False, primary_key=True)
    definition = db.Column(db.String(50), nullable=True)

class UserGroup(db.Model):
    __tablename__ = 'UserGroup'
    group_name = db.Column(db.String(20), nullable=False, primary_key=True)
    definition = db.Column(db.String(50), nullable=True)

class Invoice(db.Model):
    __tablename__ = 'invoice'
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'), nullable=False)
    filename = db.Column(db.String(120), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False)
    invoice_period_start_date = db.Column(db.Date, nullable=False)
    invoice_period_end_date = db.Column(db.Date, nullable=False)
    frequency = db.Column(db.DECIMAL(12,6), nullable=False)
    frequency_unit = db.Column(db.String(5), nullable=False)
    currency = db.Column(db.String(5), nullable=False)
    amount = db.Column(db.DECIMAL(12,6), nullable=False)
    filepath = db.Column(db.String(200), nullable=False)  # Path to store file location
    budgeted_invoice_id = db.Column(db.Integer, db.ForeignKey('budgetedInvoice.id'), nullable=True)
    project_code = db.Column(db.String(5), db.ForeignKey('ProjectCode.code'), nullable=True)

class Contract(db.Model):
    __tablename__ = 'Contract'
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'), nullable=False)
    filename = db.Column(db.String(120), nullable=False)
    contract_signing_date = db.Column(db.Date, nullable=False)
    contract_commence_date = db.Column(db.Date, nullable=False)
    renewal_frequency = db.Column(db.DECIMAL(4,2), nullable=False) # CHANGE THIS TO INTEGER
    renewal_frequency_unit = db.Column(db.String(1), nullable=False)
    renewal_notice_day_count = db.Column(db.Integer, nullable=False)
    renewal_notice_day_type = db.Column(db.String(3), nullable=False) # REMOVE THIS
    is_active = db.Column(db.Boolean, nullable=False, default = False)
    filepath = db.Column(db.String(200), nullable=False)  # Path to store file location

class Documentation(db.Model):
    __tablename__ = 'Documentation'
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'), nullable=False)
    filetype = db.Column(db.String(20), nullable=True)
    filename = db.Column(db.String(120), nullable=True)
    filepath = db.Column(db.String(200), nullable=True) 
    filelink = db.Column(db.String(120), nullable=True)
    comments = db.Column(db.String(500), nullable=True)

class Event(db.Model):
    __tablename__ = 'Event'
    id = db.Column(db.Integer, primary_key=True)
    event_date = db.Column(db.Date, nullable=False)
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'), nullable=False)
    filename = db.Column(db.String(120), nullable=True)
    filepath = db.Column(db.String(200), nullable=True)
    eventlink = db.Column(db.String(120), nullable=True)
    comments = db.Column(db.String(500), nullable=True)

class VendorContact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True) 
    tel = db.Column(db.String(20), nullable=True) 
    position = db.Column (db.String(20), nullable = False)
    comments = db.Column(db.String(500), nullable=True) 

class Budget(db.Model):
    __tablename__ = 'budget'
    year = db.Column(db.Integer, nullable=False, unique=True, primary_key=True)
    status = db.Column(db.Text, nullable=False)

class BudgetedInvoice(db.Model):
    __tablename__ = 'budgetedInvoice'
    id = db.Column(db.Integer, primary_key=True)
    budgeted_year = db.Column(db.Integer, db.ForeignKey('budget.year'), nullable=False)

    budgeted_vendor = db.Column(db.String(100), nullable=False)
    budgeted_dataset = db.Column(db.String(100), nullable=False)

    last_invoice_frequency = db.Column(db.DECIMAL(12,6), nullable=True)
    last_invoice_frequency_unit = db.Column(db.String(5), nullable=True)
    last_invoice_currency = db.Column(db.String(5), nullable=True)
    last_invoice_amount = db.Column(db.DECIMAL(12,6), nullable=True)

    budgeted_invoice_frequency = db.Column(db.DECIMAL(12,6), nullable=True)
    budgeted_invoice_frequency_unit = db.Column(db.String(5), nullable=True)
    budgeted_invoice_currency = db.Column(db.String(5), nullable=True)
    budgeted_invoice_amount = db.Column(db.DECIMAL(12,6), nullable=True) 

class CurrencyRateAgainstUSD(db.Model):
    __tablename__ = 'CurrencyRateAgainstUSD'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.DECIMAL(6,3), nullable=True) 
    currency = db.Column(db.String(5), nullable=False)
