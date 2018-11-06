import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from decision_module import DecisionModule
from event import *
from knowledge_graph import *
from action import *
from gv import kg, dbg, rng


class Hoarder(DecisionModule):
    """ The hoarder attempts to Take All """
    def __init__(self, active=False):
        super().__init__()
        self._active = active


    def process_event(self, event):
        if not self._active:
            return
        if type(event) is NewLocationEvent and gv.TakeAll.recognized():
            self._eagerness = 1.


    def parse_response(self, response):
        here = gv.kg.player_location
        success = False
        for line in response.splitlines():
            line = line.strip()
            if ':' in line:
                success = True
                # Example - small mailbox: It's securly anchored.
                entity_name, resp = [w.strip() for w in line.split(':', 1)]
                short_name = entity_name.split(' ')[-1]
                if here.has_entity_with_name(entity_name):
                    entity = here.get_entity_by_name(entity_name)
                elif kg.inventory.has_entity_with_name(entity_name):
                    entity = kg.inventory.get_entity_by_name(entity_name)
                else:
                    # Create the entity at the current location
                    entity = Entity(entity_name, here)
                    entity.add_name(short_name)
                    here.add_entity(entity)

                take_action = gv.Take(entity)
                p_valid = take_action.validate(resp)
                dbg("[Take] p={:.2f} {} --> {}".format(p_valid, entity_name, resp))
                entity.add_action_record(take_action, p_valid, resp)
                if p_valid > 0.5:
                    take_action.apply()
        self.record(success)


    def take_control(self):
        obs = yield
        response = yield gv.TakeAll
        self.parse_response(response)
        self._eagerness = 0
