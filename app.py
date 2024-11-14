from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

app = Flask(__name__)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Income(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Expense(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Budget(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    period = db.Column(db.String(20), nullable=False, default='monthly')

# Create tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    users = User.query.all()
    return render_template('index.html', users=users)

@app.route('/dashboard/<user_id>')
def dashboard(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('dashboard.html', user=user)

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    new_user = User(username=data['username'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({
        'id': new_user.id,
        'username': new_user.username,
        'created_at': new_user.created_at.isoformat()
    }), 201

@app.route('/api/income', methods=['GET', 'POST', 'DELETE'])
def manage_income():
    if request.method == 'GET':
        user_id = request.args.get('user_id')
        income_entries = Income.query.filter_by(user_id=user_id).order_by(Income.date.desc()).all()
        return jsonify([{
            'id': income.id,
            'amount': income.amount,
            'source': income.source,
            'date': income.date.isoformat()
        } for income in income_entries])
    
    elif request.method == 'POST':
        data = request.form
        new_income = Income(
            user_id=data['user_id'],
            amount=float(data['amount']),
            source=data['source'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date()
        )
        db.session.add(new_income)
        db.session.commit()
        return redirect(url_for('dashboard', user_id=data['user_id']))
    
    elif request.method == 'DELETE':
        income_id = request.args.get('income_id')
        Income.query.filter_by(id=income_id).delete()
        db.session.commit()
        return '', 204

@app.route('/api/expenses', methods=['GET', 'POST', 'DELETE'])
def manage_expenses():
    if request.method == 'GET':
        user_id = request.args.get('user_id')
        expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc()).all()
        return jsonify([{
            'id': expense.id,
            'amount': expense.amount,
            'category': expense.category,
            'date': expense.date.isoformat()
        } for expense in expenses])
    
    elif request.method == 'POST':
        data = request.form
        new_expense = Expense(
            user_id=data['user_id'],
            amount=float(data['amount']),
            category=data['category'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date()
        )
        db.session.add(new_expense)
        db.session.commit()
        return redirect(url_for('dashboard', user_id=data['user_id']))
    
    elif request.method == 'DELETE':
        expense_id = request.args.get('expense_id')
        Expense.query.filter_by(id=expense_id).delete()
        db.session.commit()
        return '', 204

@app.route('/api/analysis/summary/<user_id>')
def get_summary(user_id):
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    start_date = datetime.now().replace(day=1).date()
    
    income_total = db.session.query(db.func.sum(Income.amount))\
        .filter(Income.user_id == user_id)\
        .filter(Income.date >= start_date)\
        .scalar() or 0
    
    expense_total = db.session.query(db.func.sum(Expense.amount))\
        .filter(Expense.user_id == user_id)\
        .filter(Expense.date >= start_date)\
        .scalar() or 0
    
    expenses_by_category = db.session.query(
        Expense.category,
        db.func.sum(Expense.amount).label('total')
    ).filter(
        Expense.user_id == user_id,
        Expense.date >= start_date
    ).group_by(Expense.category).all()
    
    return jsonify({
        'income_total': income_total,
        'expense_total': expense_total,
        'net_savings': income_total - expense_total,
        'expenses_by_category': [
            {'category': cat, 'amount': total}
            for cat, total in expenses_by_category
        ]
    })

# Templates
@app.template_filter('currency')
def currency_filter(value):
    return f"${value:,.2f}"

if __name__ == '__main__':
    app.run(debug=True)