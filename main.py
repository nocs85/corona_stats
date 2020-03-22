import argparse
import requests
import re
import collections
import matplotlib.pyplot as plt
from datetime import datetime
from datetime import timedelta

# the sole ISO-8601 format we support in this script
DATE_FORMAT = '%Y-%m-%d'
# arbitrary minimum date (some nations have earlier data)
MIN_DATE = '2020-02-21'


# Plots nation data up to the provided max date
def processData(iMaxDate):
    print("Collecting data up to: '{0}'.".format(iMaxDate))

    nations = []

    Meta = collections.namedtuple('Meta', ['nation', 'url', 'dates', 'cases', 'delay'])
    nations.append(Meta('it', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Italy', [], [], 0))
    nations.append(Meta('de', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Germany', [], [], 0))
    nations.append(Meta('at', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Austria', [], [], 0))
#    nations.append(Meta('us', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_the_United_States', [], [], -1))
    nations.append(Meta('fr', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_France', [], [], 0))
    nations.append(Meta('gb', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_the_United_Kingdom', [], [], 0))
    nations.append(Meta('sp', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Spain', [], [], 0))
    nations.append(Meta('ch', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Switzerland', [], [], 0))
    nations.append(Meta('no', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Norway', [], [], 0))

    for aNation in nations:
        parseNation(aNation)

    expandDatesAndCut(nations, MIN_DATE, iMaxDate)

    # print the plots with unedited data from wiki
    plotData(nations, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d_%H-%M-%S')+'.png')

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

    plotData(nations, 'Days to reach Italy, as of {0}'.format(iMaxDate), datetime.now().strftime('delay_%Y-%m-%d_%H-%M-%S') + '.png')
    plt.show()


# Parses wikpedia table format for the provided date range
# 
# special '⋮' are parsed only once the iMinDate has been reached
#
# - ioNation: meta array which will be parsed
def parseNation(ioNation):
    print('getting data for:' + ioNation.nation + ' ' + ioNation.url)

    state = 0
    r = requests.get(ioNation.url)
    for line in r.text.splitlines():
        if state == 0:  # search for <table...
            result = re.match(r'^<table .*>$', line)
            if result:
                state = 1
        elif state == 1:  # search for <td ....>date</td>
            result = re.match(r'^<td .*>(\d\d\d\d-\d\d\-\d\d|⋮)<\/td>$', line)
            if result:
                date = result.group(1)
                if date != '⋮':
                    iso8601YmdValidator(date)    # validate the format, in case we parsed a date
                ioNation.dates.append(date)
                state = 2
        elif state == 2:  # search for <td ....>number<...
            result = re.match(r'^<td .*>(\d+,*\d*)<.*', line)
            if result:
                cases = result.group(1).replace(',', '')
                ioNation.cases.append(cases)
                state = 1
        else:
            print('error')


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
    plt.savefig(filename)


# Parses %Y-%m-%d ISO-8601 dates, raising an exception if violated
def iso8601YmdValidator(iDate):
    try:
        return datetime.strptime(iDate, DATE_FORMAT)
    except:
        msg = "Invalid date: '{0}'.".format(iDate)
        raise argparse.ArgumentTypeError(msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plots transnational covid-19 statistics.')

    # optionally provide the limit date (by default today)
    parser.add_argument('--limitDate', type=iso8601YmdValidator, required=False,
                        help='target date for italian data (Y-m-d ISO-8601 format)',
                        default=datetime.now().strftime(DATE_FORMAT))
    args = parser.parse_args()

    processData(args.limitDate.strftime(DATE_FORMAT))
