import argparse
import requests
import re
import collections
import matplotlib.pyplot as plt
from datetime import datetime
from datetime import timedelta

# the sole ISO-8601 format we support in this script
DATE_FORMAT = '%Y-%m-%d'
# arbitrary minumum date (some nations have earlier data)
MIN_DATE = '2020-01-31'

# Plots nation data up to the provided max date
def plotData(iMaxDate):
    print("Collecting data up to: '{0}'.".format(iMaxDate))

    nations = []

    Meta = collections.namedtuple('Meta', ['nation', 'url', 'dates', 'cases'])
    nations.append(Meta('it', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Italy', [], []))
    nations.append(Meta('de', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Germany', [], []))
    nations.append(Meta('at', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Austria', [], []))
    nations.append(Meta('us', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_the_United_States', [], []))
    nations.append(Meta('fr', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_France', [], []))
    nations.append(Meta('gb', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_the_United_Kingdom', [], []))
    nations.append(Meta('sp', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Spain', [], []))
    nations.append(Meta('ch', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Switzerland', [], []))
    nations.append(Meta('no', 'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Norway', [], []))

    for aNation in nations:
        parseNation(aNation,MIN_DATE,iMaxDate)


    # duplicate all the '⋮' elements found in 'dates' (placeholder used in wiki-tables to compress repeated case-numbers)
    for i in nations:
        print(i.nation + ' ' + i.url + ':')

        for kdx, date in enumerate(i.dates):
            if date == '⋮':
                start = datetime.strptime(i.dates[kdx-1], DATE_FORMAT)
                end = datetime.strptime(i.dates[kdx+1], DATE_FORMAT)
                diff_days = (end-start).days

                cases = i.cases.pop(kdx)        # get the number of cases at the placeholder pos and then eliminate the '⋮' element
                i.dates.pop(kdx)                # eliminate the date at the placeholder position
                for days in range(diff_days-1, 0, -1):      # count backwards the number of days to add instead of the placeholder
                    extrap = start + timedelta(days=days)
                    i.dates.insert(kdx, extrap.strftime('%Y-%m-%d'))
                    i.cases.insert(kdx, cases)


    # print the plots with unedited data from wiki
    plt.figure()
    for it in nations:
        y = list(map(int, it.cases))    # convert cases str-array to integer-array
        plt.plot(it.dates, y, lw=0.5, marker='.', label=it.nation)
    plt.grid(True)
    plt.xticks(rotation=90)
    plt.legend()
    plt.title(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    plt.savefig(datetime.now().strftime('%Y-%m-%d_%H-%M-%S')+'.png')


    # print the delayed plots, use italy as reference country
    plt.figure()
    it = nations[0]
    y = list(map(int, it.cases))
    plt.plot(it.dates, y, lw=0.5, marker='.', label=it.nation)

    # calc the delay of the other countries wrt italy
    for n in range(1, len(nations)):
        de = nations[n]
        # each 'cases' vector has to have the length of the italy-cases vector
        # fill up as needed with heading zero-cases
        for bckw in range(0, len(it.cases)-len(de.cases)):  # count backwards the number of days to add
            extrap = datetime.strptime(de.dates[0], ('%Y-%m-%d')) + timedelta(days=-1)
            de.dates.insert(0, extrap.strftime('%Y-%m-%d'))
            de.cases.insert(0, 0)

        # cut cases-vector if longer than italy-cases
        if len(de.cases) > len(it.cases):
            for rm in range(0, len(de.cases)-len(it.cases)):
                de.cases.pop(0)
                de.dates.pop(0)

        # calc the delay in days
        # use minimum square error
        diff = []
        for ii in range(0, len(it.cases)):      # iterate over all the italy-cases
            sum = 0
            for jj in range(0, len(it.cases)-ii):   # shift by one and iterate over the remaining cases of the other country
                sum = sum + (int(it.cases[jj])-int(de.cases[ii+jj]))**2
            sum = sum / (jj+1)
            diff.insert(ii, sum)

        delay = diff.index(min(diff))

        # remove elements from the list's head
        for i in range(0, delay):
            de.cases.pop(0)
            de.dates.pop(0)
        # subtract the delay from each datum
        for i in range(0, len(de.cases)):
            subs = datetime.strptime(de.dates[i], (DATE_FORMAT)) + timedelta(days=-delay)
            de.dates[i] = subs.strftime(DATE_FORMAT)

        # now plot
        y = list(map(int, de.cases))
        plt.plot(de.dates, y, lw=0.5, marker='.', label=de.nation+':'+str(delay))

    plt.xticks(rotation=90)
    plt.legend()
    plt.title('Days to reach Italy, as of {0}'.format(iMaxDate))
    plt.savefig(datetime.now().strftime('delay_%Y-%m-%d_%H-%M-%S')+'.png')
    plt.show()
    None

# Parses wikpedia table format for the provided date range
# 
# special '⋮' are parsed only once the iMinDate has been reached
#
# - ioNation: meta array which will be parsed
# - iMinDate: all dates prior to this one will be filtered out
# - iMaxDate: all dates past this one will be filtered out
def parseNation(ioNation,iMinDate,iMaxDate):
    print('getting data for:' + ioNation.nation + ' ' + ioNation.url)

    isMinDatePassed = False
    state = 0
    date = ''
    number = ''
    r = requests.get(ioNation.url)
    for line in r.text.splitlines():
        if state == 0:  #search for <table...
            result = re.match(r'^<table .*>$', line)
            if result:
                state = 1
        elif state == 1: #search for <td ....>date</td>
            result = re.match(r'^<td .*>(\d\d\d\d-\d\d\-\d\d|⋮)<\/td>$', line)
            if result:
                # Y-m-d ISO-8601 formatted dates can be compared lexicographically
                # ('⋮' special element, for repeated might be considered depending 
                # if we ever reached the minimum date)
                if result.group(1) != '⋮':
                    iso8601YmdValidator(result.group(1))
                    if result.group(1) < iMinDate:
                        continue
                    isMinDatePassed = True
                    if result.group(1) > iMaxDate:
                        break
                # 
                elif isMinDatePassed is False:
                    continue
                date = result.group(1)
                ioNation.dates.append(date)
                state = 2
        elif state == 2: #search for <td ....>number<...
            result = re.match(r'^<td .*>(\d+,*\d*)<.*', line)
            if result:
                cases = result.group(1)
                cases = cases.replace(',', '')
                ioNation.cases.append(cases)
                state = 1
        else:
            print('error')
    
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
    parser.add_argument('--limitDate', type=iso8601YmdValidator, required=False, help='target date for italian data (Y-m-d ISO-8601 format)', default=datetime.now().strftime(DATE_FORMAT))
    args = parser.parse_args()
    
    plotData(args.limitDate.strftime(DATE_FORMAT))