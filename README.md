# Gastaccountverwaltung — guest account management
(written for the [Mathematisches Institut at Heidelberg
University](https://www.mathi.uni-heidelberg.de))

This script manages a possibility to send guest account requests to the
administrators without storing the passwords in plain in a database.

## Setup
You have to set up a Database with an available
[sqlalchemy](https://www.sqlalchemy.org) adapter and create an empty table
“accounts”.

Install the requirements (in an virtual environment):

    python3 -m venv <venv-directory>
    source <venv-directory>/bin/activate
    pip install -r requirements.txt

## Run
You have to set these environment Variables:

    GUEST_MAIL_TO=to@example.org
    GUEST_MAIL_FROM=from@example.org
    GUEST_SMTP_HOST=localhost
    GUEST_FLASK_PORT=5003
    GUEST_ADMIN_URL=https://www.example.org/fancyadmins.html
    GUEST_SQL_URL=postgresql://localhost/guestaccounts
    GUEST_KEY=<key with length which can be devided by 16>

Run this script via:

    python3 main.py

## Debug
To debug the script one can set this environment variable:

    DEBUG=True
