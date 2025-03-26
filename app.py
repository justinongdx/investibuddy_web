from flask import Flask, render_template, request, redirect, url_for, session, flash
from models.database_manager import DatabaseManager, create_database
from models.user_manager import UserManager
from models.portfolio_manager import PortfolioManager

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Initialise database and managers
create_database()
db_manager = DatabaseManager()
user_manager = UserManager(db_manager)
portfolio_manager = PortfolioManager(db_manager)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        risk_tolerance = request.form['risk_tolerance']

        if user_manager.register_user(username, password, risk_tolerance):
            flash('✅ Registration successful! Please log in.')
            return redirect(url_for('login'))
        else:
            flash('❌ Username already exists.')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_id = user_manager.login_user(username, password)

        if user_id:
            session['user_id'] = user_id
            session['username'] = username
            flash(f'😊 Welcome back, {username}!')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Invalid username or password.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('👋 You have been logged out.')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('⚠️ Please log in to continue.')
        return redirect(url_for('login'))

    return render_template('dashboard.html', username=session['username'])

@app.route('/create-portfolio', methods=['GET', 'POST'])
def create_portfolio():
    if 'user_id' not in session:
        flash("⚠️ Please log in to create a portfolio.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        portfolio_manager.create_portfolio(session['user_id'], name)
        flash(f"✅ Portfolio '{name}' created successfully!")
        return redirect(url_for('dashboard'))

    return render_template('create_portfolio.html')

@app.route('/view-portfolios')
def view_portfolios():
    if 'user_id' not in session:
        flash("⚠️ Please log in to view your portfolios.")
        return redirect(url_for('login'))

    portfolios = portfolio_manager.get_user_portfolios(session['user_id'])
    return render_template('view_portfolios.html', portfolios=portfolios)

@app.route('/portfolio/<int:portfolio_id>/add-symbol', methods=['GET', 'POST'])
def add_symbol(portfolio_id):
    if 'user_id' not in session:
        flash("⚠️ Please log in to add symbols.")
        return redirect(url_for('login'))

    rows = db_manager.execute_query(
        "SELECT portfolio_id, user_id, name FROM portfolios WHERE portfolio_id = ? AND user_id = ?",
        (portfolio_id, session['user_id'])
    )

    if not rows:
        flash("❌ Portfolio not found or does not belong to you.")
        return redirect(url_for('view_portfolios'))

    portfolio = {
        'portfolio_id': rows[0][0],
        'user_id': rows[0][1],
        'name': rows[0][2]
    }

    if request.method == 'POST':
        ticker = request.form['ticker'].upper().strip()
        data = portfolio_manager.yf.fetch_data(ticker)

        if "error" in data:
            flash(data["error"])
        else:
            sector = data.get("sector", "Unknown")
            result = portfolio_manager.add_symbol(portfolio_id, ticker, sector)
            if result:
                flash(f"✅ Symbol '{ticker}' added to portfolio!")
                return redirect(url_for('portfolio_detail', portfolio_id=portfolio_id))
            else:
                flash(f"⚠️ Symbol '{ticker}' already exists in this portfolio.")

    return render_template('add_symbol.html', portfolio=portfolio)

@app.route('/portfolio/<int:portfolio_id>')
def portfolio_detail(portfolio_id):
    if 'user_id' not in session:
        flash("⚠️ Please log in to view a portfolio.")
        return redirect(url_for('login'))

    rows = db_manager.execute_query(
        "SELECT portfolio_id, user_id, name FROM portfolios WHERE portfolio_id = ? AND user_id = ?",
        (portfolio_id, session['user_id'])
    )

    if not rows:
        flash("❌ Portfolio not found or does not belong to you.")
        return redirect(url_for('view_portfolios'))

    portfolio = {
        'portfolio_id': rows[0][0],
        'user_id': rows[0][1],
        'name': rows[0][2]
    }

    symbols = portfolio_manager.get_portfolio_symbols(portfolio_id)

    total_market_value = 0
    total_cost_all = 0

    for s in symbols:
        total_shares = 0
        total_cost = 0
        transactions = s.transactions if hasattr(s, 'transactions') and s.transactions else []

        for txn in transactions:
            try:
                shares = float(txn.shares)
                price = float(txn.price)
                if txn.transaction_type == 'Buy':
                    total_shares += shares
                    total_cost += shares * price
                elif txn.transaction_type == 'Sell':
                    total_shares -= shares
            except ValueError:
                flash(f"❌ Invalid transaction: shares='{txn.shares}', price='{txn.price}' for symbol {s.ticker}")
                continue

        last_price = s.current_data.get('last_price', 0) if s.current_data else 0
        s.current_shares = total_shares
        s.current_value = round(total_shares * last_price, 2) if total_shares > 0 else 0

        total_market_value += s.current_value
        total_cost_all += total_cost

    portfolio_summary = {
        'market_value': round(total_market_value, 2),
        'total_cost': round(total_cost_all, 2),
        'pnl': round(total_market_value - total_cost_all, 2)
    }

    return render_template('portfolio_detail.html', portfolio=portfolio, symbols=symbols, portfolio_summary=portfolio_summary)

@app.route('/portfolio/<int:portfolio_id>/symbol/<int:symbol_id>/add-transaction', methods=['GET', 'POST'])
def add_transaction(portfolio_id, symbol_id):
    if 'user_id' not in session:
        flash("⚠️ Please log in to add transactions.")
        return redirect(url_for('login'))

    symbol = portfolio_manager.get_symbol_by_id(symbol_id)

    if not symbol or symbol.portfolio_id != portfolio_id:
        flash("❌ Symbol not found or does not belong to this portfolio.")
        return redirect(url_for('portfolio_detail', portfolio_id=portfolio_id))

    if request.method == 'POST':
        txn_type = request.form['transaction_type']
        txn_date = request.form['transaction_date']
        shares = float(request.form['shares'])
        price_str = request.form['price'].strip()
        price = float(price_str) if price_str else symbol.current_data['last_price']
        cost = float(request.form['transaction_cost'])

        portfolio_manager.add_transaction(symbol_id, txn_type, shares, price, cost, txn_date)
        flash(f"{txn_type} transaction for {shares} shares of {symbol.ticker} added!")
        return redirect(url_for('portfolio_detail', portfolio_id=portfolio_id))

    return render_template('add_transaction.html', symbol=symbol, portfolio_id=portfolio_id)


if __name__ == '__main__':
    app.run(debug=True)

