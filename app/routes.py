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
    if(days < 10 ):
        days = 10
    elif (days > 50):
        days = 50

    # generate graphs
    nations = engine.gatherData()
    totalGraphRaw = engine.processData(nations,datetime.now().strftime(engine.DATE_FORMAT), days = days)
    deathsGraphRaw = engine.processData(nations,datetime.now().strftime(engine.DATE_FORMAT), isDeaths=True , days = days)
    deathsPopGraphRaw = engine.processData(nations, datetime.now().strftime(engine.DATE_FORMAT), isDeaths=True, isPopulation=True, days=days)

    return render_template('index.html',
                           countries=totalGraphRaw['countries'].decode('ascii') ,
                           delays=totalGraphRaw['delays'].decode('ascii'),
                           deathsCountries=deathsGraphRaw['countries'].decode('ascii'),
                           deathsDelays=deathsGraphRaw['delays'].decode('ascii'),
                           deathsPopCountries=deathsPopGraphRaw['countries'].decode('ascii'),
                           deathsPopDelays=deathsPopGraphRaw['delays'].decode('ascii'),
                           )