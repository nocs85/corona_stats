from app import app
from app.core import engine
from flask import render_template
from datetime import datetime

@app.route('/')
@app.route('/index')
def index():
    # generate graphs
    totalGraphRaw = engine.processData(datetime.now().strftime(engine.DATE_FORMAT))
    deathsGraphRaw = engine.processData(datetime.now().strftime(engine.DATE_FORMAT), isDeaths=True)

    return render_template('index.html',
                           countries=totalGraphRaw['countries'].decode('ascii') ,
                           delays=totalGraphRaw['delays'].decode('ascii'),
                           deathsCountries=deathsGraphRaw['countries'].decode('ascii'),
                           deathsDelays=deathsGraphRaw['delays'].decode('ascii'),
                           )