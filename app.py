from flask import Flask, render_template, url_for, redirect, request, session, flash, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date
from apscheduler.schedulers.background import BackgroundScheduler
from flask_socketio import SocketIO, join_room
from datetime import datetime, timedelta
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

app.secret_key = "w8RbFq4xGzL0I3o2e9sP"

app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://root:@localhost/rbr"

scheduler = BackgroundScheduler()
scheduler.start()

db = SQLAlchemy(app)
class Accounts(db.Model):
    acc_no = db.Column(db.String(6), primary_key=True)
    acc_holder = db.Column(db.String(50), nullable=False)
    acc_email = db.Column(db.String(55), nullable=False)
    acc_holder_dob = db.Column(Date, nullable=True)
    acc_pin = db.Column(db.String(4), nullable=False)
    acc_principal = db.Column(db.Integer, nullable=False)

class FrozenAccounts(db.Model):
    acc_no = db.Column(db.String(6), primary_key=True)
    acc_holder = db.Column(db.String(50), nullable=False)
    acc_email = db.Column(db.String(55), nullable=False)
    acc_holder_dob = db.Column(Date, nullable=True)
    acc_pin = db.Column(db.String(4), nullable=False)
    acc_principal = db.Column(db.Integer, nullable=False)

class Transactions(db.Model):
    transaction_id = db.Column(db.Integer, primary_key=True, autoincrement=True) # Auto Increment 
    sender_accno = db.Column(db.String(6), nullable=False)
    sender_name = db.Column(db.String(50), nullable=False)
    reciever_accno = db.Column(db.String(6), nullable=False)
    reciever_name = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "transaction_id": self.transaction_id,
            "sender_accno": self.sender_accno,
            "sender_name": self.sender_name,
            "reciever_accno": self.reciever_accno,
            "reciever_name": self.reciever_name,
            "amount": self.amount
        }
    
class Admins(db.Model):
    sno = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)

class Loans(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    acc_no = db.Column(db.String, nullable=False)
    acc_holder = db.Column(db.String, nullable=False)
    principal = db.Column(db.Integer, nullable=False)
    time = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False)


@app.route('/')
def index():
    session.clear()
    if 'acc_no' not in session:
        return render_template("index.html")
    elif 'acc_no' in session:
        return render_template(f"dashboard.html?acc_no={session['acc_no']}")

# Routes for the user
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        acc_no = request.form['acc_no']
        n = request.form['acc_pin']
        def DecimalToBinary(num):
             return bin(num).replace("0b", "") 
        acc_pin = str(DecimalToBinary(int(n)))
        sql = Accounts.query.filter_by(acc_no=acc_no, acc_pin=acc_pin).count()
        if sql > 0: 
            session['acc_no'] = acc_no
            sql_get = Accounts.query.filter_by(acc_no=acc_no, acc_pin=acc_pin).first()
            session['acc_holder'] = sql_get.acc_holder
            session['acc_email'] = sql_get.acc_email
            session['acc_principal'] = sql_get.acc_principal
            if "acc_holder_dob" in session:
                session['acc_holder_dob'] = sql_get.acc_holder_dob.strftime("%D")
            session['acc_pin'] = sql_get.acc_pin
            
            return redirect(url_for('dashboard', acc_no=acc_no))
        else:
            flash("Username or Password is incorrect!")
            return render_template('login.html')
    else:
        return render_template('login.html')

@app.route('/dashboard/<acc_no>')
def dashboard(acc_no):
    if len(session.items())>0:
        if session['acc_no']==acc_no:
            return render_template('dashboard.html', acc_no=acc_no, acc_holder=session.get('acc_holder'))
    return redirect(url_for("notLogged"))

@app.route("/notLogged")
def notLogged():
    session.clear()
    return render_template('notLogged.html')

@app.route('/profile/<acc_no>')
def profile(acc_no):
    if len(session.items())>0:
        if session['acc_no']==acc_no:
            account = Accounts.query.filter_by(acc_no=acc_no).first()
            return render_template('profile.html', acc_no=acc_no, acc_holder=account.acc_holder, acc_email=account.acc_email, acc_holder_dob=account.acc_holder_dob, acc_principal=account.acc_principal)
    return redirect(url_for("notLogged"))


@app.route("/change_pin/<acc_no>", methods=['POST', 'GET'])
def changePin(acc_no):
    if len(session.items())>0:
        if session['acc_no']==acc_no:
            if request.method=="POST":
                n = request.form.get('acc_oldpin')
                def DecimalToBinary(num):
                    return bin(num).replace("0b", "") 
                old_pin = DecimalToBinary(int(n))
                n = request.form.get('acc_newpin')
                new_pin = DecimalToBinary(int(n))
                sql = Accounts.query.filter_by(acc_no=acc_no, acc_pin=old_pin).first()
                if sql:
                    session['acc_pin'] = new_pin
                    sql.acc_pin = new_pin
                    db.session.commit()
                    return redirect(url_for('dashboard', acc_no=acc_no))
                else:
                    return redirect(url_for('dashboard', acc_no=acc_no))
            else:
                return render_template('changePin.html', acc_no=acc_no)
    return redirect(url_for("notLogged"))

@app.route("/pay/<acc_no>", methods=['POST', 'GET'])
def pay(acc_no):
    if len(session.items())>0:
        if session['acc_no']==acc_no:
            if request.method == "POST":
                acc_no1 = request.form.get('acc_no1')
                acc_holder1 = request.form.get('acc_holder')
                amount = int(request.form.get('amount'))
                def pay(sql, _sql, amount):
                    if sql and _sql:
                        if _sql.acc_principal > amount and sql.acc_no!=_sql.acc_no:
                            sql.acc_principal += amount
                            _sql.acc_principal -= amount
                            session['acc_principal'] -= amount
                            db.session.commit()
                            return 1
                    return -1
                sql = Accounts.query.filter_by(acc_no=acc_no1, acc_holder=acc_holder1).first()  # Reciever
                if sql:
                    _sql = Accounts.query.filter_by(acc_no=acc_no, acc_pin=session['acc_pin']).first() # Sender
                    if _sql:
                        result = pay(sql=sql, _sql=_sql, amount=amount)
                        if (result == 1):
                            # Saving Transaction in the database
                            new_transaction = Transactions(sender_accno=_sql.acc_no, sender_name=_sql.acc_holder, reciever_accno=sql.acc_no, reciever_name=sql.acc_holder, amount=amount)
                            db.session.add(new_transaction)
                            db.session.commit()
                            return redirect(url_for('transaction_status', acc_no=acc_no, status="Successful"))
                        elif result == -1:
                            return redirect(url_for('transaction_status', acc_no=acc_no, status="Failed"))

                return redirect(url_for('transaction_status', acc_no=acc_no, status="Failed!"))
                    
            return render_template('pay.html', acc_no=acc_no)
    return redirect(url_for("notLogged"))

@app.route("/transaction_status/<acc_no>/<status>")
def transaction_status(acc_no, status):
    return render_template('transaction_status.html', acc_no=acc_no, status=status)

@app.route("/transaction_history/<acc_no>")
def transaction_history(acc_no):
    if len(session.items())>0:
        if session['acc_no']==acc_no:
            sql = Transactions.query.all()
            if "data" in session:
                session.pop("data")
            if sql:
                isOur = False
                for transaction in sql:
                    if transaction.reciever_accno==acc_no or transaction.sender_accno==acc_no:
                        isOur = True
                if isOur==True:
                    data = [transaction.to_dict() for transaction in sql]
                    session["data"] = data
            return render_template('transaction_history.html', acc_no=acc_no)
    return redirect(url_for("notLogged"))

@app.route("/logout/<acc_no>")
def logout(acc_no):
    if len(session.items())>0:
        if session['acc_no']==acc_no:
            session.clear()
            return render_template('index.html')
    return redirect(url_for("notLogged"))

@app.route("/pay_loan/<acc_no>", methods=["GET", "POST"])
def payLoan(acc_no):
    if len(session.items())>0:
        if session['acc_no']==acc_no:
            if request.method=="POST":
                pending = Loans.query.filter_by(acc_no=acc_no).all()
                account = Accounts.query.filter_by(acc_no=acc_no).first()
                if pending and account:
                    for loan in pending:
                        if account.acc_principal>=loan.amount:
                            account.acc_principal-=loan.amount
                            db.session.delete(loan)
                            db.session.commit()
                            flash("Loan paid!")
                            return redirect(url_for('dashboard', acc_no=acc_no))
                        flash(f"Insufficient Balance {loan.amount} and {account.acc_principal}")
                flash("No pending dues!")
    return render_template("payLoan.html", acc_no=acc_no)

# Routes for RBI admin
def send_alert(acc_no, amount):
    socketio.emit('notification', {'message': f"Your loan for {amount} is overdue!"}, room=acc_no)

def check_loans():
    with app.app_context():
        loans = Loans.query.filter(Loans.time<=datetime.now()).all()
        for loan in loans:
            send_alert(loan.acc_no, loan.amount)

def shubh_salary():
    with app.app_context():
        shubh = Accounts.query.filter_by(acc_no="111000").first()
        shubh.acc_principal += 1000
        db.session.commit()

shubhSalary = scheduler.add_job(shubh_salary, 'interval', minutes=40)
checkLoans = scheduler.add_job(check_loans, 'interval', minutes=1)


@app.route("/admin/adminLogin", methods=["GET", "POST"])
def adminLogin():
    if "admin" in session:
        session.pop("admin")
    if request.method=="POST":
        username = request.form.get("username")
        password = request.form.get("password")
        admins = Admins.query.all()
        for admin in admins:
            if admin.username==username and admin.password==password:
                session["admin"] = username
                return redirect(url_for('admin'))
        flash("Username or Password is incorrect!")
        return redirect(url_for('adminLogin'))

    return render_template("/admin/login.html")

@app.route("/admin/admin")
def admin():
    if "admin" in session:
        if session["admin"] in [admin.username for admin in Admins.query.all()]:
            return render_template("/admin/admin.html")
    return redirect(url_for("adminLogin"))

@app.route("/admin/create_account", methods=['POST', 'GET'])
def create_account():
    if "admin" in session:
        if session["admin"] in [admin.username for admin in Admins.query.all()]:
            if request.method=="POST":
                acc_no = request.form.get('acc_no')
                acc_holder = request.form.get('acc_holder')
                acc_email = request.form.get('acc_email')
                acc_holder_dob = request.form.get('acc_holder_dob')
                acc_pin_ = request.form.get('acc_pin')
                acc_principal = request.form.get('acc_principal')
                def DecimalToBinary(num):
                     return bin(num).replace("0b", "") 
                new_account = Accounts(acc_no=acc_no, acc_holder=acc_holder, acc_email=acc_email, acc_holder_dob=acc_holder_dob, acc_pin=DecimalToBinary(int(acc_pin_)), acc_principal=acc_principal)
                db.session.add(new_account)
                db.session.commit()
                return redirect(url_for("admin"))

            return render_template("/admin/create_account.html")
    return redirect(url_for("adminLogin"))

@app.route("/admin/freeze_account", methods=['POST', 'GET'])
def freeze_account():
    if "admin" in session:
        if session["admin"] in [admin.username for admin in Admins.query.all()]:
            if request.method=="POST":
                acc_no = request.form.get('acc_no')
                sql = Accounts.query.filter_by(acc_no=acc_no).first()
                if sql:
                    _sql = FrozenAccounts(acc_no=sql.acc_no, acc_holder=sql.acc_holder, acc_email=sql.acc_email, acc_holder_dob=sql.acc_holder_dob, acc_pin=sql.acc_pin, acc_principal=sql.acc_principal)
                    db.session.add(_sql)
                    db.session.delete(sql)
                    db.session.commit()
                    return redirect(url_for('admin'))
            return render_template("/admin/freeze_account.html")
    return redirect(url_for("adminLogin"))


@app.route("/admin/release_account", methods=['POST', 'GET'])
def release_account():
    if "admin" in session:
        if session["admin"] in [admin.username for admin in Admins.query.all()]:
            if request.method=="POST":
                acc_no = request.form.get('acc_no')
                sql = FrozenAccounts.query.filter_by(acc_no=acc_no).first()
                if sql:
                    _sql = Accounts(acc_no=sql.acc_no, acc_holder=sql.acc_holder, acc_email=sql.acc_email, acc_holder_dob=sql.acc_holder_dob, acc_pin=sql.acc_pin, acc_principal=sql.acc_principal)
                    db.session.add(_sql)
                    db.session.delete(sql)
                    db.session.commit()
                    return redirect(url_for('admin'))
            return render_template("/admin/release_account.html")
    return redirect(url_for("adminLogin"))

@app.route("/admin/tax", methods=['POST', 'GET'])
def tax():
    if "admin" in session:
        if session["admin"] in [admin.username for admin in Admins.query.all()]:
            if request.method=="POST":
                acc_no = request.form.get('acc_no')
                tax_percent = int(request.form.get('tax'))
                sql = Accounts.query.filter_by(acc_no=acc_no).first()
                if sql:
                    sql.acc_principal -= (tax_percent/100)*sql.acc_principal
                    db.session.commit()
                    return redirect(url_for('admin'))
            return render_template('/admin/tax.html')
    return redirect(url_for("adminLogin"))

@app.route("/admin/loan", methods=["GET", "POST"])
def loan():
    if "admin" in session:
        if session["admin"] in [admin.username for admin in Admins.query.all()]:
            if request.method=="POST":
                acc_no = request.form.get("acc_no")
                principal = int(request.form.get("principal"))
                time = int(request.form.get("time"))
                current = datetime.now()
                due = current + timedelta(minutes=time)
                rate = 4
                # amount = int(principal*((1+rate/100)**time)) For compound interest
                amount = int(((principal*rate*time)/100)+principal)
                if principal>1000000 or principal<1000:
                    flash("Principal must lie in the range 1000-1000000")
                    return redirect(url_for('loan'))
                account = Accounts.query.filter_by(acc_no=acc_no).first()
                if account:
                    acc_holder = account.acc_holder
                    entry = Loans(acc_no=acc_no, acc_holder=acc_holder, principal=principal, time=due, amount=amount)
                    account.acc_principal+=principal
                    db.session.add(entry)
                    db.session.commit()
                    return redirect(url_for('admin'))
                    
                
                return render_template('/admin/admin.html', loan=False)

            return render_template("/admin/loan.html")
    return redirect(url_for("adminLogin"))

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html")

@socketio.on('connect')
def handle_connect():
    acc_no = request.args.get('acc_no')
    room = acc_no
    join_room(room)
    print(f"Client {request.sid} connected room {room}")

@socketio.on('disconnect')
def handle_disconnect():
    # Handle client disconnection
    print('Client disconnected:', request.sid)


if __name__=='__main__':
    socketio.run(app, debug=True, host="0.0.0.0")
