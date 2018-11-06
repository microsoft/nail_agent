import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from valid_detectors.learned_valid_detector import LearnedValidDetector
from decision_module import DecisionModule
from action import StandaloneAction, SingleAction, DoubleAction
from gv import kg, rng, dbg
from event import *
from attribute import *
from util import first_sentence

standalone_verbs = [
    'get all', 'take all', 'drop all', 'wait', 'yes',
    'look', 'in', 'out', 'climb', 'turn on', 'turn off',
    'use', 'clap', 'get', 'dig', 'swim', 'jump',
    'drink', 'leave', 'put', 'talk', 'hop', 'buy',
    'no', 'dance', 'sleep', 'stand', 'feel', 'sit',
    'pray', 'cross', 'knock', 'open', 'pull', 'push',
    'away', 'kill', 'hide', 'pay', 'type', 'listen',
    'inventory', 'get up'
]

single_object_verbs = [
    'call', 'lock', 'smash', 'kiss', 'free',
    'answer', 'pay', 'make', 'play', 'push',
    'rewind', 'mix', 'sharpen', 'print', 'tap',
    'unlock', 'repair', 'build', 'bribe', 'chew',
    'eat', 'wear', 'think', 'cross', 'cut',
    'slide', 'walk', 'get', 'offer', 'unlight',
    'douse', 'jump', 'buy', 'off', 'remember',
    'shoot', 'oil', 'look', 'operate', 'type',
    'kill', 'clean', 'steal', 'remove', 'turn',
    'press', 'watch', 'wave', 'throw', 'search',
    'exit', 'blow', 'raise', 'cast', 'pluck',
    'unfold', 'open', 'activate', 'ride', 'set',
    'lift', 'arrest', 'pull', 'follow', 'wake',
    'talk', 'hide', 'dial', 'untie', 'start',
    'swing', 'dismount', 'catch', 'feed', 'kick',
    'part', 'inflate', 'touch', 'drink', 'hello',
    'dig', 'rub', 'hit', 'climb', 'swim', 'plug',
    'roll', 'leave', 'put', 'tear', 'break',
    'ring', 'bite', 'warm', 'give', 'say', 'sit',
    'fill', 'shake', 'take', 'enter', 'brandish',
    'light', 'show', 'chop', 'move', 'insert',
    'feel', 'fix', 'burn', 'use', 'stab', 'read',
    'close', 'examine', 'fly', 'hold', 'water',
    'load', 'tie', 'inspect', 'mount', 'empty',
    'connect', 'drop', 'go', 'lower', 'wait',
    'weigh', 'tickle', 'extinguish', 'out', 'on',
    'spray', 'wring', 'pour', 'grab', 'knock on',
    'look under', 'get all from', 'turn on', 'turn off'
]

complex_verbs = [
    ('give','to'), ('tell','to'), ('ask','about'),
    ('put','in'), ('unlock','with'), ('tie','to'),
    ('rub','with'), ('dip','in'), ('ask', 'for'),
    ('kill','with'), ('show','to'), ('chop','with'),
    ('compare','and'), ('throw','at'), ('wet','with'),
    ('get','from'), ('attack','with'), ('dig','with'),
    ('cut','with'), ('insert','in'), ('operate','on'),
    ('open','with'), ('point','at'), ('break','with')
]


class Idler(DecisionModule):
    """
    The Idler module accepts control when no others are willing to.
    """
    def __init__(self, active=False):
        super().__init__()
        self._active = active
        self._valid_detector = LearnedValidDetector()
        self._eagerness = .05


    def process_event(self, event):
        """ Process an event from the event stream. """
        pass


    def get_random_entity(self):
        """ Returns a random entity from the location or inventory. """
        if kg.player_location.entities or kg.inventory.entities:
            return rng.choice(kg.player_location.entities + kg.inventory.entities)
        return None


    def get_standalone_action(self):
        return StandaloneAction(rng.choice(standalone_verbs))


    def get_single_object_action(self):
        entity = self.get_random_entity()
        if not entity:
            return None
        verb = rng.choice(single_object_verbs)
        return SingleAction(verb, entity)


    def get_double_action(self):
        if len(kg.player_location.entities) + len(kg.inventory.entities) <= 1:
            return None
        entity1 = None
        entity2 = None
        count = 0
        while id(entity1) == id(entity2):
            if count == 100:
                return None  # Failsafe
            else:
                count += 1
            entity1 = self.get_random_entity()
            entity2 = self.get_random_entity()
        verb, prep = rng.choice(complex_verbs)
        return DoubleAction(verb, entity1, prep, entity2)


    def get_action(self):
        if not self._active:
            return StandaloneAction('look')
        n = rng.random()
        if n < .1:
            return self.get_standalone_action()
        elif n < .8:
            return self.get_single_object_action()
        else:
            return self.get_double_action()


    def take_control(self):
        obs = yield
        action = self.get_action()
        while action is None or not action.recognized():
            action = self.get_action()
        response = yield action
        p_valid = self._valid_detector.action_valid(action, first_sentence(response))
        if isinstance(action, StandaloneAction):
            kg.player_location.add_action_record(action, p_valid, response)
        elif isinstance(action, SingleAction):
            action.entity.add_action_record(action, p_valid, response)
        elif isinstance(action, DoubleAction):
            action.entity1.add_action_record(action, p_valid, response)
        success = (p_valid > 0.5)
        self.record(success)
        dbg("[IDLER]({}) p={:.2f} {} --> {}".format(
            "val" if success else "inv", p_valid, action, response))
