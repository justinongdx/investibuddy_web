from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from models.database_manager import DatabaseManager, create_database
from models.user_manager import UserManager
from models.portfolio_manager import PortfolioManager
from io import BytesIO
from models.entities import Portfolio
from dotenv import load_dotenv
from models.portfolio_manager import calculate_portfolio_summary
import os

load_dotenv()

import pandas as pd
import datetime

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
        email = request.form['email']
        password = request.form['password']
        risk_tolerance = request.form['risk_tolerance']

        success, message, verification_code = user_manager.register_user(username, email, password, risk_tolerance)

        if success:
            # Store email in session for verification page
            session['registration_email'] = email
            flash(message)
            return redirect(url_for('verify'))
        else:
            flash(f'❌ {message}')

    return render_template('register.html')


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if 'registration_email' not in session:
        flash('⚠️ Please register first.')
        return redirect(url_for('register'))

    if request.method == 'POST':
        verification_code = request.form['verification_code']
        email = session['registration_email']

        if user_manager.verify_user(email, verification_code):
            # Clear registration email from session
            session.pop('registration_email', None)
            flash('✅ Verification successful! Please log in.')
            return redirect(url_for('login'))
        else:
            flash('❌ Invalid verification code.')

    return render_template('verify.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        result = user_manager.login_user(email, password)

        if result:
            user_id, username = result
            session['user_id'] = user_id
            session['username'] = username
            flash(f'😊 Welcome back, {username}!')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Invalid email or password, or account not verified.')

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

        # Date cannot be a future date
        try:
            txn_date_obj = datetime.datetime.strptime(txn_date, '%Y-%m-%d').date()
            if txn_date_obj > datetime.date.today():
                flash("❌ Transaction date cannot be in the future.")
                return redirect(url_for('add_transaction', portfolio_id=portfolio_id, symbol_id=symbol_id))
        except ValueError:
            flash("❌ Invalid date format. Please use YYYY-MM-DD.")
            return redirect(url_for('add_transaction', portfolio_id=portfolio_id, symbol_id=symbol_id))

        # Prevent selling more shares than currently owned
        total_bought = sum(txn.shares for txn in symbol.transactions if txn.transaction_type.lower() == 'buy')
        total_sold = sum(txn.shares for txn in symbol.transactions if txn.transaction_type.lower() == 'sell')
        current_shares = total_bought - total_sold

        if txn_type.lower() == 'sell' and shares > current_shares:
            flash(f"❌ Cannot sell {shares} shares. You only own {current_shares} shares.")
            return redirect(url_for('add_transaction', portfolio_id=portfolio_id, symbol_id=symbol_id))

        # Proceed to save transaction
        portfolio_manager.add_transaction(symbol_id, txn_type, shares, price, cost, txn_date)
        flash(f"{txn_type} transaction for {shares} shares of {symbol.ticker} added!")
        return redirect(url_for('portfolio_detail', portfolio_id=portfolio_id))

    return render_template('add_transaction.html', symbol=symbol, portfolio_id=portfolio_id)

@app.route('/portfolio/<int:portfolio_id>/sector-exposure')
def sector_exposure(portfolio_id):
    if 'user_id' not in session:
        flash("⚠️ Please log in to view sector exposure.")
        return redirect(url_for('login'))

    rows = db_manager.execute_query(
        "SELECT portfolio_id FROM portfolios WHERE portfolio_id = ? AND user_id = ?",
        (portfolio_id, session['user_id'])
    )

    if not rows:
        flash("❌ Portfolio not found or does not belong to you.")
        return redirect(url_for('view_portfolios'))

    portfolio = {
        'portfolio_id': portfolio_id,
        'name': rows[0][0]
    }

    exposure = portfolio_manager.calculate_sector_exposure(portfolio_id)
    return render_template('sector_exposure.html', portfolio=portfolio, portfolio_id=portfolio_id, sector_exposure=exposure)


@app.route('/portfolio/<int:portfolio_id>/export')
def export_portfolio_excel(portfolio_id):
    symbols = portfolio_manager.get_portfolio_symbols(portfolio_id)

    data = []
    for s in symbols:
        metrics = portfolio_manager.calculate_symbol_metrics(s)
        data.append({
            "Ticker": metrics["ticker"],
            "Sector": metrics["sector"],
            "Current Price": metrics["current_price"],
            "Avg Cost": metrics["avg_cost"],
            "Shares": metrics["current_shares"],
            "Investment": metrics["total_investment"],
            "Current Value": metrics["current_value"],
            "Unrealised P/L": metrics["unrealised_pl"],
            "Unrealised P/L %": metrics["unrealised_pl_percent"],
            "Day Change": metrics["day_change"],
            "Day Change %": metrics["day_change_percent"]
        })

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Portfolio')

    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name=f'portfolio_{portfolio_id}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
from flask import render_template, redirect, url_for
from utils.gemini import format_portfolio_for_gemini, get_gemini_recommendation

@app.route('/portfolio/<int:portfolio_id>/recommendations')
def recommendations(portfolio_id):
    portfolio = portfolio_manager.get_portfolio_by_id(portfolio_id)
    symbols = portfolio_manager.get_portfolio_symbols(portfolio_id)

    # Calculate updated metrics BEFORE rendering template
    symbol_metrics = [portfolio_manager.calculate_symbol_metrics(s) for s in symbols]

    # Use the calculated data for Gemini + frontend
    formatted = format_portfolio_for_gemini(symbol_metrics)
    gemini_response = get_gemini_recommendation(formatted)

    # This ensures your data table doesn't go blank!
    for i, sym in enumerate(symbols):
        sym.current_data = {
            "last_price": symbol_metrics[i]["current_price"]
        }
        sym.current_shares = symbol_metrics[i]["current_shares"]
        sym.current_value = symbol_metrics[i]["current_value"]

    return render_template(
        "portfolio_detail.html",
        portfolio=portfolio,
        symbols=symbols,
        portfolio_summary=calculate_portfolio_summary(symbols),
        recommendation=gemini_response
    )


if __name__ == '__main__':
    app.run(debug=True)
