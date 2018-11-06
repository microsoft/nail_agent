import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from valid_detectors.learned_valid_detector import LearnedValidDetector
from decision_module import DecisionModule
from gv import dbg, rng
from action import StandaloneAction
from event import NewTransitionEvent
from util import first_sentence

class Darkness(DecisionModule):
    """
    The Darkness module listens for phrases like 'it's pitch black' and tries to turn on a light.

    """
    def __init__(self, active=False):
        super().__init__()
        self._active = active
        self._valid_detector = LearnedValidDetector()
        self.queries = ['pitch black', 'too dark to see']

    def process_event(self, event):
        """ Process an event from the event stream. """
        if not self._active:
            return
        if type(event) is NewTransitionEvent:
            if any(query in event.new_obs for query in self.queries):
                self._eagerness = 1.


    def take_control(self):
        """ Performs the previously extracted action """
        obs = yield
        action = StandaloneAction('turn on')
        response = yield action
        p_valid = self._valid_detector.action_valid(action, first_sentence(response))
        success = (p_valid > 0.5)
        self.record(success)
        self._eagerness = 0.
