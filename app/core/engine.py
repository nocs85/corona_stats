import requests
import re
import collections
import base64
import matplotlib.pyplot as plt
from datetime import datetime
from datetime import timedelta
from io import BytesIO
from lxml import html

# the sole ISO-8601 format we support in this script
DATE_FORMAT = '%Y-%m-%d'
# arbitrary minimum date (some nations have earlier data)
MIN_DATE = '2020-02-21'


# Plots nation data up to the provided max date
def processData(iMaxDate, isDeaths=False):
    outputGraphRaw = {}

    print("Collecting data up to: '{0}'.".format(iMaxDate))

    nations = []

    Meta = collections.namedtuple('Meta', ['nation', 'url', 'dates', 'cases', 'delay'])
    nations.append(Meta('it', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Italy', [], [], 0))
    nations.append(Meta('de', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Germany', [], [], 0))
    nations.append(Meta('at', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Austria', [], [], 0))
    nations.append(Meta('us', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_the_United_States', [], [], 0))
    nations.append(Meta('fr', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_France', [], [], 0))
    nations.append(Meta('sp', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Spain', [], [], 0))
    nations.append(Meta('uk', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_the_United_Kingdom', [], [], 0))

#    NO DEATHS FOR CH / NO
#    nations.append(Meta('ch', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Switzerland', [], [], 0))
#    nations.append(Meta('no', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Norway', [], [], 0))

    for aNation in nations:
        parseNation(aNation, isDeaths)

    expandDatesAndCut(nations, MIN_DATE, iMaxDate)

    # generate raw data as reported on wiki
    countryChartRaw = BytesIO()
    title = "TOTAL - " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if isDeaths is True:
        title = "DEATHS - " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    plotData(nations, title, countryChartRaw)
    countryChartRaw.seek(0)
    outputGraphRaw['countries'] = base64.b64encode(countryChartRaw.getvalue())

    # get italy to calc the delay with the other nations
    it = nations[0]

    # calc the delay of the other countries wrt italy
    for n in range(1, len(nations)):
        cmp = nations[n]

        # calc the delay in days, use minimum square error
        diff = []
        for ii in range(0, len(cmp.cases)):
            ss = 0
            for jj in range(ii, len(cmp.cases)):
                c = jj - ii
                ss = ss + (int(it.cases[c]) - int(cmp.cases[jj])) ** 2
            diff.insert(ii, ss)

        aDelay = diff.index(min(diff))

        # align:
        # some data from other nations start later than italy, so we have to account for
        # that while shifting
        it_base_date = datetime.strptime(it.dates[0], DATE_FORMAT)
        cmp_base_date = datetime.strptime(cmp.dates[0], DATE_FORMAT)
        diff_days = (cmp_base_date - it_base_date).days

        for i in range(0, aDelay):
            cmp.cases.pop(0)
            cmp.dates.pop(0)

        # subtract the delay from each datum
        for i in range(0, len(cmp.cases)):
            subs = datetime.strptime(cmp.dates[i], DATE_FORMAT) + timedelta(days=-aDelay-diff_days)
            cmp.dates[i] = subs.strftime(DATE_FORMAT)

        # save the delay (requires in place replacement of element being a namedtuple)
        nations[n] = cmp._replace(delay=aDelay+diff_days)

    # sort by delay
    nations = sorted(nations, key=lambda nation: nation.delay)

    # generate raw data for delays
    delayChartRaw = BytesIO()
    title = 'TOTAL - Days to reach Italy, as of {0}'.format(iMaxDate)
    if isDeaths is True:
        title = 'DEATHS - Days to reach Italy, as of {0}'.format(iMaxDate)
    plotData(nations, title, delayChartRaw)
    delayChartRaw.seek(0)
    outputGraphRaw['delays'] = base64.b64encode(countryChartRaw.getvalue())

    return outputGraphRaw

# Parses wikpedia table format for the provided date range
# 
# special '⋮' are parsed only once the iMinDate has been reached
#
# - ioNation: meta array which will be parsed
def parseNation(ioNation, isDeaths):
    print('getting data for:' + ioNation.nation + ' ' + ioNation.url)
    r = requests.get(ioNation.url)
    tree = html.fromstring(r.content)
    # get the table with data - can be spotted by the header containing a specific text
    aTable = tree.xpath("//th[contains(text(), 'COVID-19 cases')]/ancestor::table")
    if (aTable is None) or (len(aTable) != 1):
        return
    # now get all of its rows
    rows = aTable[0].xpath(".//tr")
    if (rows is None) or (len(rows) == 0):  # no result found
        return
    # and for each row...
    # - well, not for each: wikipedia has three special rows, title, header, footers: skip them!
    for rowIndex in range(2,len(rows)-1):
        # ... its columns
        columns = rows[rowIndex].xpath(".//td")
        if (columns is None) or (len(columns) != 4):    # get rid of spurious data
            continue

        # column 0: date
        date = columns[0].text_content()
        if date != '⋮':
            iso8601YmdValidator(date)  # validate the format, in case we parsed a date
        ioNation.dates.append(date)

        # column 1: chart
        # -- ignore

        # column 2: total
        # column 3: deaths
        value = columns[2].text_content()
        if isDeaths == True:
            value = columns[3].text_content()
        if len(value) > 0:
            cases = value.split('(')[0].replace(',', '')
            ioNation.cases.append(cases)
        # wikipedia might store nothing: in this case it means ZERO (unless this is the last row, in which case
        # data is late: let's just assume the same number for now)
        elif rowIndex == len(rows)-2:
            ioNation.cases.append(ioNation.cases[-1])
        else:
            ioNation.cases.append(0)


# Expands the '⋮' placeholder with actual date-elements and then
# eliminates all the dates prior to iMinDate
#
# - iMinDate: all dates prior to this one will be filtered out
# - iMaxDate: all dates past this one will be filtered out
def expandDatesAndCut(ioNation, iMinDate, iMaxDate):
    # duplicate all the '⋮' elements found in 'dates' (placeholder used in wiki-tables to compress repeated case-numbers)
    for aNation in ioNation:
        for kdx, date in enumerate(aNation.dates):
            if date == '⋮':
                start = datetime.strptime(aNation.dates[kdx - 1], DATE_FORMAT)
                end = datetime.strptime(aNation.dates[kdx + 1], DATE_FORMAT)
                diff_days = (end - start).days

                cases = aNation.cases.pop(kdx)  # get the number of cases at the placeholder pos and then eliminate the '⋮' element
                aNation.dates.pop(kdx)  # eliminate the date at the placeholder position
                for days in range(diff_days - 1, 0, -1):  # count backwards the number of days to add instead of the placeholder
                    extrap = start + timedelta(days=days)
                    aNation.dates.insert(kdx, extrap.strftime(DATE_FORMAT))
                    aNation.cases.insert(kdx, cases)

    # now filter out the dates prior to iMinDate
    for aNation in ioNation:
        while aNation.dates[0] < iMinDate:
            aNation.cases.pop(0)
            aNation.dates.pop(0)

    # filter out all the dates past the newest available italian data
    for n in range(1, len(ioNation)):
        aNation = ioNation[n]
        while aNation.dates[-1] > ioNation[0].dates[-1]:
            aNation.cases.pop(-1)
            aNation.dates.pop(-1)


def plotData(ioNation, title, filename):
    # print the delayed plots, use italy as reference country
    plt.figure()
    for aNation in ioNation:
        y = list(map(int, aNation.cases))
        if aNation.delay == 0:
            plt.plot(aNation.dates, y, lw=0.5, marker='.', label=aNation.nation)
        else:
            plt.plot(aNation.dates, y, lw=0.5, marker='.', label=aNation.nation + ':' + str(-aNation.delay))
    plt.grid()
    plt.xticks(rotation=90)
    plt.legend()
    plt.title(title)
    plt.savefig(filename , format='png')


# Parses %Y-%m-%d ISO-8601 dates, raising an exception if violated
def iso8601YmdValidator(iDate):
    try:
        return datetime.strptime(iDate, DATE_FORMAT)
    except:
        msg = "Invalid date: '{0}'.".format(iDate)
        raise argparse.ArgumentTypeError(msg)
