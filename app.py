import os
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, g
import sqlite3
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect("finance.db")
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show portfolio of stocks"""
    if request.method == "POST":
        if not request.form.get("shares"):
            return apology("must provide # of share", 400)

        symbolData1 = lookup(request.form.get("symbol"))
        symbol1 = symbolData1["symbol"]
        price1 = symbolData1["price"]
        shares1 = int(request.form.get("shares"))
        total1 = price1 * shares1
        db = get_db()
        person1 = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchall()
        db.commit()
        if total1 <= person1[0]["cash"]:
            now1 = datetime.now()
            db = get_db()
            db.execute("INSERT INTO portfolio (id, symbol, shares, price, total, time) VALUES (?, ?, ?, ?, ?, ?)",
                       (person1[0]["id"], symbol1, shares1, price1, total1, now1))
            balance1 = person1[0]["cash"] - total1
            db.execute("UPDATE users SET cash = ? WHERE id = ?", (balance1, person1[0]["id"]))
            db.commit()
            flash("Bought!")
            return redirect("/")
        else:
            return apology("not enough money", 400)
    db = get_db()
    
    person = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchall()
    id = person[0]["id"]
    cash = person[0]["cash"]
    total = cash
    # portfolio = db.execute("SELECT * FROM portfolio WHERE id = ?", id)
    oldPortfolio = db.execute(
        "SELECT symbol, SUM(shares) as shares, SUM(price) as price, SUM(total) as total FROM portfolio WHERE id = ? GROUP BY symbol", (id,)).fetchall()
    db.commit()
    for i in oldPortfolio:
        i = dict(i)
        symbolData = lookup(i["symbol"])
        i["price"] = symbolData["price"]
        i["total"] = i["price"] * i["shares"]
        total += i["total"]

    portfolio = [i for i in oldPortfolio if i["shares"] != 0]

    return render_template("index.html", portfolio=portfolio, cash=cash, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide symbol", 400)
        if not request.form.get("shares"):
            return apology("must provide # of share", 400)

        symbolData = lookup(request.form.get("symbol"))
        if symbolData is not None:
            symbol = symbolData["symbol"]
            price = symbolData["price"]
            shares = int(request.form.get("shares"))
            total = price * shares
            db = get_db()
            person = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchall()
            db.commit()
            if total <= person[0]["cash"]:
                now = datetime.now()
                db = get_db()
                db.execute("INSERT INTO portfolio (id, symbol, shares, price, total, time) VALUES (?, ?, ?, ?, ?, ?)",
                           (person[0]["id"], symbol, shares, price, total, now))
                balance = person[0]["cash"] - total
                db.execute("UPDATE users SET cash = ? WHERE id = ?", (balance, person[0]["id"]))
                db.commit()
                flash("Bought!")
                return redirect("/")
            else:
                return apology("not enough money", 400)
        else:
            return apology("symbol not found", 400)

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    db = get_db()
    person = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchall()
    id = person[0]["id"]
    portfolio = db.execute("SELECT symbol, shares, price, time FROM portfolio WHERE id = ?", (id,)).fetchall()
    db.commit()
    return render_template("history.html", portfolio=portfolio)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        db = get_db()
        rows = db.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),)).fetchall()
        db.commit()




        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page

        return redirect("/")
        # return redirect("/index.html")
        # return render_template("index.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("invalid ticker", 400)
        symbolData = lookup(request.form.get("symbol"))
        if symbolData is not None:
            symbol = symbolData["symbol"]
            price = usd(symbolData["price"])
            return render_template("quoted.html", symbol=symbol, price=price)
        else:
            return apology("invalid symbol", 400)

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # try:
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)
        if not request.form.get("password"):
            return apology("must provide password", 400)
        if request.form.get("confirmation") != request.form.get("password"):
            return apology("password entered not the same", 400)
        db = get_db()
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", (request.form.get("username"),)
        )
        db.commit()
        # if len(rows) == 0:
        try:
            db = get_db()
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (request.form.get("username"),
                       generate_password_hash(request.form.get("password"))))
            db.commit()
            # db.execute("INSERT INTO users (hash) VALUES (?)", generate_password_hash(request.form.get("password")))
        except (ValueError):
            return apology("user name taken", 400)
        db = get_db()
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", (request.form.get("username"),)
        ).fetchall()
        db.commit()
        session["user_id"] = rows[0]["id"]
        flash("Registered")
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    db = get_db()
    person = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchall()
    id = person[0]["id"]

    oldPortfolio = db.execute(
        "SELECT symbol, SUM(shares) as shares, SUM(price) as price, SUM(total) as total FROM portfolio WHERE id = ? GROUP BY symbol", (id,)).fetchall()
    portfolio = [i for i in oldPortfolio if i["shares"] != 0]
    db.commit()
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Pick a symbo;", 400)
        if not request.form.get("shares"):
            return apology("Pick shares", 400)
        shares = int(request.form.get("shares"))
        symbol = request.form.get("symbol")

        for i in portfolio:
            if i["symbol"] == symbol:
                if i["shares"] >= shares:
                    symbolData = lookup(symbol)
                    price = symbolData["price"]
                    total = price * shares
                    now = datetime.now()
                    db = get_db()
                    db.execute("INSERT INTO portfolio (id, symbol, shares, price, total, time) VALUES (?, ?, ?, ?, ?, ?)",
                               (person[0]["id"], symbol, -shares, price, -total, now))
                    balance = person[0]["cash"] + total
                    db.execute("UPDATE users SET cash = ? WHERE id = ?", (balance, person[0]["id"]))
                    db.commit()
                    flash("Sold!")
                    return redirect("/")
                else:
                    return apology("too many shares", 4030)

    return render_template("sell.html", portfolio=portfolio)
