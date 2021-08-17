import random
import statistics
import datetime
import os
import psutil
import multiprocessing as mp
import traceback
import ctypes
# I use a ton of deque objects cuz I like having a mutable list with a fixed length.
from collections import deque
from pathlib import Path

smallBatch = False
callerDebug = False
subProcessDebug = False

tierList = (0, 1, 2, 3, 4)
starLevelLookup = (1, 3, 9)
starList = (0, 1, 2)
maxRollsBeforeCutoff = 250

# champ tier:(number of different champs in that tier:instances of each champ)
origChampQuant = ((13, 29), (13, 22), (13, 18), (11, 12), (8, 10))

# given a summoner level, what is the likelihood to get a champ of a
# given tier?
#           (%T1,%T2,%T3,%T4,%T5)
champOdds = ((100, 0, 0, 0, 0),  # lvl1
             (100, 0, 0, 0, 0),  # lvl2
             (75, 25, 0, 0, 0),  # lvl3
             (55, 30, 15, 0, 0),  # lvl4
             (45, 33, 20, 2, 0),  # lvl5
             (25, 40, 30, 5, 0),  # lvl6
             (19, 30, 35, 15, 1),  # lvl7
             (15, 20, 35, 25, 5),  # lvl8
             (10, 15, 30, 30, 15))  # lvl9


class ImpossibleRollException(Exception):
    pass


def howManyRerolls(summonerLevel: int,
                   champTier: int,
                   desiredChampsTaken: int,
                   champsWanted: int,
                   otherChampsMissingInTier: int) -> tuple[int, str, str]:
    global callerDebug
    debugInfo = ""
    exceptionLog = ""
    rolls = -1
    try:
        if callerDebug:
            debugInfo += f"howManyRerolls callerDebugging info:\n"
            debugInfo += f"summonerLevel,champTier,desiredChampsTaken,champsWanted,otherChampsMissingInTier\n"
            debugInfo += f"{summonerLevel},{champTier},{desiredChampsTaken},{champsWanted},{otherChampsMissingInTier}\n"
        summonerOdds = champOdds[summonerLevel]
        if summonerOdds[champTier] == 0:
            raise ImpossibleRollException(
                f"at summoner level {summonerLevel}, cannot hit champ at tier {champTier}.  Chances are: {summonerOdds}")
        champsInTier = deque([origChampQuant[champTier][1] for i in
                              range(origChampQuant[champTier][0])])
        # we'll say the champ we want to hit is the first in the list
        champsInTier[0] -= desiredChampsTaken
        # verify enough champs remain to actually hit
        if champsInTier[0] < champsWanted:
            raise ImpossibleRollException(f"can't roll to hit a champ if there aren't enough in the pool.")
        # remove other champs of the same Tier from the pool.  We'll
        # take one from each other champ pool until we're done.
        if callerDebug:
            debugInfo += f"champOdds\n"
            debugInfo += f"{champOdds[summonerLevel]}\n"
            debugInfo += f"availableChampsInTier\n"
            debugInfo += f"{origChampQuant[champTier][0]} champs in tier;{origChampQuant[champTier][1]} of each champ available\n"
        for i in range(otherChampsMissingInTier):
            # we'll always start from the second champ in the pool
            # and go around until we've removed a sufficient amount, or,
            # if none remain, throw an error
            champIndex = 1 + (i % (origChampQuant[champTier][0] - 1))
            if callerDebug:  # change to True for callerDebugging
                print(f"removing 1 of champ {champIndex} from pool")
                print(f"{champsInTier}")
            assert champsInTier[champIndex] > 0
            champsInTier[champIndex] -= 1
            if callerDebug:  # change to True for callerDebugging
                print(f"{champsInTier}")
        champsFound = 0
        rolls = 0
        printOnce = True
        while champsWanted > champsFound:
            # make sure we don't accidentally end up in an infinite loop
            if rolls == maxRollsBeforeCutoff:
                # for now, we'll just return maxRollsBeforeCutoff, because who cares if it's more than that
                raise BreakException("")
            rolls += 1
            shopTierList = tuple(random.choices((0, 1, 2, 3, 4), summonerOdds)[0] for i in range(5))
            # print(shopTierList)
            for chosenTier in shopTierList:
                # we don't care what the shop populates when our tier isn't chosen
                if chosenTier == champTier:
                    numChamps = origChampQuant[champTier][0]
                    availableChamps = tuple(range(numChamps))
                    champSelected = random.choices(availableChamps, champsInTier)[0]
                    # we chose the first champ as the one we're interested in
                    if champSelected == 0:
                        champsFound += 1
                        champsInTier[0] -= 1
    except BreakException:
        pass
    except Exception as e:
        exceptionLog = log_exception(e)
    finally:
        return (rolls, debugInfo, exceptionLog)


class BreakException(Exception):
    pass


def runXIterations(summonerLevel: int,
                   champTier: int,
                   desiredChampsTaken: int,
                   champsWanted: int,
                   otherChampsMissingInTier: int,
                   iterations: int,
                   rollList: deque[int]) -> tuple[str, str]:
    debugInfo = ""
    exceptionInfo = ""
    iterationDebugInfo = ""
    try:
        if callerDebug: debugInfo += \
            f"runXIterations: summonerLevel:{summonerLevel}, champTier:{champTier}, " \
            f"desiredChampsTaken:{desiredChampsTaken}, champsWanted:{champsWanted}, " \
            f"otherChampsMissingInTier:{otherChampsMissingInTier}, iterations:{iterations}, " \
            f"rollList: list of length {len(rollList)}"
        for i in range(iterations):
            rollList[i], rerollDebugInfo, rerollExceptionInfo = howManyRerolls(summonerLevel,
                                                                               champTier,
                                                                               desiredChampsTaken,
                                                                               champsWanted,
                                                                               otherChampsMissingInTier)

            # we'll only return one iteration of debug info, otherwise it gets way too big
            if subProcessDebug and iterationDebugInfo == "":
                iterationDebugInfo += rerollDebugInfo
            exceptionInfo += rerollExceptionInfo
            if rerollExceptionInfo != "":
                raise BreakException("")
    except BreakException:
        pass
    except Exception as e:
        exceptionInfo += log_exception(e)
    finally:
        return (debugInfo + iterationDebugInfo, exceptionInfo)


"""
class rollResultsObject():
    def __init__(self,summonerLevel: int, champsWanted: int, champTierResults: list, exceptionLog: str = ""):
        global callerDebug
        
        if callerDebug:
            exceptionExists = exceptionLog==""
            print(f"rollResultsObject instantiation: {summonerLevel}:summonerLevel, {champsWanted}:champsWanted, champTierList:List of len {len(champTierResults)}, exception raised?:{exceptionExists}")
        self.summonerLevel = summonerLevel
        self.champsWanted = champsWanted
        self.champTierResults = champTierResults
        self.descriptor = f"summonerLevel:{summonerLevel}; champsWanted:{champsWanted}; champTierResults length:{len(champTierResults)}"
        if exceptionLog != "":
            self.exceptionLog =  + exceptionLog
        else:
            self.exceptionLog = ""
"""


def MultiProcessCalculation(numTests: int) -> deque[deque[list[list[list[deque[float]]]]]]:
    """
    This function outputs a nested list of the following form:
    Summoner Level List: deque length 9
    [
        Champs Wanted List: deque length 9
        [
            Champ Tiers List: list length 1-5
            depends on available tiers at summoner level
            [
                Desired Champs Taken List: list; length variable depending on how many champs are in the tier
                [
                    Same Tier Champs Missing List: list; length variable depending on how many champs are in the tier
                    [
                        Roll List: deque length = numTests parameter
                        [
                            Roll 1 Result
                            ...
                            Roll numTests Result
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

    global callerDebug
    # if callerDebug: print(f"MultiProcessCalculation numTests:{numTests}")
    stopAfterTwo = 0
    num_workers = mp.cpu_count()
    # the num_workers parameter is extraneous, as that is the default.
    # Leaving it to make it explicit what is happening (and so we can mess around with this number).

    # vv summoner Levels List
    rollResultsList = deque(
        # vv champs Wanted List vv
        deque([] for champsWanted in range(9))
        for summonerLevel in range(9))
    poolArgs = []
    for summonerLevel in range(9):
        # if callerDebug: print_memory_usage()
        for champsWanted in range(9):
            if callerDebug:
                stopAfterTwo += 1
            poolArgs.append((summonerLevel, champsWanted, numTests))
            if callerDebug and stopAfterTwo == 2:
                break
    if callerDebug: print(f"creating worker pool.")
    # ----------------------------------------------------------------------------------------------------------------------------------------------
    with mp.Pool(num_workers) as pool:
        if subProcessDebug:
            print(f"starting asynchronous results calculation subprocesses.")
        AsyncResultList = [pool.apply_async(workerProcessCalculation, args) for args in poolArgs]
        results = [ASResult.get() for ASResult in AsyncResultList]
    # ----------------------------------------------------------------------------------------------------------------------------------------------
    # num_workers processes have been started, which will return 81 results.  Now, to wait for them.
    if subProcessDebug:
        print("Roll calculations complete.  Re-arranging and compiling results.")
    printOnce = True
    for result in results:
        if printOnce and callerDebug:
            print("processing result")
        # resultsObject = (summonerLevel, champsWanted, champTierResults, exceptionLog)
        summonerLevel = result[0]
        champsWanted = result[1]
        champTierResults = result[2]
        exceptionLog = result[3]
        if printOnce and exceptionLog != "":
            print("One or more exceptions were encountered.  Exception information:")
            print(exceptionLog)
        debugInfo = result[4]
        if printOnce and subProcessDebug:
            print(debugInfo)
            printOnce = False
        rollResultsList[summonerLevel][champsWanted] = champTierResults
    if callerDebug:
        print("returning results list")
    return rollResultsList


# ----------------------------------------------------------------------------------------------------------------------------------------------

def workerProcessCalculation(summonerLevel: int, champsWanted: int, numTests: int):
    global subProcessDebug
    debugInfo = ""
    exceptionInfo = ""
    workerDebugInfo = ""
    exceptionLog = ""
    champTierResults = []
    try:
        if subProcessDebug and workerDebugInfo == "": workerDebugInfo += \
            f"workerProcessCalculation: summonerLevel:{summonerLevel}, champsWanted:{champsWanted}, " \
                f"numTests:{numTests}"
        for champTier in range(5):
            # only look at ones we can get
            if champOdds[summonerLevel][champTier] > 0:
                numChampsInTier = origChampQuant[champTier][0]
                champsAvailable = origChampQuant[champTier][1]
                # iterate through every available option - from none missing to
                # exactly enough remaining to get the number you want

                champsLikelyOwned = 9 - champsWanted
                maxDesiredChampsTaken = min(champsAvailable - champsWanted,
                                            12 + champsLikelyOwned)
                # we'll look at up to 12 missing champions in enemy pools (4x 2 star champions) +
                # the number of champions you would own if you were going for a 3-star

                countBy = 4

                # iterate through each option - all available to
                # all taken except exactly how many you want
                # vv desired champs Taken List vv
                desiredChampsTakenList = deque(
                    # vv other champs missing in Tier list vv
                    deque(
                        # vv roll List vv
                        deque(0 for roll in range(numTests))

                        for otherChampsMissingInTier in range(20 - (summonerLevel // 2)))
                    for desiredChampsTaken in range(maxDesiredChampsTaken))

                champTierResults.append(desiredChampsTakenList)
                for desiredChampsTaken in range(maxDesiredChampsTaken):
                    otherChampsMissingInTierList = desiredChampsTakenList[desiredChampsTaken]
                    for otherChampsMissingInTier_unedited in range(20 - (summonerLevel // 2)):
                        rollList = otherChampsMissingInTierList[otherChampsMissingInTier_unedited]
                        otherChampsMissingInTier = otherChampsMissingInTier_unedited * countBy
                        # if subProcessDebug: debugInfo += f"running test."
                        # if subProcessDebug: debugInfo +=
                        # f"summonerLevel:{summonerLevel},desiredChampsTaken:{desiredChampsTaken}," \
                        # f"champsWanted:{champsWanted},otherChampsMissingInTierList:{otherChampsMissingInTierList}," \
                        # f"countBy:{countBy},numTests:{numTests}"
                        iterationDebugInfo, iterationExceptionInfo = \
                            runXIterations(summonerLevel,
                                           champTier,
                                           desiredChampsTaken,
                                           champsWanted + 1,
                                           otherChampsMissingInTier,
                                           numTests,
                                           rollList)
                        if subProcessDebug and debugInfo == "": debugInfo += iterationDebugInfo
                        exceptionInfo += iterationExceptionInfo
                        if iterationExceptionInfo != "":
                            raise BreakException("")
    except BreakException:
        pass
    except Exception as e:
        exceptionLog = log_exception(e)
    finally:
        exceptionInfo += exceptionLog
        # ----------------------------------------------------------------------------------------------------------------------------------------------
        result = (summonerLevel, champsWanted, champTierResults, exceptionInfo, workerDebugInfo + debugInfo)
        return result


# ----------------------------------------------------------------------------------------------------------------------------------------------

""""
class statisticsResultsObject():
    def __init__(self,summonerLevel: int, champsWanted: int, champTierResults: list):
        global callerDebug
        
        if callerDebug:
            print(f"statisticsResultsObject instantiation: {summonerLevel}:summonerLevel, {champsWanted}:champsWanted, champTierList:List of length {len(champTierList)}")
        self.summonerLevel = summonerLevel
        self.champsWanted = champsWanted
        self.champTierResults = champTierResults
        self.descriptor = f"statisticsResultsObject: {summonerLevel}:summonerLevel, {champsWanted}:champsWanted, champTierList:List of length {len(champTierList)}"
"""


def collectRollStatisticsMultiProcess(
        rollResultsList: deque[deque[list[list[list[deque[float]]]]]], numTests: int) \
        -> deque[deque[list[[deque[deque[str]]]]]]:
    global callerDebug
    if callerDebug: print(
        f"collectRollStatisticsMultiProcess: rollResultsList: list of length {len(rollResultsList)}, "
        f"numTests: {numTests}")
    stopAfterTwo = 0
    num_workers = mp.cpu_count()
    # the num_workers parameter is extraneous, as that is the default.
    # Leaving it to make it explicit what is happening (and so we can mess around with this number).

    # vv summoner Levels List
    rollStatisticsList: deque[deque[list[deque[deque[str]]]]]
    rollStatisticsList = deque(
        # vv champs Wanted List vv
        deque([] for champsWanted in range(9))
        for summonerLevel in range(9))
    poolArgs: list[tuple[list[list[list[deque[float]]]], int, int, int]]
    poolArgs = []
    summonerLevel: int
    champsWantedList: deque[list[list[list[deque[float]]]]]
    for (summonerLevel, champsWantedList) in enumerate(rollStatisticsList):
        champsWanted: int
        champTierRollResultsList: list[list[list[deque[float]]]]
        # don't need champTierRollResultsList but it looks nicer this way
        for (champsWanted, champTierRollResultsList) in enumerate(champsWantedList):
            if callerDebug: stopAfterTwo += 1
            champTierRollResultsList = rollResultsList[summonerLevel][champsWanted]
            poolArgs.append((champTierRollResultsList, summonerLevel, champsWanted, numTests))
            if callerDebug and stopAfterTwo == 2:
                break
    # ------------------------------------------------------------------------------------------------------
    with mp.Pool(processes=num_workers) as pool:
        if subProcessDebug: print(f"starting asynchronous results calculation subprocesses.")
        AsyncResultList = [pool.apply_async(workerProcessRollResults, args) for args in poolArgs]
        results: list[tuple[int, int, list[deque[deque[str]]], str, str]]
        results = [ASResult.get() for ASResult in AsyncResultList]
    # ------------------------------------------------------------------------------------------------------
    if subProcessDebug: print("Roll calculations complete.  Re-arranging and compiling results.")
    printOnce = True
    for result in results:
        if printOnce and callerDebug: print("processing result")
        # rollStatisticsList[result.summonerLevel][result.champsWanted] = result.champTierResults
        # resultsObject = (summonerLevel, champsWanted, champTierResults)
        summonerLevel = result[0]
        champsWanted = result[1]
        champTierResults = result[2]
        if printOnce and callerDebug:
            print(f"summonerLevel:{summonerLevel},champsWanted:{champsWanted}")
        exceptionLog = result[3]
        debugInfo = result[4]
        if printOnce and subProcessDebug:
            print(f"debuginfo:\n{debugInfo}")
        rollStatisticsList[summonerLevel][champsWanted] = champTierResults
        if printOnce and exceptionLog != "":
            print(exceptionLog)
        printOnce = False
    if callerDebug: print("returning results list")
    return rollStatisticsList


def workerProcessRollResults(champTierRollResultsList: deque[deque[deque[deque[int]]]],
                             summonerLevel: int,
                             champsWanted: int,
                             numTests: int) -> tuple[int, int, list[deque[deque[str]]], str, str]:
    global subProcessDebug
    debugInfo = ""
    exceptionLog = ""
    champTierResults = []
    if subProcessDebug:
        debugInfo = f"workerProcessRollResults: champTierRollResultsList:List of length "
        f"{len(champTierRollResultsList)}, summonerLevel:{summonerLevel}, champsWanted: {champsWanted}, "
        f"numTests:{numTests}\n"
    try:
        printOnce = True
        champTier: int
        desiredChampsTakenResultsList: deque[deque[deque[int]]]
        for (champTier, desiredChampsTakenResultsList) in enumerate(champTierRollResultsList):
            numChampsinTier = origChampQuant[champTier][0]
            champsAvailable = origChampQuant[champTier][1]
            # iterate through every available option - from none missing to exactly enough remaining to get
            # the number you want
            maxDesiredChampsTaken = champsAvailable - champsWanted
            # we're going to go by multiples of 3 here -
            # we will always have 10 data points.  This is to minimize file size.
            countBy = 3

            # iterate through each option - all available to
            # all taken except exactly how many you want
            # vv desired champs Taken List vv
            desiredChampsTakenStatisticsList = deque(
                # vv other champs missing in Tier list vv
                deque("" for otherChampsMissingInTier in range(20 - (summonerLevel // 2)))
                for desiredChampsTaken in range(maxDesiredChampsTaken))
            champTierResults.append(desiredChampsTakenStatisticsList)
            desiredChampsTaken: int
            otherChampsMissingInTierList: deque[deque[int]]
            for (desiredChampsTaken, otherChampsMissingInTierList) in enumerate(desiredChampsTakenResultsList):
                otherChampsMissingInTier_unedited: int
                rollList: deque[int]
                for (otherChampsMissingInTier_unedited, rollList) in enumerate(otherChampsMissingInTierList):
                    otherChampsMissingInTier = otherChampsMissingInTier_unedited * countBy
                    average = statistics.mean(rollList)
                    median = statistics.median(rollList)
                    stdDev = statistics.stdev(rollList)
                    quantiles = statistics.quantiles(rollList, n=100, method="inclusive")
                    quantileList = [9, 19, 29, 39, 49, 59, 69, 79, 89, 94, 97, 98]
                    maxVal = max(rollList)
                    numMaxRolls = rollList.count(maxRollsBeforeCutoff)
                    result = f"{summonerLevel + 1},{champTier + 1},{champsWanted + 1},{desiredChampsTaken}," \
                             f"{otherChampsMissingInTier},{average},{median},{stdDev}," + \
                             ",".join(str(quantiles[i]) for i in quantileList) + f",{maxVal},{numMaxRolls}\n"
                    if printOnce and subProcessDebug:
                        debugInfo += f"Result: {result}\n"
                        printOnce = False
                    champTierResults[champTier][desiredChampsTaken][otherChampsMissingInTier_unedited] = result
    except Exception as e:
        exceptionLog = log_exception(e)
    finally:
        # ----------------------------------------------------------------------------------------------------------------------------------------------
        result = (summonerLevel, champsWanted, champTierResults, exceptionLog, debugInfo)
        return result


# ----------------------------------------------------------------------------------------------------------------------------------------------

def printStatisticsToFile(rollStatisticsList: deque, numTests: int, outputFolder: str):
    global callerDebug
    if callerDebug: print(
        f"printStatisticsToFile: rollStatisticsList: List of length {len(rollStatisticsList)}, "
        f"numTests: {numTests}, outputFolder: {outputFolder}")

    tsDateTime = datetime.datetime.now()
    timestamp = f"{tsDateTime.year}.{tsDateTime.month:02}.{tsDateTime.day:02}...{tsDateTime.hour:02}.{tsDateTime.minute:02}.{tsDateTime.second:02}"

    fileName = os.path.join(outputFolder, r"TFT_Test_" + str(numTests) + f"Tests {timestamp}.csv")
    with open(fileName, "w+") as outputFile:
        outputFile.write(f"Results from {numTests} tests for each data point; cutoff value "
                         f"{maxRollsBeforeCutoff}\n")
        quantileList = [9, 19, 29, 39, 49, 59, 69, 79, 89, 94, 97, 98]
        outputFile.write("Sum Level,Champ Tier,Champs Wanted,Desired Champs Taken,Other Champs Missing In Tier,"
                         "Avg,Median,Std Dev," +
                         ",".join("Q " + str(quantileList[i] + 1) for i in range(len(quantileList))) +
                         f",max,# of {maxRollsBeforeCutoff} rolls\n")
        for (summonerLevel, champsWantedList) in enumerate(rollStatisticsList):
            for (champsWanted, champTierList) in enumerate(champsWantedList):
                for (champTier, desiredChampsTakenList) in enumerate(champTierList):
                    for (desiredChampsTaken, otherChampsMissingInTierList) in enumerate(desiredChampsTakenList):
                        for (otherChampsMissingInTier_unedited, result) in enumerate(otherChampsMissingInTierList):
                            outputFile.write(result)


def runXTests(numTests: int):
    myComputerIsNowAnInsomniac()
    global callerDebug
    if callerDebug: print(f"runXTests numTests:{numTests}")
    outputFolder = str(Path.home() / "Downloads")
    if not os.path.exists(outputFolder):
        raise Exception(f"Folder {outputFolder} does not exist")
    if numTests < 2:
        raise Exception(f"numTests ({numTests}) cannot be less than 2.")
    rollResultsList: deque[deque[list[list[list[deque[float]]]]]]
    rollResultsList = MultiProcessCalculation(numTests)
    if callerDebug: print("-" * 40 + "\n")
    if callerDebug: print("ROLL RESULTS FINISHED")
    if callerDebug: print("-" * 40 + "\n")
    rollStatisticsList: deque[deque[list[list[list[deque[str]]]]]]
    rollStatisticsList = collectRollStatisticsMultiProcess(rollResultsList, numTests)
    if callerDebug: print("-" * 40 + "\n")
    if callerDebug: print("STATISTICAL ANALYSIS FINISHED")
    if callerDebug: print("-" * 40 + "\n")
    printStatisticsToFile(rollStatisticsList, numTests, outputFolder)
    youWorkedHardLittleComputerNowYouMaySleep()


def timeTests(maxTests: int, minTests: int = 2):
    global callerDebug
    if callerDebug: print(f"timeTests maxTests:{maxTests}")
    if maxTests < 2 or minTests < 2:
        raise Exception("must run more than 2 tests")
    for i in range(minTests, maxTests + 1, 2):
        startTime = datetime.datetime.now()
        runXTests(i)
        endTime = datetime.datetime.now()
        deltaTime = endTime - startTime
        print(f"Time to run {i} tests: {deltaTime}")


# https://airbrake.io/blog/python/memoryerror
def print_memory_usage():
    """Prints current memory usage stats.
    See: https://stackoverflow.com/a/15495136

    :return: None
    """
    global callerDebug
    if callerDebug: print("print_memory_usage()")
    PROCESS = psutil.Process(os.getpid())
    MEGA = 10 ** 6  # information will be shown as megabytes
    total, available, percent, used, free = psutil.virtual_memory()
    total, available, used, free = int(total / MEGA), int(available / MEGA), int(used / MEGA), int(free / MEGA)
    proc = int(PROCESS.memory_info()[1] / MEGA)
    print(
        f"process = {proc} MB total = {total} MB available = {available} MB used = {used} MB free = {free} "
        f":MB percent = {percent} MB")


def log_exception(exception: Exception):
    """Prints the passed BaseException to the console, including traceback.

    :param exception: The BaseException to output.
    """
    global callerDebug
    if callerDebug: print(f"log_exception()")
    exceptionTraceback = "".join(traceback.extract_tb(exception.__traceback__).format())
    output = f"{type(exception).__name__}: {exception}\nTraceback:\n{exceptionTraceback}"
    return output


# https://stackoverflow.com/questions/57647034/prevent-sleep-mode-python-wakelock-on-python
def myComputerIsNowAnInsomniac():
    setState("wake")

def youWorkedHardLittleComputerNowYouMaySleep():
    setState("sleep")


"""
SetThreadExecutionState function (winbase.h)

    12/05/2018
    3 minutes to read

Enables an application to inform the system that it is in use, thereby preventing the system from 
entering sleep or turning off the display while the application is running.
Syntax
C++

EXECUTION_STATE SetThreadExecutionState(
  EXECUTION_STATE esFlags
);

Parameters

esFlags

The thread's execution requirements. This parameter can be one or more of the following values.
Parameters
Value 	Meaning

ES_AWAYMODE_REQUIRED
0x00000040

	Enables away mode. This value must be specified with ES_CONTINUOUS.

Away mode should be used only by media-recording and media-distribution applications that must perform 
critical background processing on desktop computers while the computer appears to be sleeping. See Remarks.

ES_CONTINUOUS
0x80000000

	Informs the system that the state being set should remain in effect until the next call that uses 
	ES_CONTINUOUS and one of the other state flags is cleared.

ES_DISPLAY_REQUIRED
0x00000002

	Forces the display to be on by resetting the display idle timer.

ES_SYSTEM_REQUIRED
0x00000001

	Forces the system to be in the working state by resetting the system idle timer.

ES_USER_PRESENT
0x00000004

	This value is not supported. If ES_USER_PRESENT is combined with other esFlags values, the call will 
	fail and none of the specified states will be set. 
	
	Return value

If the function succeeds, the return value is the previous thread execution state.

If the function fails, the return value is NULL.
Remarks

The system automatically detects activities such as local keyboard or mouse input, server activity, 
and changing window focus. Activities that are not automatically detected include disk or CPU activity 
and video display.

Calling SetThreadExecutionState without ES_CONTINUOUS simply resets the idle timer; to keep the display
 or system in the working state, the thread must call SetThreadExecutionState periodically.

To run properly on a power-managed computer, applications such as fax servers, answering machines, 
backup agents, and network management applications must use both ES_SYSTEM_REQUIRED and ES_CONTINUOUS 
when they process events. Multimedia applications, such as video players and presentation applications, 
must use ES_DISPLAY_REQUIRED when they display video for long periods of time without user input. Applications
 such as word processors, spreadsheets, browsers, and games do not need to call SetThreadExecutionState.

The ES_AWAYMODE_REQUIRED value should be used only when absolutely necessary by media applications that 
require the system to perform background tasks such as recording television content or streaming media to 
other devices while the system appears to be sleeping. Applications that do not require critical background 
processing or that run on portable computers should not enable away mode because it prevents the system from 
conserving power by entering true sleep.

To enable away mode, an application uses both ES_AWAYMODE_REQUIRED and ES_CONTINUOUS; to disable away mode, 
an application calls SetThreadExecutionState with ES_CONTINUOUS and clears ES_AWAYMODE_REQUIRED. When away 
mode is enabled, any operation that would put the computer to sleep puts it in away mode instead. The computer 
appears to be sleeping while the system continues to perform tasks that do not require user input. Away mode does 
not affect the sleep idle timer; to prevent the system from entering sleep when the timer expires, an application 
must also set the ES_SYSTEM_REQUIRED value.

The SetThreadExecutionState function cannot be used to prevent the user from putting the computer to sleep.
Applications should respect that the user expects a certain behavior when they close the lid on their laptop 
or press the power button.

This function does not stop the screen saver from executing.
"""
def setState(state):
    validStates = "wake", "sleep"
    if state not in validStates:
        raise ValueError(f"setState: state must be one of {validStates}")
    ES_AWAYMODE_REQUIRED = 0x00000040
    ES_CONTINUOUS = 0x80000000
    ES_DISPLAY_REQUIRED = 0x00000002
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_USER_PRESENT = 0x00000004
    if state == "wake":
        wakeState = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(wakeState)
    if state == "sleep":
        sleepState = ES_CONTINUOUS
        ctypes.windll.kernel32.SetThreadExecutionState(sleepState)
