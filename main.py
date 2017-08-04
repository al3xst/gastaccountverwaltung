from flask import Flask, json, render_template, request
from datetime import date, datetime, timedelta
from base64 import b64encode, b64decode
from email.mime.text import MIMEText
from Crypto.Cipher import AES
import sqlalchemy
import smtplib
import random
import string
import html
import sys
import os

# TODO create an account class - results in an sqlalchemy improvement

if "DEBUG" in os.environ:
    DEBUG=True
else:
    DEBUG=False


# receives environment variables
def get_env_variable(varname, *, default=None, defaulttext=None, check_debug=True):
    try:
        value = os.environ[varname]
    except KeyError:
        if default == None or (check_debug and not DEBUG):
            print("ENV Variable '{}' not set. Exiting program.".format(varname))
            sys.exit(1)
        else:
            if defaulttext: print("   "+defaulttext)
            value = default
    if DEBUG: print("{:20} {}".format(varname+":", value))
    return value


# Returns a connection and a metadata object
def sql_connect():
    # The return value of create_engine() is our connection object
    con = sqlalchemy.create_engine(sql_url, client_encoding='utf8')
    # We then bind the connection to MetaData()
    meta = sqlalchemy.MetaData(bind=con, reflect=True)
    return con, meta


def generate_password(_pwlen = 8):
    chars = string.ascii_letters[:] + "".join([str(x) for x in range(10)])

    result = ""
    for _ in range(_pwlen):
        result += random.choice(chars)

    # password has to be divided by 16 when using AES
    while not len(result)%16 == 0:
        result += '\x00'

    return result


def send_mail(_name, _accname):
    mailbody = "Lieber Admin!\n\nBitte erneuere den Gastaccount {} für {}.".format(_accname, _name)
    mailbody += "\nBitte benutze dafür das Script, was sich die dazugehörigen Daten (Passwort + Ablaufdatum) " \
                "automatisch aus der Datenbank holt." \
                "\n\nDeine Gastaccountverwaltung"

    msg = MIMEText(mailbody)
    msg['Subject'] = "Gastaccount für " +_accname
    msg['From'] = mail_from
    msg['To'] = mail_to

    s = smtplib.SMTP(smtp_host)
    s.send_message(msg)
    s.quit()


def encrypt(plaintext, key):
    IV = 16*'\x00'
    cipher = AES.new(key, AES.MODE_CBC, IV)
    return cipher.encrypt(plaintext)


def decrypt(ciphertext, key):
    IV = 16*'\x00'
    cipher = AES.new(key, AES.MODE_CBC, IV)
    return cipher.decrypt(ciphertext)


def verify_entry(accountid, guest_password, key):
    accounts = meta.tables["accounts"].c
    dbselect = meta.tables["accounts"].select().where(accounts.id == accountid)

    test_decrypted_pw = decrypt(b64decode(con.execute(dbselect).fetchone()['password']), key).decode()
    return test_decrypted_pw == guest_password


def create_guest_account(_name, expdate):
    # establish connection to database
    con, meta = sql_connect()
    # check if we have free guest accounts (results = (... state == "active" AND expdate < date.today()))
    accounts = meta.tables["accounts"].c
    sel = meta.tables["accounts"].select().\
        where((accounts.state == "active") & (accounts.expdate < date.today()))

    # assign free guest accounts (results[0]) #take the first one
    # try except, because we can have 0 available accounts
    try:
        firstEntry = list(con.execute(sel).fetchone())
        accountid = firstEntry[0]  # get id of the first result from the query
        accountname = firstEntry[1]
    except:
        return ""

    # generate new random password for guest account
    guest_password = generate_password()
    guest_password_enc = encrypt(guest_password, key)

    # increment date by 7 days
    real_expdate = expdate + timedelta(days=7)

    # change state of guest account to todo
    # generate update query with new information
    dbupdate = meta.tables["accounts"].update().\
        where(accounts.id == accountid).\
        values({'name': _name, 'expdate': real_expdate, 'password': b64encode(guest_password_enc).decode(), 'state': 'todo'})

    # execute query
    con.execute(dbupdate)

    # test if password in database is correct
    if not verify_entry(accountid, guest_password, key):
        raise ValueError("Password in database not the same as it should be.")

    return_message  = "Der Gastaccount <b>{accountname}</b> wird in den nächsten 7 Tagen <br>"
    return_message += "mit dem Ablaufdatum <b>{date}</b><br>"
    return_message += "und dem Passwort <b>{password}</b> erstellt.<br>"
    return_message += "Bitte teilen Sie <b>{name}</b> die obigen Daten mit."

    # User was created successfully in the database, so wen can trigger sendmail here
    send_mail(_name, accountname)

    return return_message.format(accountname=accountname,
                                 name=_name,
                                 date=expdate.strftime('%d.%m.%Y'),
                                 password=guest_password.strip('\x00')
                                )


def initialize_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template('index.html')

    @app.route("/sign_up", methods=['POST'])
    def sign_up():
        _name = request.form['inputName']
        _date = request.form['inputDate']

        # sanitize _name and _date!
        _name = html.escape(_name)
        _date = html.escape(_date)

        # check if _name and _date are not null and date as valid
        if _name == "":
            return json.dumps({'error': 'Bitte Name eintragen!'}), 500
        if _date == "":
            return json.dumps({'error': 'Bitte Datum eintragen!'}), 500
        try:
            _date = datetime.strptime(_date, "%Y-%m-%d")
            if _date < datetime.now():
                return json.dumps({'error': 'Bitte ein Datum in der Zukunft eintragen!'}), 500
        except ValueError as e:
            return json.dumps({'error': str(e)}), 500

        account = create_guest_account(_name, _date)
        if account == "":
            return json.dumps({'error': 'Es sind keine Gästeaccounts zur Zeit frei.<br>' +
                                        'Bitte kontaktieren sie einen ' +
                                        '<a href="{}" target="_blank">Admin</a>!'.format(admin_url),
                               'actn': 'disableBtn'}), 500

        if DEBUG:
            print("\nValues after successful update")
            from pprint import pprint
            pprint(list(con.execute(meta.tables["accounts"].select()).fetchall()))

        return json.dumps({'message': account})

    return app


if __name__ == "__main__":
    # get all environment variables
    mail_to = get_env_variable("GUEST_MAIL_TO")
    mail_from = get_env_variable("GUEST_MAIL_FROM")
    smtp_host = get_env_variable("GUEST_SMTP_HOST", default="localhost")
    flask_port = get_env_variable("GUEST_FLASK_PORT", default=5003, check_debug=False)
    admin_url = get_env_variable("GUEST_ADMIN_URL", default="", check_debug=False)
    sql_url = get_env_variable("GUEST_SQL_URL",
                               default='postgresql://guestaccounts@localhost/guestaccounts',
                               defaulttext="Using dev PSQL URL")
    key = get_env_variable("GUEST_KEY",
                           default = b'R\xc9P 9\xba\x96b\xc5\xe94`\xfb\xcf\xb6OlR\x11D\xe2\xf3\xeal',
                           defaulttext="Using dev AES key")

    # TODO create another script that (re)initializes the database
    # reset db entry
    con, meta = sql_connect()
    con.execute(meta.tables["accounts"].delete())
    for i in range(10):
        con.execute(
            meta.tables["accounts"].insert().\
            values({'id': i,
                    'accountname': 'guest{:02}'.format(i),
                    'name': None,
                    'expdate': date.today()-timedelta(days=1),
                    'password': None,
                    'state': 'active'})
        )

    if DEBUG:
        print("\nInitial Values at app startup")
        from pprint import pprint
        pprint(list(con.execute(meta.tables["accounts"].select()).fetchall()))

    # initialize flask
    app = initialize_app()
    app.run(port=flask_port)