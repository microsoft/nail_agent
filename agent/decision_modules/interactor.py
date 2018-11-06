import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from valid_detectors.learned_valid_detector import LearnedValidDetector
from affordance_extractors.lm_affordance_extractor import LmAffordanceExtractor
from decision_module import DecisionModule
from gv import kg, event_stream, dbg, rng
from event import *
from attribute import *
from util import clean, first_sentence
from action import SingleAction, DoubleAction


class Interactor(DecisionModule):
    """
    The Interactor creates actions designed to interact with objects
    at the current location.
    """
    def __init__(self, active=False):
        super().__init__()
        self._active = active
        self._valid_detector = LearnedValidDetector()
        self._affordance_extractor = LmAffordanceExtractor()
        self.best_action = None
        self._eagerness = 0.
        self.actions_that_caused_death = {}

    def process_event(self, event):
        pass

    def get_eagerness(self):
        if not self._active:
            return 0.
        self.best_action = None
        self._eagerness = 0.
        max_eagerness = 0.

        # Consider single-object actions.
        for entity in kg.player_location.entities + kg.inventory.entities:
            for action, prob in self._affordance_extractor.extract_single_object_actions(entity):
                if prob <= max_eagerness:
                    break
                if entity.has_action_record(action) or \
                        (not action.recognized()) or \
                        (action in self.actions_that_caused_death) or \
                        ((action.verb == 'take') and (entity in kg.inventory.entities)):  # Need to promote to Take.
                    continue
                max_eagerness = prob
                self.best_action = action
                break

        # Consider double-object actions.
        for entity1 in kg.player_location.entities + kg.inventory.entities:
            for entity2 in kg.player_location.entities + kg.inventory.entities:
                if entity1 != entity2:
                    for action, prob in self._affordance_extractor.extract_double_object_actions(entity1, entity2):
                        if prob <= max_eagerness:
                            break
                        if entity1.has_action_record(action) or \
                                (not action.recognized()) or \
                                (action in self.actions_that_caused_death):
                            continue
                        max_eagerness = prob
                        self.best_action = action
                        break

        self._eagerness = max_eagerness
        return self._eagerness

    def take_control(self):
        obs = yield

        # Failsafe checks
        if self._eagerness == 0.:  # Should never happen anyway.
            self.get_eagerness()  # But if it does, try finding a best action.
            if self._eagerness == 0.:
                return  # If no good action can be found, simply return without yielding.

        action = self.best_action
        self.best_action = None
        self._eagerness = 0.

        response = yield action
        p_valid = action.validate(response)
        if p_valid is None:
            p_valid = self._valid_detector.action_valid(action, first_sentence(response))
        if isinstance(action, SingleAction):
            action.entity.add_action_record(action, p_valid, response)
        elif isinstance(action, DoubleAction):
            action.entity1.add_action_record(action, p_valid, response)
        success = (p_valid > 0.5)
        self.record(success)
        if success:
            action.apply()
        dbg("[INT]({}) p={:.2f} {} --> {}".format(
            "val" if success else "inv", p_valid, action, response))

        if ('RESTART' in response and 'RESTORE' in response and 'QUIT' in response) or ('You have died' in response):
            if action not in self.actions_that_caused_death:
                self.actions_that_caused_death[action] = True  # Remember actions that cause death.
