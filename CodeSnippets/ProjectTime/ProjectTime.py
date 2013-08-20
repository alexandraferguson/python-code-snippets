#!/usr/bin/python
# coding: ISO-8859-15


"""
    Ermittelt anhand der timestamp von Verz. und Dateien die Arbeitszeit
    an einem Projekt.

    http://www.jensdiemer.de

    license = GNU General Public License v3 or above
      en -> http://www.opensource.org/licenses/gpl-license.php
      de -> http://jensdiemer.de/Programmieren/GPL-License
"""

__version__ = "v0.1"
__history__ = """
v0.1
    - erste Version
"""

import os, datetime, math

weekDaysMap = {
    "Mon": "MO",
    "Tue": "DI",
    "Wed": "MI",
    "Thu": "DO",
    "Fri": "FR",
    "Sat": "SA",
    "Sun": "SO"
}

day_additionals = {
    "SA":1.5,
    "SO":1.5,
}

class TimeStore(dict):
    def add(self, time, filePath):
        if not self.has_key(time):
            self[time] = []
        self[time].append(filePath)



class Chronologer:
    def __init__(self,
        projectPath, # Pfad in dem die Projectdateinen liegen
        hourlyRate, # Stundenlohn
        maxTimeDiff=60 * 60, # max Zeit, die ein Arbeitsblock trennt
        minBlockTime=30 * 60, # kleinste Zeiteinheit, f�r einen Block
        # Erster und letzter Tag, andere Zeiten werden ignoriert
        projectStart=datetime.datetime(year=1977, month=1, day=1),
        projectEnd=datetime.datetime(year=2200, month=12, day=31),
        exclude_dirs=None,
        day_additionals=day_additionals,
        debug=False,
            ):

        self.projectPath = projectPath
        self.maxTimeDiff = maxTimeDiff
        self.minBlockTime = minBlockTime
        self.hourlyRate = hourlyRate
        self.projectStart = projectStart
        self.projectEnd = projectEnd
        self.exclude_dirs = exclude_dirs or []
        self.day_additionals = day_additionals
        self.debug = debug

        self.statistics = {}
        self.dayData = {}
        self.timeStore = TimeStore()

        print "read %r..." % self.projectPath,
        count = self.readDir(self.projectPath)
        print "OK (%s items)" % count

        print "calc blocks...",
        timeBlocks = self.makeBlocks()
        print "OK"

        print "analyseBlocks...",
        self.analyseBlocks(timeBlocks)
        print "OK"

    def readDir(self, path):
        """ Einlesen der Verzeichnis Informationen """

        def exclude_dir(dir):
            dir = "\\%s\\" % dir.strip("\\")
            for exclude_dir in self.exclude_dirs:
                exclude_dir = "\\%s\\" % exclude_dir.strip("\\")

                #~ print dir, exclude_dir
                #~ if dir.startswith(exclude_dir):
                if exclude_dir in dir:
                    return True
            return False

        count = 0
        if not os.path.isdir(path):
            raise SystemError("Path '%s' not found!" % path)

        for root, dirs, files in os.walk(path):
            if exclude_dir(root):
                if self.debug:
                    print "Skip dir %r..." % root
                continue
            for dir in dirs:
                count += 1
                self.statFile(os.path.join(root, dir))
            for fileName in files:
                count += 1
                self.statFile(os.path.join(root, fileName))
        return count

    def statFile(self, path):
        """ Zeiten f�r Verz.Eintrag festhalten """
        try:
            pathStat = os.stat(path)
        except Exception, err:
            print "Error getting stat for %r: %s" % (path, err)
            return
        creationTime = pathStat.st_ctime
        lastAccess = pathStat.st_atime
        lastModification = pathStat.st_mtime

        if self.debug:
            print "File %r:" % path
            print "creation time...: %r" % datetime.datetime.fromtimestamp(creationTime)
            print "last access time: %r" % datetime.datetime.fromtimestamp(lastAccess)
            print "last modify time: %r" % datetime.datetime.fromtimestamp(lastModification)

        self.timeStore.add(creationTime, path)
        self.timeStore.add(lastAccess, path)
        self.timeStore.add(lastModification, path)

    def makeBlocks(self):
        """ Zusammenh�ngende Arbeitszeiten ermitteln """
        timeList = self.timeStore.keys()
        timeList.sort()

        # Ende-Datum soll inkl. des angegebenen Tags sein
        projectEnd = self.projectEnd + datetime.timedelta(days=1)

        timeBlocks = []
        lastTime = 0
        for t in timeList:
            d = datetime.datetime.fromtimestamp(t)
            if d < self.projectStart: continue
            if d > projectEnd: continue

            if (t - lastTime) > self.maxTimeDiff:
                # Ein neuer Block, weil die Differenz zu gro� ist
                timeBlocks.append([])

            timeBlocks[-1].append(t)
            lastTime = t

        return timeBlocks

    def blockTime(self, block):
        """ Liefert die Zeit eines Blocks zur�ck """
        if len(block) == 1:
            return self.minBlockTime

        workTime = block[-1] - block[0]
        if workTime < self.minBlockTime:
            return self.minBlockTime

        return workTime

    def analyseBlocks(self, timeBlocks):
        """
        Ermittelt gesammt Arbeitszeit und kalkuliert die Zeit f�r
        jeden Arbeits-Block
        """
        self.statistics["totalTime"] = 0
        self.statistics["day_additionals"] = {}
        days = {}
        for block in timeBlocks:
            blockTime = self.blockTime(block)
            self.statistics["totalTime"] += blockTime

            d = datetime.datetime.fromtimestamp(block[0])
            key = d.strftime("%y%m%d")
            day_name = weekDaysMap[d.strftime("%a")]

            if day_name in self.statistics["day_additionals"]:
                self.statistics["day_additionals"][day_name] += blockTime
            else:
                self.statistics["day_additionals"][day_name] = blockTime

            if key in self.dayData:
                self.dayData[key]["blockTime"] += blockTime
                self.dayData[key]["block"].append(block)
            else:
                self.dayData[key] = {
                    "dayName"   : day_name,
                    "week"      : d.strftime("%W"),
                    "dateStr"   : d.strftime("%d.%m.%Y"),
                    "blockTime" : blockTime,
                    "block"     : [block],
                }

    def displayBlock(self, dayBlock, verbose):
        """
        Anzeige eines zusammenh�ngenden Blockes
        """
        for coherentBlocks in dayBlock:
            dirInfo = {}
            for timestamp in coherentBlocks:
                fileList = self.timeStore[timestamp]
                for path in fileList:
                    dir, file = os.path.split(path)

                if not dirInfo.has_key(dir):
                    dirInfo[dir] = []

                dirInfo[dir].append(file)

            dirs = dirInfo.keys()
            dirs.sort()
            for dirName in dirs:
                shortDirName = ".%s" % dirName[len(self.projectPath):]

                if verbose == 1:
                    print "\t%3s files in %s" % (
                        len(dirInfo[dirName]), shortDirName
                    )
                else:
                    print "\t%s" % shortDirName
                    for fileName in dirInfo[dirName]:
                        print "\t\t%s" % fileName
        print

    def displayResults(self, verbose=0):
        """
        Anzeigen der Ergebnisse
        verbose = 0 -> normale Ansicht, nur Tag und Std.-Anzahl
        verbode = 1 -> Anzahl der ge�nderten Dateien
        verbode = 2 -> Auflistung der ge�nderten Dateien
        """
        totalTime = self.statistics["totalTime"]
        print
        print ">display Results"
        print
        print "totalTime: %sSec -> %.2fStd -> %.2f 8-Std-Tage" % (
            totalTime, totalTime / 60.0 / 60.0,
            totalTime / 60.0 / 60.0 / 8.0
        )
        keys = self.dayData.keys()
        keys.sort()

        print "-" * 40

        lastWeek = 0
        total_hours = 0
        for i, key in enumerate(keys):
            dayName = self.dayData[key]["dayName"]
            week = self.dayData[key]["week"]
            dateStr = self.dayData[key]["dateStr"]
            blockTime = self.dayData[key]["blockTime"]
            block = self.dayData[key]["block"]

            if week > lastWeek: # Leerzeile zwischen den Wochen
                print
                print "Woche: %s" % week
            lastWeek = week

            blockTime = int(math.ceil(blockTime / 60.0 / 60.0)) # Aufrunden
            print "%4s - %s, %s:%3i Std ->%4s�" % (
                i + 1, dayName, dateStr, blockTime, blockTime * self.hourlyRate
            )
            total_hours += blockTime
            if verbose:
                self.displayBlock(block, verbose)

        print "_" * 40
        totalCosts = total_hours * self.hourlyRate
        print " %s Std * %s� = %s�" % (total_hours, self.hourlyRate, totalCosts)

        print
        print "day additionals:"
        for day, factor in self.day_additionals.items():
            if day in self.statistics["day_additionals"]:
                day_time = self.statistics["day_additionals"][day]
                day_hours = day_time / 60.0 / 60.0
                day_hourly_rate = self.hourlyRate*factor
                print "\t%s: %s� * %.1f = %.2f�/Std | %.2fStd. * %.2f�/Std = %.2f�" % (
                    day,
                    self.hourlyRate, factor, day_hourly_rate,
                    day_hours, day_hourly_rate, day_hours*day_hourly_rate,
                )


    def displayPushedResults(self, exchangeRatio,
        displayMoneyOnly=False, maxDayTime=14):
        """
        Rechnet die Anzahl der Stunden pro Tag so um, das unterm Strich
        ungef�hr der gleiche Betrag, trotz eines anderen Stundenlohns
        herrauskommt.
        maxDayTime - Max. Arbeitszeit pro Tag, �berz�hlige Stunden werden auf
            den n�chten Tag "verschoben"
        """
        print
        print "-" * 40
        print ">PushedResults (exchangeRatio: %s, maxDayTime: %s)" % (
            exchangeRatio, maxDayTime
        )

        keys = self.dayData.keys()
        keys.sort()

        lastWeek = 0
        total_hours = 0

        total_addition_hours = 0
        additionals = {}

        overhang = 0
        for i, key in enumerate(keys):
            dayName = self.dayData[key]["dayName"]
            week = self.dayData[key]["week"]
            dateStr = self.dayData[key]["dateStr"]
            blockTime = self.dayData[key]["blockTime"]
            block = self.dayData[key]["block"]

            if week > lastWeek: # Leerzeile zwischen den Wochen
                print
                print "Woche: %s" % week
                lastWeek = week

            blockTime = blockTime * self.hourlyRate / exchangeRatio
            pushedTime = int(math.ceil(blockTime / 60.0 / 60.0))

            # T�gliche Abeitszeit begrenzen
            pushedTime += overhang
            if pushedTime > maxDayTime:
                overhang = pushedTime - maxDayTime
                pushedTime = maxDayTime
            else:
                overhang = 0

            if dayName in self.day_additionals:
                factor = self.day_additionals[dayName]
                additional_time = (pushedTime * factor) - pushedTime
                total_addition_hours += additional_time
                if dayName in additionals:
                    additionals[dayName] += additional_time
                else:
                    additionals[dayName] = additional_time

                additional_into = "+%.1fStd (%s Aufschlag)" % (additional_time, dayName)
            else:
                additional_into = ""

            if displayMoneyOnly:
                print "%3s - %s, %s:%4i� %s" % (
                    i + 1, dayName, dateStr, pushedTime * exchangeRatio,
                    additional_into
                )
            else:
                print "%3s - %s, %s:%3i Std %s" % (
                    i + 1, dayName, dateStr, pushedTime,
                    additional_into
                )
            total_hours += pushedTime

        if overhang > 0:
            print "-> rest overhang: %sStd !!!" % overhang

        print "_" * 79

        print
        print "day additionals:"#, additionals
        for day, factor in self.day_additionals.items():
            if day in additionals:
                day_time = additionals[day]
                day_costs = day_time * exchangeRatio
                print "\t%s: %sStd * %s� = %.2f�" % (
                    day,
                    day_time, exchangeRatio, day_time * exchangeRatio
                )

        print
        totalCosts = total_hours * exchangeRatio
        total_addition_costs = (total_hours + total_addition_hours) * exchangeRatio
        if displayMoneyOnly:
            print "Ohne Aufschlag..: %5s�" % totalCosts
            print "Mit Aufschlag...: %5s�" % total_addition_costs
        else:
            print "Ohne Aufschlag..: %s Std * %s� = %s�" % (total_hours, exchangeRatio, totalCosts)
            print "Mit Aufschlag...: %s + %s Std = %s Std * %s� = %.2f�" % (
                total_hours, total_addition_hours, (total_hours + total_addition_hours),
                exchangeRatio, total_addition_costs
            )


if __name__ == "__main__":
    import tempfile
    #~ test_path = tempfile.gettempdir()

    test_path = os.path.expanduser("~")

    #~ c = Chronologer(
        #~ projectPath     = test_path,
        #~ hourlyRate      = 80,
    #~ ).displayResults()

    c = Chronologer(
        projectPath=test_path,
        hourlyRate=80,
        maxTimeDiff=60 * 60,
        minBlockTime=55 * 60,
        projectStart=datetime.datetime(year=2005, month=3, day=1),
        projectEnd=datetime.datetime(year=2007, month=3, day=31),
    )

    print "\n" * 3, "="*79
    print "(verbose: 0)"
    c.displayResults()

    #~ print "\n" * 3, "="*79
    #~ print "(verbose: 1)"
    #~ c.displayResults(verbose=1)

    #~ print "\n" * 3, "="*79
    #~ print "(verbose: 2)"
    #~ c.displayResults(verbose=2)

    #~ print "\n" * 3, "="*79

    # Umrechnung auf anderen Stundenlohn
    c.displayPushedResults(exchangeRatio=35)
    print "\n" * 3, "="*79
    #~ c.displayPushedResults(exchangeRatio=30)
    #~ print "\n" * 3, "="*79
    #~ c.displayPushedResults(exchangeRatio=35, displayMoneyOnly=True)





