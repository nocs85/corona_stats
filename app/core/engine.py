import grequests
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
DAYS_WINDOW_SIZE = 25
MIN_ITALY_DATE = '2020-02-21'

# simple method to return the URL and print some debug info
#
# Returns the url
def getUrl(aNation):
    print('Gathering data for', aNation.nation , aNation.url)
    return aNation.url

# gather data at once for the configured list of nations
#
# Returns the namedtuple for all nations
def gatherData():
    nations = []

    Meta = collections.namedtuple('Meta', ['nation', 'url', 'dates', 'cases', 'delay', 'content'])
    nations.append(Meta('it', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Italy', [], [], 0, ''))
    nations.append(Meta('de', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Germany', [], [], 0, ''))
    nations.append(Meta('at', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Austria', [], [], 0, ''))
    nations.append(Meta('us', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_the_United_States', [], [], 0, ''))
    nations.append(Meta('fr', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_France', [], [], 0, ''))
    nations.append(Meta('sp', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Spain', [], [], 0, ''))
    nations.append(Meta('uk', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_the_United_Kingdom', [], [], 0, ''))
    nations.append(Meta('nl', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_the_Netherlands', [], [], 0, ''))
    #    NO DEATHS FOR CH / NO
    nations.append(Meta('ch', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Switzerland', [], [], 0, ''))
    nations.append(Meta('no', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Norway', [], [], 0, ''))

    # retrieve all nations' content
    results = grequests.map((grequests.get(getUrl(nations[n])) for n in range(0, len(nations))))
    for n in range(0, len(nations)):
        # insert content in tuple (darn replace)
        nations[n] = nations[n]._replace(content=results[n].content)

    return nations


# Plots nation data up to the provided max date
#
# - ioNationList list of nation named tuples, populated as output
# - iMaxDate max date
# - isDeaths flag to determine if deaths are to be plotted rather than cases
# - days sliding window configuration
def processData(ioNationList, iMaxDate, isDeaths=False, days=DAYS_WINDOW_SIZE):
    # collect last days worth of data
    minDate = (datetime.now() - timedelta(days=days)).strftime(DATE_FORMAT)

    # Italy is our baseline: since there is no interesting data prior to this date, just stop
    if minDate < MIN_ITALY_DATE:
        minDate = MIN_ITALY_DATE
        days = (datetime.strptime(iMaxDate, DATE_FORMAT) - datetime.strptime(minDate, DATE_FORMAT)).days

    outputGraphRaw = {}

    print("Plotting data from", minDate, "to", iMaxDate, "deaths?", isDeaths)

    # for each nation
    for n in range(0, len(ioNationList)):
        # clear data (darn replace)
        ioNationList[n] = ioNationList[n]._replace(dates=[], cases=[], delay=0)
        # parse data from content
        parseNation(ioNationList[n], isDeaths)

    expandDatesAndCut(ioNationList, minDate)

    # generate raw data as reported on wiki
    countryChartRaw = BytesIO()
    title = "TOTAL (last " + str(days) + " days) - " + datetime.now().strftime(DATE_FORMAT)
    if isDeaths is True:
        title = "DEATHS (last " + str(days) + " days) - " + datetime.now().strftime(DATE_FORMAT)
    plotData(ioNationList, title, countryChartRaw)
    countryChartRaw.seek(0)
    outputGraphRaw['countries'] = base64.b64encode(countryChartRaw.getvalue())

    # get italy to calc the delay with the other nations
    it = ioNationList[0]

    # calc the delay of the other countries wrt italy
    for n in range(1, len(ioNationList)):
        cmp = ioNationList[n]
        # no need to process nations with no data (this is the case for some deaths)
        if len(cmp.dates) == 0:
            continue

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

        # check if there are new dates that are falling before the min date (to be filtered out)
        lastIndex = -1
        for i in range(0, len(cmp.dates)):
            subs = datetime.strptime(cmp.dates[i], DATE_FORMAT) + timedelta(days=-aDelay - diff_days)
            aNewDate = subs.strftime(DATE_FORMAT)
            # as soon as a date is past: all good, but until them we need to filter
            if aNewDate > minDate:
                lastIndex = i
                break
        # then get rid of all of such cases
        if lastIndex >= 1:
            del cmp.cases[:lastIndex-1]
            del cmp.dates[:lastIndex-1]

        # subtract the delay from each datum
        for i in range(0, len(cmp.dates)):
            subs = datetime.strptime(cmp.dates[i], DATE_FORMAT) + timedelta(days=-aDelay - diff_days)
            aNewDate = subs.strftime(DATE_FORMAT)
            cmp.dates[i] = aNewDate

        # save the delay (requires in place replacement of element being a namedtuple)
        ioNationList[n] = cmp._replace(delay=aDelay + diff_days)

    # sort by delay
    ioNationList = sorted(ioNationList, key=lambda nation: nation.delay)

    # generate raw data for delays
    delayChartRaw = BytesIO()
    title = "NORMALIZED TOTAL (last " + str(days) + " days) - " + iMaxDate
    if isDeaths is True:
        title = "NORMALIZED DEATHS (last " + str(days) + " days) - " + iMaxDate
    plotData(ioNationList, title, delayChartRaw)
    delayChartRaw.seek(0)
    outputGraphRaw['delays'] = base64.b64encode(delayChartRaw.getvalue())

    return outputGraphRaw


def parseNation(ioNation, isDeaths):
    tree = html.fromstring(ioNation.content)
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
    lastValue = None
    for rowIndex in range(2, len(rows) - 1):
        # ... its columns
        columns = rows[rowIndex].xpath(".//td")
        if (columns is None) or (len(columns) < 3):  # get rid of spurious data
            continue

        # column 0: date
        date = columns[0].text_content()
        if date != '⋮':
            iso8601YmdValidator(date)  # validate the format, in case we parsed a date

        # when new data is getting added, edits on wikipedia might be... copy paste! Skip it for the moment
        if date in ioNation.dates:
            continue

        # append the date only if we have a value

        # column 1: chart
        # -- ignore

        # column 2: total
        # column 3: deaths
        value = columns[2].text_content()
        if isDeaths == True:
            if len(columns) >= 4:
                value = columns[3].text_content()
            else:
                continue  # no deaths for this collected dataset

        # extract the first number in the value string
        # examples:
        #  1,809(+26%)
        #  [vi]8,215(+9.5%)     # the [vi] is a note
        result = re.search('([0-9.,]+)', value)
        if result:
            cases = result.group(0).replace(',', '')
            lastValue = cases  # save the last encountered value
            ioNation.cases.append(numberValidator(cases))  # validate the format
            ioNation.dates.append(date)
        # wikipedia might store nothing: in this case it means ZERO (if no further value was ever encountered)
        elif lastValue is None:
            ioNation.cases.append(0)
            ioNation.dates.append(date)


# Expands the '⋮' placeholder with actual date-elements and then
# eliminates all the dates prior to iMinDate
#
# - iMinDate: all dates prior to this one will be filtered out
def expandDatesAndCut(ioNation, iMinDate):
    # duplicate all the '⋮' elements found in 'dates' (placeholder used in wiki-tables to compress repeated case-numbers)
    for aNation in ioNation:
        for kdx, date in enumerate(aNation.dates):
            if date == '⋮':
                start = datetime.strptime(aNation.dates[kdx - 1], DATE_FORMAT)
                end = datetime.strptime(aNation.dates[kdx + 1], DATE_FORMAT)
                diff_days = (end - start).days

                cases = aNation.cases.pop(
                    kdx)  # get the number of cases at the placeholder pos and then eliminate the '⋮' element
                aNation.dates.pop(kdx)  # eliminate the date at the placeholder position
                for days in range(diff_days - 1, 0,
                                  -1):  # count backwards the number of days to add instead of the placeholder
                    extrap = start + timedelta(days=days)
                    aNation.dates.insert(kdx, extrap.strftime(DATE_FORMAT))
                    aNation.cases.insert(kdx, cases)

    # now filter out the dates prior to iMinDate
    for aNation in ioNation:
        while (len(aNation.dates) > 0) and (aNation.dates[0] < iMinDate):
            aNation.cases.pop(0)
            aNation.dates.pop(0)

    # filter out all the dates past the newest available italian data
    for n in range(1, len(ioNation)):
        aNation = ioNation[n]
        while (len(aNation.dates) > 0) and (aNation.dates[-1] > ioNation[0].dates[-1]):
            aNation.cases.pop(-1)
            aNation.dates.pop(-1)


def plotData(ioNation, title, filename):
    # print the delayed plots, use italy as reference country
    plt.figure()
    for aNation in ioNation:
        # skip countries with no data (might happen with deaths)
        if len(aNation.dates) == 0:
            continue

        y = list(map(int, aNation.cases))
        if aNation.delay == 0:
            plt.plot(aNation.dates, y, lw=0.5, marker='.', label=aNation.nation)
        else:
            plt.plot(aNation.dates, y, lw=0.5, marker='.', label=aNation.nation + ':' + str(-aNation.delay))
    plt.grid()
    plt.xticks(rotation=90)
    plt.legend()
    plt.title(title)
    plt.savefig(filename, format='png')


# Parses %Y-%m-%d ISO-8601 dates, raising an exception if violated
def iso8601YmdValidator(iDate):
    try:
        return datetime.strptime(iDate, DATE_FORMAT)
    except:
        msg = "Invalid date: '{0}'.".format(iDate)
        raise argparse.ArgumentTypeError(msg)


def numberValidator(iNumber):
    try:
        return str(int(iNumber))
    except:
        msg = "Invalid int: '{0}'.".format(iNumber)
        raise argparse.ArgumentTypeError(msg)
