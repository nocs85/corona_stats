from app import app
from app.core import engine
from flask import render_template
from flask import request
from datetime import datetime

@app.route('/')
@app.route('/index')
@app.route('/index.html')
def index():

    # get any query param for the number of days between [5, 60] , defaulting to 25
    days = request.args.get('days', default=25, type=int)
    if(days < 5 ) or (days > 60):
        days = 25

    # generate graphs
    totalGraphRaw = engine.processData(datetime.now().strftime(engine.DATE_FORMAT), days = days)
    deathsGraphRaw = engine.processData(datetime.now().strftime(engine.DATE_FORMAT), isDeaths=True , days = days)

    return render_template('index.html',
                           countries=totalGraphRaw['countries'].decode('ascii') ,
                           delays=totalGraphRaw['delays'].decode('ascii'),
                           deathsCountries=deathsGraphRaw['countries'].decode('ascii'),
                           deathsDelays=deathsGraphRaw['delays'].decode('ascii'),
                           )