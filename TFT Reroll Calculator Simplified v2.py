import random
import statistics
import datetime
import os
import psutil
import sys

#I use a ton of deque objects cuz I like having a mutable list with a fixed length.
from collections import deque

tierList = (0,1,2,3,4)
starLevelLookup = (1,3,9)
starList = (0,1,2)
maxRollsBeforeCutoff = 250

#champ tier:(number of different champs in that tier:instances of each champ)
origChampQuant = ((13,29), (13,22), (13,18), (11,12), (8,10))

#given a summoner level, what is the likelihood to get a champ of a
#given tier?
#           (%T1,%T2,%T3,%T4,%T5)
champOdds = ((100,0,0,0,0),         #lvl1
             (100,0,0,0,0),         #lvl2
             (75,25,0,0,0),         #lvl3
             (55,30,15,0,0),        #lvl4
             (45,33,20,2,0),        #lvl5
             (35,35,25,5,0),        #lvl6
             (19,35,30,15,1),       #lvl7
             (15,20,35,25,5),       #lvl8
             (10,15,30,30,15))      #lvl9

class ImpossibleRollException(Exception):
    pass

def howManyRerolls(summonerLevel,
                   champTier,
                   desiredChampsTaken,
                   champsWanted,
                   otherChampsMissingInTier):
    debug = False# summonerLevel > 1
    if debug: #change to true for debugging
        print(f"Debugging info:")
        print(f"summonerLevel,champTier,desiredChampsTaken,champsWanted,otherChampsMissingInTier")
        print(f"{summonerLevel},{champTier},{desiredChampsTaken},{champsWanted},{otherChampsMissingInTier}")
    summonerOdds = champOdds[summonerLevel]
    if summonerOdds[champTier] == 0:
        raise ImpossibleRollException(f"at summoner level {summonerLevel}, cannot hit champ at tier {champTier}.  Chances are: {summonerOdds}")
    champsInTier = deque([origChampQuant[champTier][1] for i in
                   range(origChampQuant[champTier][0])])
    #we'll say the champ we want to hit is the first in the list
    champsInTier[0] -= desiredChampsTaken
    #verify enough champs remain to actually hit
    if champsInTier[0] < champsWanted:
        raise ImpossibleRollException(f"can't roll to hit a champ if there aren't enough in the pool.")
    #remove other champs of the same Tier from the pool.  We'll
    #take one from each other champ pool until we're done.
    if debug:        
        print(f"champOdds")
        print(f"{champOdds[summonerLevel]}")
        print(f"availableChampsInTier")
        print(f"{origChampQuant[summonerLevel][0]} champs in tier;{origChampQuant[summonerLevel][1]} of each champ available")
    for i in range(otherChampsMissingInTier):
        #we'll always start from the second champ in the pool
        #and go around until we've removed a sufficient amount, or,
        #if none remain, throw an error
        champIndex = 1 + (i % (origChampQuant[champTier][0] - 1))
        if debug: #change to True for debugging
            print(f"removing 1 of champ {champIndex} from pool")
            print(f"{champsInTier}")
        assert champsInTier[champIndex] > 0
        champsInTier[champIndex] -= 1
        if debug: #change to True for debugging
            print(f"{champsInTier}")
    champsFound = 0
    rolls = 0
    printonce = True
    while champsWanted > champsFound:
        #make sure we don't accidentally end up in an infinite loop
        if rolls == maxRollsBeforeCutoff:
            #for now, we'll just return maxRollsBeforeCutoff, because who cares if it's more than that
            return maxRollsBeforeCutoff
        """
            print(f"Too many rolls hit.  Debugging info:")
            print(f"summonerLevel,champTier,desiredChampsTaken,champsWanted,otherChampsMissingInTier")
            print(f"{summonerLevel},{champTier},{desiredChampsTaken},{champsWanted},{otherChampsMissingInTier}")
            print(f"champs found")
            print(f"{champsFound}")
            print(f"champOdds")
            print(f"{champOdds[summonerLevel]}")
            print(f"availableChampsInTier")
            print(f"{origChampQuant[summonerLevel][0]} champs in tier;{origChampQuant[summonerLevel][1]} of each champ available")
            print(f"remainingChamps")
            print(f"{champsInTier}")
            raise ImpossibleRollException("Too many rolls")
        """
        rolls += 1
        shopTierList = tuple(random.choices((0,1,2,3,4),summonerOdds)[0] for i in range(5))
        #print(shopTierList)
        for chosenTier in shopTierList:
            #we don't care what the shop populates when our tier isn't chosen
            if chosenTier == champTier:
                numChamps = origChampQuant[champTier][0]
                availableChamps = tuple(range(numChamps))
                champSelected = random.choices(availableChamps,champsInTier)[0]
                #we chose the first champ as the one we're interested in
                if champSelected == 0:
                    champsFound += 1
                    champsInTier[0] -= 1
    return rolls


def runXIterations(summonerLevel,
                   champTier,
                   desiredChampsTaken,
                   champsWanted,
                   otherChampsMissingInTier,
                   iterations,
                   rollList):
    for i in range(iterations):        
        rollList[i] = howManyRerolls(summonerLevel,
                   champTier,
                   desiredChampsTaken,
                   champsWanted,
                   otherChampsMissingInTier)
"""
This function outputs a nested list of the following form:
Summoner Level List: length 9
[
    Champs Wanted List: length 9
    [
        Champ Tiers List: length 1-5
        depends on available tiers at summoner level
        [
            Desired Champs Taken List: length variable depending on how many champs are in the tier
            [
                Same Tier Champs Missing List: length variable depending on how many champs are in the tier
                [
                    Roll List: length = numRolls parameter
                    [
                        Roll 1 Result
                        ...
                        Roll numRolls Result
                    ]
                    ...num champs missing
                    []Roll list N
                ]
                ...num champs Taken
                []champs Missing List N
            ]
            ...champ tiers
            []champ tier list N
        ]
        ...9
        []champ wanted list 9
    ]
    ...9
    []Summoner Level 9
]
"""

def FullCalculation(numRolls):
    #vv summoner Levels List
    summonerLevelsList = deque(
        #vv champs Wanted List vv
        deque([] for champsWanted in range(9))
        for summonerLevel in range(9))
    try:
        for summonerLevel in range(9):
            #print_memory_usage()
            #print(f"summonerLevel:{summonerLevel}")
            champsWantedList = summonerLevelsList[summonerLevel]
            for champsWanted in range(9):
                #print(f"champsWanted:{champsWanted}")
                champTierList = champsWantedList[champsWanted]
                for champTier in range(5):
                    #only look at ones we can get
                    if champOdds[summonerLevel][champTier] > 0:
                        numChampsinTier = origChampQuant[champTier][0]
                        champsAvailable = origChampQuant[champTier][1]
                        maxDesiredChampsTaken = min(champsAvailable - champsWanted, 9) #usually, not more than 9 of a champ are missing.
                        maxOtherChampsMissingInTier = 2 * numChampsinTier

                        #iterate through each option - all available to
                        #all taken except exactly how many you want
                        #vv desired champs Taken List vv
                        desiredChampsTakenList = deque(
                            #vv other champs missing in Tier list vv
                            deque(
                                #vv roll List vv
                                deque(0 for roll in range(numRolls))

                                for otherChampsMissingInTier in range(maxOtherChampsMissingInTier))
                            for desiredChampsTaken in range(maxDesiredChampsTaken))


                        champTierList.append(desiredChampsTakenList)
                        for desiredChampsTaken in range(maxDesiredChampsTaken):
                            otherChampsMissingInTierList = desiredChampsTakenList[desiredChampsTaken]
                            for otherChampsMissingInTier in range(maxOtherChampsMissingInTier):
                                rollList = otherChampsMissingInTierList[otherChampsMissingInTier]
                                #print(f"running test.")
                                #print(f"summonerLevel:{summonerLevel},champsTaken:{champsTaken},champsWanted:{champsWanted},champsMissingInTier:{champsMissingInTier},numRolls:{numRolls}")
                                runXIterations(summonerLevel,
                                                   champTier,
                                                   desiredChampsTaken,
                                                   champsWanted+1,
                                                   otherChampsMissingInTier,
                                                   numRolls,
                                                   rollList)
    except Exception as e:
        return (summonerLevelsList, e)
    return (summonerLevelsList, None)

def processRollResults(summonerLevels, numTests, outputFolder, e = None):
    if type(e) == ImpossibleRollException:
        date = datetime.datetime.now()
        fileErrorFlag = "error_" + ".".join((str(date.year), str(date.month), str(date.day), str(date.hour), str(date.minute), str(date.second)))
    else:
        fileErrorFlag = ""
    fileName = os.path.join(outputFolder, r"TFT_Test_" + str(numTests) + fileErrorFlag + "Tests.csv")
    with open(fileName, "w+") as outputFile:
        outputFile.write(f"Results from {numTests} tests for each data point; cutoff value {maxRollsBeforeCutoff}\n")
        quantileList = [9,19,29,39,49,59,69,79,89,94,97,98]
        outputFile.write(f"Sum Level,Champ Tier,Champs Wanted,Desired Champs Taken,Other Champs Missing In Tier,Avg,Median,Std Dev," + ",".join("Q " + str(quantileList[i] + 1)for i in range(len(quantileList))) + f",max,# of {maxRollsBeforeCutoff} rolls\n")
        for (summonerLevel, champsWantedList) in enumerate(summonerLevels):
            for (champsWanted, champTierList) in enumerate(champsWantedList):
                for (champTier, desiredChampsTakenList) in enumerate(champTierList):
                    for (desiredChampsTaken, otherChampsMissingInTierList) in enumerate(desiredChampsTakenList):
                        for (otherChampsMissingInTier, rollList) in enumerate(otherChampsMissingInTierList):
                            average = statistics.mean(rollList)
                            median = statistics.median(rollList)
                            stdev = statistics.stdev(rollList)
                            quantiles = statistics.quantiles(rollList,n=100,method="inclusive")
                            maxVal = max(rollList)
                            numMaxRolls = rollList.count(maxRollsBeforeCutoff)
                            outputFile.write(f"{summonerLevel+1},{champTier+1},{champsWanted+1},{desiredChampsTaken},{otherChampsMissingInTier},{average},{median},{stdev}," + ",".join(str(quantiles[i]) for i in quantileList) + f",{maxVal},{numMaxRolls}\n")

def runXTests(numTests):
    outputFolder = r"C:\Users\OQA597\OneDrive - SUEZ\Documents"
    if not os.path.exists(outputFolder):
        raise Exception(f"Folder {outputFolder} does not exist")
    if numTests < 2:
        raise Exception("cannot do statistics with a sample size less than 2")
    result = FullCalculation(numTests)
    rollResults = result[0]
    #print(len(rollResults))
    e = result[1]
    #for now during debugging, I want to process Roll Results
    if e == None or type(e) == ImpossibleRollException:
        processRollResults(rollResults, numTests, outputFolder, e)
    else:
        raise Exception(e)


def timeTests(maxTests):
    if maxTests < 2:
        raise Exception("must run more than 2 tests")
    for i in range(2,maxTests+1,2):
        startTime = datetime.datetime.now()
        runXTests(i)
        endTime = datetime.datetime.now()
        deltaTime = endTime - startTime
        print(f"Time to run {i} tests: {deltaTime}")

#https://airbrake.io/blog/python/memoryerror
def print_memory_usage():
    """Prints current memory usage stats.
    See: https://stackoverflow.com/a/15495136

    :return: None
    """
    import os
    import psutil
    import sys
    import traceback

    PROCESS = psutil.Process(os.getpid())
    MEGA = 10 ** 6 #information will be shown as megabytes
    total, available, percent, used, free = psutil.virtual_memory()
    total, available, used, free = int(total / MEGA), int(available / MEGA), int(used / MEGA), int(free / MEGA)
    proc = int(PROCESS.memory_info()[1] / MEGA)
    print(f"process = {proc} MB total = {total} MB available = {available} MB used = {used} MB free = {free} MB percent = {percent} MB")
