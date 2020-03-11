import sqlite3
from flask import Flask
from flask import g

DATABASE = 'records.db'
app = Flask(__name__)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        Query = "SELECT Activity_Type FROM ActivityReference"
        db.execute(Query)
    return db

def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

        
@app.route('/')
def index():
    cur = get_db().cursor()
    
    c = "girl"
    for row in cur:
        c = row[0]
    return c
if(__name__ == "__main__"):
    app.run(debug = True)