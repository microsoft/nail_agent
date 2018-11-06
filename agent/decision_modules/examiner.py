import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from entity_detectors.spacy_entity_detector import SpacyEntityDetector
from valid_detectors.learned_valid_detector import LearnedValidDetector
from decision_module import DecisionModule
from event import *
from knowledge_graph import *
from action import *
from gv import kg, dbg, rng
from util import clean, first_sentence

class Examiner(DecisionModule):
    """
    Examiner is responsible for gathering information from the environment
    by issuing the examine command on objects present at a location.

    """
    def __init__(self, active=False):
        super().__init__()
        self._active = active
        self._valid_detector = LearnedValidDetector()
        self._entity_detector = SpacyEntityDetector()
        self._to_examine = {} # Location : ['entity1', 'entity2']
        self._validation_threshold = 0.5  # Best threshold over 16 seeds, but not very sensitive.
        self._high_eagerness = 0.9
        self._low_eagerness = 0.11


    def detect_entities(self, message):
        """ Returns a list of detected candidate entities as strings. """
        return self._entity_detector.detect(message)


    def get_event_info(self, event):
        """ Returns the location and information contained by a new event. """
        message = ''
        location = kg.player_location
        if type(event) is NewLocationEvent:
            location = event.new_location
            message = event.new_location.description
        elif type(event) is NewEntityEvent:
            message = event.new_entity.description
        elif type(event) is NewActionRecordEvent:
            message = event.result_text
        elif type(event) is LocationChangedEvent:
            location = event.new_location
        return location, message


    def process_event(self, event):
        """ Process an event from the event stream. """
        location, message = self.get_event_info(event)
        if location not in self._to_examine:
            self._to_examine[location] = []
        if not message:
            return
        candidate_entities = self.detect_entities(message)
        dbg("[EXM](detect) {} --> {}".format(clean(message), candidate_entities))
        self.filter(candidate_entities)


    def get_eagerness(self):
        """ If we are located at an unexamined location, this module is very eager."""
        if not self._active:
            return 0.
        if self.get_descriptionless_entities():
            return self._high_eagerness
        elif self._to_examine[kg.player_location]:
            return self._low_eagerness
        else:
            return 0.


    def get_descriptionless_entities(self):
        l = [e for e in kg.player_location.entities if not e.description]
        l.extend([e for e in kg.inventory if not e.description])
        return l


    def filter(self, candidate_entities):
        """ Filters candidate entities. """
        curr_loc = kg.player_location
        for entity_name in candidate_entities:
            action = gv.Examine(entity_name)
            if curr_loc.has_entity_with_name(entity_name) or \
               action in curr_loc.action_records or \
               not action.recognized() or \
               entity_name in self._to_examine[curr_loc]:
                continue
            self._to_examine[curr_loc].append(entity_name)


    def take_control(self):
        """
        1) Detect candidate Entities from current location.
        2) Examine entities to get detailed descriptions
        3) Extract nested entities from detailed descriptions
        """
        obs = yield
        curr_loc = kg.player_location
        undescribed_entities = self.get_descriptionless_entities()
        if undescribed_entities:
            entity = undescribed_entities[0]
            action = gv.Examine(entity.name)
            response = yield action
            entity.description = response
            p_valid = self._valid_detector.action_valid(action, response)
            dbg("[EXM] p={:.2f} {} --> {}".format(p_valid, action, clean(response)))
            curr_loc.add_action_record(action, 1., response)
        else:
            entity_name = self._to_examine[curr_loc].pop()
            action = gv.Examine(entity_name)
            response = yield action
            p_valid = self._valid_detector.action_valid(action, first_sentence(response))
            success = (p_valid > self._validation_threshold)
            self.record(success)
            dbg("[EXM]({}) p={:.2f} {} --> {}".format(
                "val" if success else "inv", p_valid, action, clean(response)))
            curr_loc.add_action_record(action, p_valid, response)
            if success:
                entity = curr_loc.get_entity_by_description(response)
                if entity is None:
                    entity = Entity(entity_name, curr_loc, description=response)
                    # TODO: incorrect for entities discovered inside other entities
                    curr_loc.add_entity(entity)
                else:
                    dbg("[EXM](val) Discovered alternate name "\
                        "\'{}\' for \'{}\'".format(entity_name, entity.name))
                    entity.add_name(entity_name)
            if success:
                entity = curr_loc.get_entity_by_description(response)
                inv_entity = kg.inventory.get_entity_by_description(response)
                if entity is None and inv_entity is None:
                    entity = Entity(entity_name, curr_loc, description=response)
                    # TODO: incorrect for entities discovered inside other entities
                    curr_loc.add_entity(entity)
                else:
                    if entity:
                        dbg("[EXM](val) Discovered alternate name " \
                            "\'{}\' for \'{}\'".format(entity_name, entity.name))
                        entity.add_name(entity_name)
                    if inv_entity:
                        dbg("[EXM](val) Discovered alternate name " \
                            "\'{}\' for inventory item \'{}\'".format(entity_name, inv_entity.name))
                        inv_entity.add_name(entity_name)
