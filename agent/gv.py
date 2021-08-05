import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import event
import knowledge_graph
import random
import action
import attribute
import logging
import spacy

# Global RNG
rng = random.Random()

# Global logger
logger = logging.getLogger('nail')
logger.setLevel(logging.DEBUG)
dbg = logger.debug

# Global Event Stream
event_stream = event.EventStream()

# Actions that are dissallowed in any game
ILLEGAL_ACTIONS = ['restart', 'verbose', 'save', 'restore', 'score', 'quit', 'moves']

# Global Knowledge Graph
kg = knowledge_graph.KnowledgeGraph()

# Spacy NLP instance
try:
    nlp = spacy.load('en_core_web_sm')
except Exception as e:
    print("Failed to load \'en\' with exception {}. Try: python -m spacy download en_core_web_sm".format(e))
    sys.exit(1)

# Global Action Definitions
DoNothing  = action.StandaloneAction('do nothing')
Look       = action.StandaloneAction('look')
Inventory  = action.StandaloneAction('inventory')
North      = action.NavAction('north')
South      = action.NavAction('south')
East       = action.NavAction('east')
West       = action.NavAction('west')
NorthWest  = action.NavAction('northwest')
SouthWest  = action.NavAction('southwest')
NorthEast  = action.NavAction('northeast')
SouthEast  = action.NavAction('southeast')
Up         = action.NavAction('up')
Down       = action.NavAction('down')
Enter      = action.NavAction('enter')
Exit       = action.NavAction('exit')
Climb      = action.NavAction('climb')
In         = action.NavAction('in')
Out        = action.NavAction('out')
GetUp      = action.StandaloneAction('get up')
TakeAll    = action.StandaloneAction('take all')
Yes        = action.StandaloneAction('yes')
No         = action.StandaloneAction('no')
Take       = lambda x: action.TakeAction(x)
Drop       = lambda x: action.DropAction(x)
Examine    = lambda x: action.ExamineAction(x)
Eat        = lambda x: action.ConsumeAction('eat', x)
Drink      = lambda x: action.ConsumeAction('drink', x)
Swallow    = lambda x: action.ConsumeAction('swallow', x)
Consume    = lambda x: action.ConsumeAction('consume', x)
Open       = lambda x: action.OpenAction(x)
Close      = lambda x: action.CloseAction(x)
Lock       = lambda x: action.LockAction(x)
Unlock     = lambda x: action.UnlockAction(x)
LockWith   = lambda x,y: action.LockWithAction(x)
UnlockWith = lambda x,y: action.UnlockWithAction(x)
TurnOn     = lambda x: action.TurnOnAction(x)
TurnOff    = lambda x: action.TurnOffAction(x)
Light      = lambda x: action.TurnOnAction(x)
Extinguish = lambda x: action.TurnOffAction(x)
Move       = lambda x: action.SingleAction('move', x)
Push       = lambda x: action.SingleAction('push', x)
Pull       = lambda x: action.SingleAction('pull', x)
Drag       = lambda x: action.SingleAction('drag', x)
Lift       = lambda x: action.SingleAction('lift', x)
GiveTo     = lambda x,y: action.MoveItemAction('give', x, 'to', y)
PutIn      = lambda x,y: action.MoveItemAction('put', x, 'in', y)
TakeFrom   = lambda x,y: action.MoveItemAction('take', x, 'from', y)
Search     = lambda x: action.SingleAction('search', x) # TODO: Create informative action
Ask        = lambda x: action.SingleAction('ask', x)
Talk       = lambda x: action.SingleAction('talk to', x)
SayTo      = lambda x,y: action.DoubleAction('say', x, 'to', y)
Kiss       = lambda x: action.SingleAction('kiss', x)
Bribe      = lambda x: action.SingleAction('bribe', x)
BuyFrom    = lambda x,y: action.MoveItemAction('buy', x, 'from', y)
Attack     = lambda x: action.SingleAction('attack', x)
AttackWith = lambda x,y: action.DoubleAction('attack', x, 'with', y)
Kill       = lambda x: action.SingleAction('kill', x)
KillWith   = lambda x,y: action.DoubleAction('kill', x, 'with', y)

# Global Entity Attributes
Portable   = attribute.Attribute('portable',   [Take, Drop, GiveTo, PutIn, TakeFrom])
Edible     = attribute.Attribute('edible',     [Eat, Drink, Swallow, Consume])
Moveable   = attribute.Attribute('moveable',   [Move, Push, Pull, Drag, Lift])
Switchable = attribute.Attribute('switchable', [TurnOn, TurnOff])
Flammable  = attribute.Attribute('flammable',  [Light, Extinguish])
Openable   = attribute.Attribute('openable',   [Open, Close])
Lockable   = attribute.Attribute('lockable',   [Lock, Unlock, LockWith, UnlockWith])
# TODO: An Openable object may be a container. We should have logic to check for containment
Container  = attribute.Attribute('container',  [PutIn, TakeFrom, Search])
Person     = attribute.Attribute('person',     [Ask, Talk, SayTo, Kiss, Bribe, GiveTo, BuyFrom])
Enemy      = attribute.Attribute('enemy',      [Attack, AttackWith, Kill, KillWith])
