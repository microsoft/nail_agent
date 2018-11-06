from abc import ABC, abstractmethod
import gv

class DecisionModule(ABC):
    """
    A Decision Module processes events and takes actions. A module also needs
    to monitor events and report how eager it is to take control of the decision
    making.

    Decision Modules are generators - that generate sequences of actions
    conditioned on observations. A module in control remains in control until it
    stops generating actions, at which point the most eager module takes over.

    """
    def __init__(self):
        self._eagerness = 0.
        self._succ_cnt = 0
        self._fail_cnt = 0

    def process_event_stream(self):
        for event in gv.event_stream.read():
            self.process_event(event)


    def get_eagerness(self):
        """ Returns a float in [0,1] indicating how eager this module is to take
        control. """
        return self._eagerness


    def record(self, action_successful):
        """ Record whether an action succeeds or fails. """
        if action_successful:
            self._succ_cnt += 1
        else:
            self._fail_cnt += 1


    def get_success_percentage(self):
        """ Returns the percentage of times the decision module is successful. """
        try:
            return 100. * self._succ_cnt / (self._succ_cnt + self._fail_cnt)
        except ZeroDivisionError:
            return 0


    @abstractmethod
    def process_event(self, event):
        """ Process an event from the event stream. """
        pass


    @abstractmethod
    def take_control(self):
        """ Generates a sequence of actions. """
        pass
