import random

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

def printChampion(champion):
    print(f"Champion object.  Tier: {champion.tier}; championNumber: {champion.championNumber}; starLevel: {champion.starLevel}")

class RollException(Exception):
    pass

class championPoolDepletedException(Exception):
    pass

#we will assume all players are at the same base level.
class Game():
    def __init__(self, summonerLevel):
        self.champPool = ChampPool()
        self.summonerLevel = summonerLevel 
        self.players = deque(Player(summonerLevel, self.champPool) for i in range(8))
        for player in self.players:
            player.setUpRandomBoard()

    def rollForUnit(self, tier):
        rolls = 0
        player = self.players[random.choice(tuple(range(8)))]
        availableChampions = player.champPool.championsAvailable(tier, 0)
        if sum(availableChampions) == 0:
            raise championPoolDepletedException(f"How did you manage to deplete an entire champion pool?  Rolls: {rolls}")
        championNumber = random.choices(self.champPool.championNumbers[tier], availableChampions)[0]
        champion = Champion(tier, championNumber, 0)
        assert type(champion) == Champion
        while not player.inShop(champion):
            rolls += 1
            player.newShop()
            if rolls > 200:
                raise RollException("Too many rolls")
        return rolls
        
class Champion():
    def __init__(self, tier, championNumber, starLevel):
        self.tier = tier
        self.championNumber = championNumber
        assert starLevel in (0,1,2)
        self.starLevel = starLevel
    def __eq__(self, other):
        return(self.tier == other.tier and self.championNumber == other.championNumber and self.starLevel == other.starLevel)

def emptyChampion():
    champion = Champion(-1,-1,0)
    return champion


class ChampPool():
    def __init__(self):
        #championNumbers dict: (champion tier):(0,1...n) where n is the number of champions in that tier.
        #this will be used to select a champion
        templist = []
        for tier in tierList:
            templist.append(tuple(champion for champion in range(origChampQuant[tier][0])))
        self.championNumbers = tuple(templist)
        
        #avilableChampions dict: (champion tier):(remaining champions left for each champion)
        #e.g., for tier 4, this will be a list of 11 champion objects, with 12 champions
        #originally available.  As champions are removed from the pool, the remaining available will change.
        self.availableChampions = deque(
            deque([origChampQuant[tier][1] for i in range(origChampQuant[tier][0])])
            for tier in tierList)

    """this function returns a tuple of champions available at the given star level"""
    def championsAvailable(self, tier, starLevel=0):
        return tuple(self.availableChampions[tier][championNumber] if self.availableChampions[tier][championNumber] > starLevelLookup[starLevel] else 0
                for championNumber in self.championNumbers[tier])
        

    """Given a summoner level, choose a tier of champion to select from"""
    def chooseTier(self, summonerLevel):
        tierOdds = champOdds[summonerLevel]
        selectedTier = random.choices(tierList,tierOdds)[0]
        return selectedTier
    """Given a summoner level, choose a champion from the champion pool.
This function will always remove one champion from the pool.  To return a
champion back to the pool, call the returnChampion function on the champion
object."""
    def selectChampion(self, summonerLevel):
        tier = self.chooseTier(summonerLevel)
        selectedChampion = random.choices(self.championNumbers[tier],self.availableChampions[tier])[0]
        self.availableChampions[tier][selectedChampion] -= 1
        return Champion(tier, selectedChampion, 0)

    """Given a champion, this will pull an appropriate amount of champions out of the pool to create that
champion on a player's board.  Used when randomly populating player benches and boards."""
    def pullChampionFromPool(self, champion):
        try:
            assert type(champion) == Champion
        except AssertionError:
            raise Exception("invalid parameter: invalid champion object")
        try:
            assert (self.availableChampions[champion.tier][champion.championNumber] >= starLevelLookup[champion.starLevel])
        except AssertionError:
            print(champion.tier)
            print(champion.championNumber)
            print(self.availableChampions[champion.starLevel])
            print(self.availableChampions[champion.tier][champion.championNumber])
            raise Exception(f"unable to remove tier {champion.starLevel+1} champion from champion list. Only {self.availableChampions[champion.tier][champion.championNumber]} champions exist in pool.")
        self.availableChampions[champion.tier][champion.championNumber] -= starLevelLookup[champion.starLevel]
        
    
    """Return a champion back to the pool."""
    def returnChampion(self, champion):
        try:
            assert type(champion) == Champion
        except AssertionError:
            raise Exception("invalid parameter: invalid champion object")
        self.availableChampions[champion.tier][champion.championNumber] += starLevelLookup[champion.starLevel]
        
        

class Player():
    def __init__(self, summonerLevel, champPool):
        self.summonerLevel = summonerLevel
        self.champPool = champPool
        #create the player board with invalid champion objects.  This is to ensure our deque objects
        #are the correct length.
        #I tried to do these all Python-ey with list comprehensions but I couldn't get it to work
        templist = []
        for i in range(summonerLevel):
            templist.append(emptyChampion())
        self.board = deque(templist)
        for i in self.board:
            assert(type(i) == Champion)
        templist = []
        for i in range(8):
            templist.append(emptyChampion())
        self.bench = deque(templist)
        for i in self.bench:
            assert(type(i) == Champion)
        templist = []
        for i in range(5):
            templist.append(emptyChampion())
        self.shop = deque(templist)
        for i in self.shop:
            assert(type(i) == Champion)

    def newShop(self):
        for champion in self.shop:
            if champion.tier > -1:
                self.champPool.returnChampion(champion)
        for i in range(len(self.shop)):
            newChampion = self.champPool.selectChampion(self.summonerLevel)
            assert(type(newChampion)==Champion)
            self.shop[i] = newChampion

    def inShop(self, champion):
        return (champion == self.shop[0] or champion == self.shop[1] or champion == self.shop[2] or
               champion == self.shop[3] or champion == self.shop[4])

    def setUpRandomBoard(self):
        #we'll assume there's a triangle-likelihood for a champion to be on a bench.
        championsOnBench = random.choices((0,1,2,3,4,5,6,7,8), (10, 13, 15, 17, 20, 17, 15, 13, 10))[0]
        #populate the player's bench with a random number of champions.  While these champions are most
        #likely to be 1 star, I don't feel like putting together another probability distribution grid.
        for i in range(championsOnBench):
            champion = self.getRandomChampion()
            self.bench[i] = champion
            self.champPool.pullChampionFromPool(champion)
        #we are ignoring FON's and giving each player a number of champions equal to his level.
        for i in range(self.summonerLevel):
            champion = self.getRandomChampion()
            self.board[i] = champion
            self.champPool.pullChampionFromPool(champion)
        

    def getRandomChampion(self):
        #we'll assume the likelihood for a champion to already be owned by a player is the same as
        #the player's likelihood to get that champion.  Not true, as some champions are widely used
        #based on a given meta.  Could update in the future.
        tierProbability = champOdds
        
        #I sort of came up with this list at random.  It's a guess at the chance to have a champion of a given star level
        #on your board
        #                   T1          T2          T3          T4          T5
        starProbability = (((100,0,0),  (0,0,0),    (0,0,0),    (0,0,0),    (0,0,0)),       #lvl 1 (100,0,0,0,0)
                           ((90,10,0),  (0,0,0),    (0,0,0),    (0,0,0),    (0,0,0)),       #lvl 2 (100,0,0,0,0)
                           ((90,10,0),  (95,5,0),   (0,0,0),    (0,0,0),    (0,0,0)),       #lvl 3 (75,25,0,0,0)
                           ((85,13,2),  (90,8,2),   (94,5,1),   (0,0,0),    (0,0,0)),       #lvl 4 (55,30,15,0,0)
                           ((80,18,2),  (80,18,2),  (90,8,2),   (99,1,0),   (0,0,0)),       #lvl 5 (45,33,20,2,0)
                           ((75,23,2),  (75,23,2),  (75,23,2),  (98,2,0),   (0,0,0)),       #lvl 6 (35,35,25,5,0)
                           ((50,47,3),  (50,47,3),  (50,47,3),  (80,20,0),  (99,1,0)),      #lvl 7 (19,35,30,15,1)
                           ((25,72,3),  (25,72,3),  (25,72,3),  (50,45,5),  (95,5,0)),      #lvl 8 (15,20,35,25,5)
                           ((25,72,3),  (25,72,3),  (25,72,3),  (50,45,5),  (89,10,1)))     #lvl 9 (10,15,30,30,15)
        
        championFound = False
        tries = 0
        errorCollection = []
        while not championFound:
            #don't want to accidentally look forever.
            tries += 1
            if tries > 10:
                print(f"game error at summoner level {self.summonerLevel}")
                for i in errorCollection:
                    print("champ odds, tier, star level, champions available:")
                    print(i)
                raise Exception("some crazy shit happened.  Figure it out ya dumbass")
            tier = random.choices(tierList, champOdds[self.summonerLevel])[0]
            starLevel = random.choices(starList, starProbability[self.summonerLevel][tier])[0]
            availableChampions = self.champPool.championsAvailable(tier, starLevel)
            
            errorCollection.append((champOdds[self.summonerLevel], tier, starLevel, availableChampions))
            #if no champions are available at the given star level, lower the star level and try again.
            #if no champions are available in the tier (very unlikely), chose a random new tier and try again.
            while sum(availableChampions) == 0 and starLevel > 0:
                starLevel -= 1
                availableChampions = self.champPool.championsAvailable(tier, starLevel)
                errorCollection.append((tier, starLevel, availableChampions))
            if starLevel >= 0:
                championNumber = random.choices(self.champPool.championNumbers[tier], availableChampions)[0]
                champion = Champion(tier, championNumber, starLevel)
                return champion

def howManyRolls(summonerLevel, tier, numgames = 400):
    assert champOdds[summonerLevel][tier] > 0
    numRolls = deque(0 for i in range(numgames))
    for i in range(numgames):
        game = Game(summonerLevel)
        try:
            result = game.rollForUnit(tier)
            numRolls[i] = result
        except RollException:
            result = 200
            numRolls[i] = result
    expectedRolls = sum(numRolls) / 1000
    print(f"At level {summonerLevel+1}, it takes {expectedRolls} rolls to find a given tier {tier+1} unit, for an expected cost of {2*expectedRolls}.")


def calculateAllProbabilities(numgames = 400):
    for summonerLevel in range(9):
        for tier in tierList:
            if champOdds[summonerLevel][tier] > 0:
                howManyRolls(summonerLevel, tier, numgames)
