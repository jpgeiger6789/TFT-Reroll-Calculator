import random
import statistics

#I use a ton of deque objects cuz I like having a mutable list with a fixed length.
from collections import deque

tierList = (0,1,2,3,4)
starLevelLookup = (1,3,9)
starList = (0,1,2)


#champion tier:(number of champions in that tier:instances of each champion)
origChampQuant = ((13,29), (13,22), (13,18), (11,12), (8,10))

#given a summoner level, what is the likelihood to get a champion of a
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

def howManyRerolls(summonerLevel,
                   championTier,
                   championsTaken,
                   championsWanted,
                   championsMissingInTier):
    championsInTier = deque([origChampQuant[championTier][1] for i in
                   range(origChampQuant[championTier][0])])
    #we'll say the champion we want to hit is the first in the list
    championsInTier[0] -= championsTaken
    #verify enough champions remain to actually hit
    assert championsInTier[0] > championsWanted
    #remove other champions of the same Tier from the pool.  We'll
    #take one from each other champion pool until we're done.
    for i in range(championsMissingInTier):
        #we'll always start from the second champion in the pool
        #and go around until we've removed a sufficient amount, or,
        #if none remain, throw an error
        champIndex = 1 + (i % (origChampQuant[championTier][0] - 1))
        assert championsInTier[champIndex] > 0
        championsInTier[champIndex] -= 1
    championsFound = 0
    rolls = 0
    while championsWanted > championsFound:
        #make sure we don't accidentally end up in an infinite loop
        if rolls == 1000:
            print(f"Too many rolls hit.  Debugging info:")
            print(f"summonerLevel,championTier,championsTaken,championsWanted,championsMissingInTier,championsFound")
            print(f"{summonerLevel},{championTier},{championsTaken},{championsWanted},{championsMissingInTier},{championsFound}")
            print(f"champOdds")
            print(f"{champOdds[summonerLevel]}")
            raise Exception("Too many rolls")
        rolls += 1
        shopTierList = random.choices((0,1,2,3,4),champOdds[summonerLevel])
        for chosenTier in shopTierList:
            #we don't care what the shop populates when our tier isn't chosen
            if chosenTier == championTier:
                numChampions = origChampQuant[championTier][0]
                availableChampions = tuple(range(numChampions))
                championSelected = random.choices(availableChampions,championsInTier)
                #we chose the first champion as the one we're interested in
                if championSelected == 0:
                    championsFound += 1
                    championsInTier[0] -= 1
    return rolls

def runXIterations(summonerLevel,
                   championTier,
                   championsTaken,
                   championsWanted,
                   championsMissingInTier,
                   iterations):
    rolls = []
    for i in range(iterations):
        rolls.append(howManyRerolls(summonerLevel,
                   championTier,
                   championsTaken,
                   championsWanted,
                   championsMissingInTier))
    return rolls

"""
This function outputs a nested list of the following form:

Summoner Level List: length 9
[
    Champions Wanted List: length 9
    [
        Champ Tiers List: length 1-5
        depends on available tiers at summoner level
        [
            Champions Taken List: length variable depending on how many champions are in the tier
            [
                Champions Missing List: length variable depending on how many champions are in the tier
                [
                    Roll List: length = numRolls parameter
                    [
                        Roll 1 Result
                        ...
                        Roll numRolls Result
                    ]
                    ...num champions missing
                    []Roll list N
                ]
                ...num champions Taken
                []champions Missing List N
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
    summonerLevels = [[] for i in range(9)]
    #iterate through each level 1 to 9
    for (summonerLevel, summonerLevelList) in enumerate(summonerLevels):
        #iterate through champions desired - from only wanting one,
        #to three starring from scratch
        championsWantedList = [[] for i in range(9)]
        summonerLevelList.extend(championsWantedList)
        for (championsWanted, championsWantedSubList) in enumerate(championsWantedList):
            #iterate through each champ Tier
            for championTier in range(5):
                #only look at ones we can get
                if champOdds[summonerLevel][championTier] > 0:
                    champTierList = []
                    championsWantedSubList.append(champTierList)
                    numChampsinTier = origChampQuant[championTier][0]
                    champsAvailable = origChampQuant[championTier][1]
                    maxChampsTaken = champsAvailable - championsWanted
                    #iterate through each option - all available to
                    #all taken except exactly how many you want
                    champsTakenList = [[] for i in range(maxChampsTaken)]
                    champTierList.extend(champsTakenList)
                    for (championsTaken, champsTakenSubList) in enumerate(champsTakenList):
                        #sort of chose this at random
                        maxChampionsMissing = 2 * numChampsinTier
                        championsMissingList = [[] for i in range(maxChampionsMissing)]
                        champsTakenSubList.extend(championsMissingList)
                        for (championsMissingInTier, championsMissingSubList) in enumerate(championsMissingList):
                            print(f"running test.")
                            print(f"summonerLevel:{summonerLevel},championsTaken:{championsTaken},championsWanted:{championsWanted},championsMissingInTier:{championsMissingInTier},numRolls:{numRolls}")
                            championsMissingSubList.extend(
                                runXIterations(summonerLevel,
                                               championTier,
                                               championsTaken,
                                               championsWanted,
                                               championsMissingInTier,
                                               numRolls)
                                )
    return summonerLevels

def processRollResults(summonerLevels, numTests):
    fileName = r"C:\Users\OQA597\OneDrive - SUEZ\Documents\testResults.csv"
    with open(fileName, "w") as outputFile:
        outputFile.write(f"Results from {numTests} tests for each data point\n")
        outputFile.write("Summoner Level,Champion Tier,Champions Wanted,Champions Taken,Champions Missing,Average,Median,Standard Deviation\n")
        for (summonerLevel, championsWantedList) in enumerate(summonerLevels):
            for (championsWanted, champTierList) in enumerate(championsWantedList):
                for (championTier, champsTakenList) in enumerate(champTierList):
                    for (championsTaken, championsMissingList) in enumerate(champsTakenList):
                        for (championsMissingInTier, rollList) in enumerate(championsMissingList):
                            average = statistics.mean(rollList)
                            median = statistics.median(rollList)
                            stdev = statistics.stdev(rollList)
                            outputFile.write(f"{summonerLevel},{championTier},{championsWanted},{championsTaken},{championsMissingInTier},{average},{median},{stdev}\n")

def runXTests(numTests):
    rollResults = FullCalculation(numTests)
    processRollResults(rollResults)
        
                            
