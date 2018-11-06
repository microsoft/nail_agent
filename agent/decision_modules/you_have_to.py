import os, sys, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from valid_detectors.learned_valid_detector import LearnedValidDetector
from decision_module import DecisionModule
from gv import dbg, rng
from action import StandaloneAction
from event import NewTransitionEvent
from util import first_sentence

class YouHaveTo(DecisionModule):
    """
    The YouHaveTo module listens for phrases of the type You'll have to X first.

    """
    def __init__(self, active=False):
        super().__init__()
        self._active = active
        self._valid_detector = LearnedValidDetector()
        self.regexps = [
            re.compile(".*(Perhaps you should|You should|You'll have to|You'd better|You\'re not going anywhere until you) (.*) first.*"),
            re.compile(".*(You\'re not going anywhere until you) (.*)\..*"),
            re.compile(".*(You need to) (.*) before.*")
        ]


    def match(self, text):
        """ Returns the matching text if a regexp matches or empty string. """
        for regexp in self.regexps:
            match = regexp.match(text)
            if match:
                return match.group(2)
        return ''


    def process_event(self, event):
        """ Process an event from the event stream. """
        if not self._active:
            return
        if type(event) is NewTransitionEvent:
            match = self.match(event.new_obs)
            if match:
                self.act_to_do = StandaloneAction(match)
                if self.act_to_do.recognized():
                    self._eagerness = 1.


    def take_control(self):
        """ Performs the previously extracted action """
        obs = yield
        response = yield self.act_to_do
        dbg("[YouHaveTo] {} --> {}".format(self.act_to_do, response))
        p_valid = self._valid_detector.action_valid(self.act_to_do, first_sentence(response))
        success = (p_valid > 0.5)
        self.record(success)
        self._eagerness = 0.


# dm = YouHaveTo()
# print(dm.match(' You\'ll have to get out of bed first.'))
# print(dm.match(' You\'re not going anywhere until you get out of the bed. \n  '))
# print(dm.match(' You should get out of bed first.'))
# print(dm.match(' You need to be holding the green acorn before you can put it into something else.'))
# print(dm.match(' Perhaps you should examine the sign first.'))
