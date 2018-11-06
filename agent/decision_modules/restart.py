import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from decision_module import DecisionModule
from gv import dbg, kg
from action import StandaloneAction
from event import NewTransitionEvent

class Restart(DecisionModule):
    """
    The Restart module listens for a game over and will restart the game.

    """
    def __init__(self, active=False):
        super().__init__()
        self._active = active


    def process_event(self, event):
        """ Process an event from the event stream. """
        if not self._active:
            return
        if type(event) is NewTransitionEvent:
            if 'RESTART' in event.new_obs and \
               'RESTORE' in event.new_obs and \
               'QUIT' in event.new_obs:
                self._eagerness = 1.
            if 'You have died' in event.new_obs:
                self._eagerness = 1.


    def take_control(self):
        """ Performs the previously extracted action """
        obs = yield
        dbg("[RESTART] Restarting Game")
        action = StandaloneAction("IEEECIG-ADVENT-RESTART-COMMAND")
        response = yield action
        kg.reset()
        self._eagerness = 0.
