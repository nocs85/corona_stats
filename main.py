import requests
import re
import collections
import matplotlib.pyplot as plt
from datetime import datetime
from datetime import timedelta

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

for i in nations:
    print('getting data for:' + i.nation + ' ' + i.url)

    state = 0
    date = ''
    number = ''
    r = requests.get(i.url)
    for line in r.text.splitlines():
        if state == 0:  #search for <table...
            result = re.match(r'^<table .*>$', line)
            if result:
                state = 1
        elif state == 1: #search for <tr ....>date</tr>
            result = re.match(r'^<td .*>(\d\d\d\d-\d\d\-\d\d|⋮)<\/td>$', line)
            if result:
                date = result.group(1)
                i.dates.append(date)
                state = 2
        elif state == 2: #search for <tr ....>number</tr>
            result = re.match(r'^<td .*>(\d+,*\d*)<.*', line)
            if result:
                cases = result.group(1)
                cases = cases.replace(',', '')
                i.cases.append(cases)
                state = 1
        else:
            print('error')


# duplicate all the '⋮' elements found in 'dates' (placeholder used in wiki-tables to compress repeated case-numbers)
for i in nations:
    print(i.nation + ' ' + i.url + ':')

    for kdx, date in enumerate(i.dates):
        if date == '⋮':
            start = datetime.strptime(i.dates[kdx-1], '%Y-%m-%d')
            end = datetime.strptime(i.dates[kdx+1], '%Y-%m-%d')
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
        subs = datetime.strptime(de.dates[i], ('%Y-%m-%d')) + timedelta(days=-delay)
        de.dates[i] = subs.strftime('%Y-%m-%d')

    # now plot
    y = list(map(int, de.cases))
    plt.plot(de.dates, y, lw=0.5, marker='.', label=de.nation+':'+str(delay))

plt.xticks(rotation=90)
plt.legend()
plt.title(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
plt.savefig(datetime.now().strftime('delay_%Y-%m-%d_%H-%M-%S')+'.png')
plt.show()
None