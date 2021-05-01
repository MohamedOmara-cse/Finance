import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():

    # Store the username of the user logged
    username = db.execute("SELECT username FROM users WHERE id = :uid", uid=int(session['user_id']))[0]["username"]

    # Cash available in bocket
    cash_available = db.execute("SELECT cash FROM users WHERE username = :username", username=username)[0]["cash"]

    # getting information from portfolio table into a list
    stocks = db.execute("SELECT symbol, shares FROM portfolio WHERE username = :username", username=username)

    # List to add all totals
    total_sum = []

    # Iterate over the stocks list to append the faulty information needed in index.html table
    for stock in stocks:
        symbol = str(stock["symbol"])
        shares = int(stock["shares"])
        stock_name = lookup(symbol)["name"]
        price = lookup(symbol)["price"]
        total = shares * price
        stock["name"] = stock_name
        stock["price"] = usd(price)
        stock["total"] = usd(total)
        total_sum.append(float(total))


  #Total Cash (shares_price and cash available)
    cash_total = sum(total_sum) + cash_available

  # Rendering the main page
    return render_template("index.html", stocks=stocks, cash_available=usd(cash_available), cash_total=usd(cash_total))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    # buying
    if request.method=="POST" :

    # getting symbol and shares from request
        symbol=request.form.get("symbol")
        num_shares = request.form.get("shares")
    # ensure income data
        if not symbol :
            return apology("Missing Symbol",code=400)

        elif not num_shares or int(num_shares)<1 or not num_shares.isdigit():
             return apology("Missind Shares",code=400)

        else:
            num_shares=int(num_shares)
    # getting information of symbol using lookup funcion (symbol)   ['name' ,'price' ,'symbol']
            lookup_response=lookup(request.form.get("symbol"))

    # ensure lookup response
            if lookup_response == None:
                return apology("invalid symbol", 400)


            price = float(lookup_response["price"])

            cash = db.execute("SELECT cash FROM users WHERE id=?",session["user_id"])[0]["cash"]
            full_price = price * num_shares
    # ensure having enough cash for buying
            if cash < full_price:
                return apology("You don't have enough money to pay", 403)

    #Updating portfolio incase having same stock symbol or Inserting new one

            else:
                username = db.execute("SELECT username FROM users WHERE id = :uid", uid=int(session['user_id']))[0]["username"]
                row=db.execute("SELECT symbol FROM portfolio WHERE username=?",username)
                found=0
                for value in row:


                    if lookup_response["symbol"]==value["symbol"]:
                        found=1
                        break
    # updating shares in portfolio table
                if found:



                    db.execute("UPDATE portfolio SET  shares=shares + :ushares WHERE username= :username   and symbol=:symbol "
                    ,ushares=num_shares,username=username,symbol=lookup_response["symbol"])

    # Inserting new row in portfolio table (username ,symbol ,shares )
                else:


                    db.execute("INSERT INTO portfolio (username, symbol, shares) VALUES (:username, :symbol, :shares)",
                    username=db.execute("SELECT username FROM users WHERE id = :uid", uid=int(session['user_id']))[0]["username"],
                                         symbol=lookup_response['symbol'], shares=request.form.get('shares'))


    # inserting new row in history table (username ,symbol ,price ,shares )
                db.execute("INSERT INTO history (username, operation, symbol, price, shares) VALUES (:username, 'BUY', :symbol, :price, :shares)",
                username=username, symbol=lookup_response['symbol'], price=lookup_response['price'], shares=request.form.get('shares'))
    # updating available Cash
                cost=cash-full_price
                db.execute("UPDATE users SET cash =? WHERE id = ?",cost,session['user_id'])
    # redirct user to home page (index.html)
                return redirect("/")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")




@app.route("/history")
@login_required
def history():

    # Getting data nedded for history
    username = db.execute("SELECT username FROM users WHERE id = :uid", uid=int(session['user_id']))[0]["username"]
    stocks = db.execute("SELECT operation, symbol, price, date, time, shares FROM history WHERE username = :username", username=username)

    for stock in stocks:
        symbol = str(stock["symbol"])
        name = lookup(symbol)["name"]
        stock["name"] = name
    # rendering history page
    return render_template("history.html", stocks=stocks)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

    # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

    # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

    # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

    # Ensure username exists and password is correct
        if len(rows) !=1 or not check_password_hash(rows[0]["hash"],request.form.get("password")):
            return apology("invalid username and/or password", 403)

    # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

    # Redirect user to home page

        return redirect("/")
        return render_template("sucsses.html",n=len(rows))
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

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Store the dictionary returned from the search
        look = lookup(request.form.get("symbol"))

        # If the symbol searched is invalid, return apology
        if look == None:
            return apology("invalid symbol", 400)

        # If the symbol exists, return the search
        else:
            return render_template("quoted.html", name=look["name"], symbol=look["symbol"], price=usd(look["price"]))
   # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

    # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

    # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

    # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

    # Ensure username exists and password is correct
        if len(rows) > 0 or not  request.form.get("password")==request.form.get("re_password"):
            return apology("invalid username and/or password", 403)
        use=request.form.get("username")
        pas=request.form.get("password")

        row = db.execute("INSERT INTO users (username ,hash)VALUES(?,?)",use,generate_password_hash(pas, method='pbkdf2:sha256', salt_length=8))

    # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("Register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():



    # Store the username
    username = db.execute("SELECT username FROM users WHERE id = :uid", uid=int(session['user_id']))[0]["username"]

    if request.method == "POST":
        # Store the symbol inputed
        look = lookup(request.form.get("symbol"))

        # Store shares inputed
        shares = request.form.get("shares")

        # Store the number of shares the user has
        user_shares = db.execute("SELECT shares FROM portfolio WHERE username = :username and symbol = :symbol GROUP BY symbol",
                        username=username, symbol=str(request.form.get("symbol")))[0]["shares"]

        # Store the value of sale
        value = look["price"] * int(shares)

        # If the symbol searched or number of shares is invalid, return apology
        if not request.form.get("symbol") or look == None:
            return apology("you must provide a stock", 400)
        elif not shares or not shares.isdigit() or int(shares) < 1 or int(shares) > int(user_shares):
            return apology("share number is invalid", 400)

        # If everything checks, proceed with sale
        else:
            # Add the value of sale to the user's cash
            db.execute("UPDATE users SET cash = cash + :value WHERE id = :uid", value=value, uid=int(session['user_id']))

            # Add the transaction to the user's history
            db.execute("INSERT INTO history (username, operation, symbol, price, shares) VALUES (:username, 'SELL', :symbol, :price, :shares)",
            username=username, symbol=look['symbol'], price=look['price'], shares=request.form.get('shares'))

            # If the user is selling all the shares, remove the stock from the user's portfolio
            if int(user_shares) == int(shares):
                db.execute("DELETE FROM portfolio WHERE username = :username and symbol = :symbol",
                            username=username, symbol=str(request.form.get("symbol")))

            # If the user is just selling some of the shares, update the portfolio
            elif int(user_shares) > int(shares):
                db.execute("UPDATE portfolio SET shares =shares - :shares WHERE username = :username and symbol = :symbol",
                            shares=shares, username=username, symbol=request.form.get("symbol"))

        # Send them to the portfolio
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Get the symbols from portfolio for the select list
        symbols = db.execute("SELECT symbol FROM portfolio WHERE username = :username ", username=username)

        return render_template("sell.html", symbols=symbols)



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
