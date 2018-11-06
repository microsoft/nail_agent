import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from valid_detectors.learned_valid_detector import LearnedValidDetector
from decision_module import DecisionModule
from gv import Yes, No, rng
from event import NewTransitionEvent
from util import first_sentence

class YesNo(DecisionModule):
    """
    The YesNo module listens for Yes/No questions and always outputs Yes.

    """
    def __init__(self, active=False):
        super().__init__()
        self._active = active
        self._valid_detector = LearnedValidDetector()
        self.query1 = "yes or n"
        self.query2 = "y/n"
        self.query3 = "(y or n)"

    def process_event(self, event):
        """ Process an event from the event stream. """
        if not self._active:
            return
        if type(event) is NewTransitionEvent:
            obs = event.new_obs.lower()
            if (self.query1 in obs) or (self.query2 in obs) or (self.query3 in obs):
                self._eagerness = 1.
            else:
                self._eagerness = 0.


    def take_control(self):
        """ Always answers yes """
        obs = yield
        action = rng.choice([Yes, No])
        response = yield action
        p_valid = self._valid_detector.action_valid(action, first_sentence(response))
        success = (p_valid > 0.5)
        self.record(success)
        self._eagerness = 0.
