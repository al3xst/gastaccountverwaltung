from flask import Flask, json, render_template, request

from email.mime.text import MIMEText  # sendmail

from Crypto.Cipher import AES

import datetime
import html  # html escape
import os # to capture env vars
import random  # pwgen
import smtplib  # sendmail
import sqlalchemy  # psql connection
import string

#  aes key, generated with  get_random_bytes(30)


mailto = ""
mailfrom = ""
FLASK_PORT = 5003  # change, so no conflicts arise with other running flask apps


print("*** ============= ***")
print("Mails will be sent to: ")
print(mailto)
print("*** ============= ***")
print()

try:
    key = os.environ["GASTACCKEY"].encode()
except KeyError:
    # TODO UNCOMMENT IN PRODUCTION!!
    # print("ENV Variable 'GASTACCKEY' not set. Exiting program.")
    # raise
    print("*** ==================== ***")
    print("*** USING DEV AES KEY!!! ***")
    print("*** ==================== ***")
    print()
    key = b'R\xc9P 9\xba\x96b\xc5\xe94`\xfb\xcf\xb6OlR\x11D\xe2\xf3\xeal'

app = Flask(__name__)


def connect():
    # Returns a connection and a metadata object
    try:
        url = os.environ["GASTACCPSQL"]
    except KeyError:
        # print("ENV Variable 'GASTACCPSQL' not set. Exiting program.")
        # raise
        # TODO UNCOMMENT IN PRODUCTION!!
        print("*** ==================== ***")
        print("*** USING DEV PSQL URL!!! ***")
        print("*** ==================== ***")
        print()
        url = 'postgresql://guestaccounts@localhost/guestaccounts'

    # The return value of create_engine() is our connection object
    con = sqlalchemy.create_engine(url, client_encoding='utf8')

    # We then bind the connection to MetaData()
    meta = sqlalchemy.MetaData(bind=con, reflect=True)

    return con, meta


def genPassword(_pwlen = 8):

    chars = string.ascii_letters[:] + "".join([str(x) for x in range(10)])

    result = ""
    for _ in range(_pwlen):
        result += random.choice(chars)

    return result


def sendMail(_name, _accname):

    mailbody = "Lieber Admin!\n\nBitte erneuere den Gastaccount {} für {}.".format(_accname, _name)
    mailbody += "\nBitte benutze dafür das Script, was sich die dazugehörigen Daten (Passwort + Ablaufdatum) " \
                "automatisch aus der Datenbank holt." \
                "\n\nDeine Gastaccountverwaltung"

    msg = MIMEText(mailbody)

    msg['Subject'] = "Gastaccount für " +_accname
    msg['From'] = mailfrom
    msg['To'] = mailto

    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()


def decrypt(ciphertext):
    IV = 16 *'\x00'
    cipher = AES.new(key, AES.MODE_CBC, IV)
    return cipher.decrypt(ciphertext)


def createGuestAccount(_name, _date):

    # establish connection to database
    con, meta = connect()
    # check if we have free guest accounts (results = (... state == "active" AND expdate < date.today()))
    accounts = meta.tables["accounts"].c
    sel = meta.tables["accounts"].select().\
        where((accounts.state == "active") & (accounts.expdate < datetime.date.today()))

    # assign free guest accounts (results[0]) #take the first one
    # try except, because we can have 0 available accounts
    try:
        firstEntry = list(con.execute(sel).fetchone())
        accountid = firstEntry[0]  # get id of the first result from the query
        accoutnname = firstEntry[1]
    except:
        return ""

    # generate new random password for guest account

    guestpassword = genPassword()  # using default len of 10 chars
    guestpwEnc = guestpassword #.encode("utf-8")
    IV = 16*'\x00'
    print(type(key))
    cipher = AES.new(key, AES.MODE_CBC, IV)
    guestpasswordEnc = cipher.encrypt(guestpwEnc)

    print(decrypt(guestpasswordEnc))
    print(guestpwEnc)

    # change date+7
    date_1 = datetime.datetime.strptime(_date, "%Y-%m-%d")
    expdate = date_1 + datetime.timedelta(days=7)

    # change state of guest account to todo
    # generate update query with new information
    dbupdate = meta.tables["accounts"].update().\
        where(accounts.id == accountid).\
        values({'name': _name, 'expdate': expdate, 'password': guestpasswordEnc, 'state': 'todo'})

    # execute query
    con.execute(dbupdate)

    rtrnMsg = "Der Gastaccount <b>" + accoutnname + "</b> wird in den nächsten 7 Tagen erstellt<br> für <b>" + _name
    rtrnMsg += "</b> bis zum <b>" + _date + "</b><br> mit dem Passwort <b>"+guestpassword+"</b>"

    # User was created successfully in the database, so wen can trigger sendmail here
    sendMail(_name, accoutnname)

    return rtrnMsg


@app.route("/")
def main():

    return render_template('index.html')


@app.route("/signUp", methods=['POST'])
def signUp():

    _name = request.form['inputName']
    _date = request.form['inputDate']

    # sanitize _name and _date!
    _name = html.escape(_name)
    _date = html.escape(_date)

    # check if _name and _date are valid (not null)
    if _name == "" or _date == "":
        return json.dumps({'error': 'Bitte Name und Datum eintragen!'}), 500

    account = createGuestAccount(_name, _date)

    if account == "":
        return json.dumps({'error': 'Es sind keine Gästeaccounts zur Zeit frei.<br> Bitte kontaktieren sie einen Admin!',
                           'actn': 'disableBtn'}), 500

    return json.dumps({'message': account})


if __name__ == "__main__":

    con, meta = connect()

    #reset db entry
    accounts = meta.tables["accounts"].c
    dbupdate = meta.tables["accounts"].update().\
        where(accounts.id == 0).\
        values({'name': "Alex S", 'expdate': "2015-7-6", 'password': "asdf", 'state': 'active'})
    con.execute(dbupdate)

    # query = meta.tables["accounts"].insert().values(id = 0,
    #                                                 accountname='testacc',
    #                                                 name='Alex S',
    #                                                 expdate='2017-07-06',
    #                                                 password='totalsecret',
    #                                                 state='todo')
    #
    #con.execute(query)

    for row in con.execute(meta.tables["accounts"].select()):
        print(row)
    print(list(con.execute(meta.tables["accounts"].select()).fetchone())[0])

    app.run(port=FLASK_PORT)