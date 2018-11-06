from abc import ABC, abstractmethod
import gv
from entity import Entity


class Action(ABC):
    """
    An action contains the generation and effects of a given text
    string.

    """
    def __init__(self, verb):
        self.verb = verb

    @abstractmethod
    def text(self):
        """ Generate the text equivalent of a given action. """
        pass

    def validate(self, response_text):
        """
        Determine if an action has succeded based on the textual game's
        textual response. Returns p(valid), the probability of the
        action having succeded.

        """
        return None

    def apply(self):
        """
        Apply the action to the knowledge_graph. The effects of applying
        depend on which action being applied.

        """
        pass

    def recognized(self):
        """ Returns true if action doesn't contain unrecognized words. """
        for word in self.text().split(' '):
            if word in gv.kg._unrecognized_words:
                return False
        return True

    def __str__(self):
        return self.text()

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self.text())

    def __eq__(self, other):
        return self.text() == other.text()


class StandaloneAction(Action):
    """ An action that doesn't require any entities. """
    def __init__(self, verb):
        super().__init__(verb)

    def text(self):
        return self.verb


class SingleAction(Action):
    """ An action of the form: verb entity. """
    def __init__(self, verb, entity):
        super().__init__(verb)
        if not isinstance(entity, Entity):
            raise ValueError("Expected entity object, got {}".format(type(entity)))
        self.entity = entity

    def text(self):
        return "{} {}".format(self.verb, self.entity.name)


class DoubleAction(Action):
    """ An action of the form: verb Entity1 preposition Entity2 """
    def __init__(self, verb, entity1, preposition, entity2):
        super().__init__(verb)
        if not isinstance(entity1, Entity):
            raise ValueError("Expected entity object, got {}".format(type(entity1)))
        if not isinstance(entity2, Entity):
            raise ValueError("Expected entity object, got {}".format(type(entity2)))
        self.entity1 = entity1
        self.prep = preposition
        self.entity2 = entity2

    def text(self):
        return "{} {} {} {}".format(self.verb, self.entity1.name,
                                    self.prep, self.entity2.name)


class NavAction(StandaloneAction):
    def __init__(self, verb):
        super().__init__(verb)

    def apply(self):
        to_loc = gv.kg.connections.navigate(gv.kg.player_location, self)
        assert to_loc, "Error: Unknown connection"
        gv.kg.player_location = to_loc


class ExamineAction(Action):
    def __init__(self, entity_name:str):
        super().__init__("examine")
        self.entity_name = entity_name

    def text(self):
        return "{} {}".format(self.verb, self.entity_name)

    def apply(self):
        entity = Entity(self.entity, response)
        gv.kg.player_location.add_entity(entity)


class TakeAction(SingleAction):
    def __init__(self, entity):
        super().__init__("take", entity)

    def apply(self):
        player_loc = gv.kg.player_location
        if player_loc.has_entity(self.entity):
            player_loc.del_entity(self.entity)
        else:
            gv.logger.warning("WARNING Took non-present entity {}".format(self.entity.name))
        gv.kg.inventory.add_entity(self.entity)
        self.entity.add_attribute(gv.Portable)

    def validate(self, response_text):
        if 'taken' in response_text.lower() or \
           'already' in response_text.lower():
            return 1.
        else:
            return 0.


class TakeAllAction(StandaloneAction):
    def __init__(self):
        super().__init__('take all')


class DropAction(SingleAction):
    def __init__(self, entity):
        super().__init__("drop", entity)

    def apply(self):
        assert self.entity in gv.kg.inventory
        gv.kg.inventory.remove(self.entity)
        gv.kg.player_location.add_entity(self.entity)
        self.entity.add_attribute(gv.Portable)

    def validate(self, response_text):
        if 'dropped' in response_text.lower():
            return 1.
        else:
            return 0.


class OpenAction(SingleAction):
    def __init__(self, entity):
        super().__init__("open", entity)

    def apply(self):
        self.entity.state.open()
        self.entity.add_attribute(gv.Openable)


class CloseAction(SingleAction):
    def __init__(self, entity):
        super().__init__("close", entity)

    def apply(self):
        self.entity.state.close()
        self.entity.add_attribute(gv.Openable)


class LockAction(SingleAction):
    def __init__(self, entity):
        super().__init__("lock", entity)

    def apply(self):
        self.entity.state.lock()
        self.entity.add_attribute(gv.Lockable)

class LockWithAction(DoubleAction):
    def __init__(self, entity1, entity2):
        super().__init__("lock", entity1, "with", entity2)

    def apply(self):
        self.entity1.state.lock()
        self.entity1.add_attribute(gv.Lockable)

class UnlockAction(SingleAction):
    def __init__(self, entity):
        super().__init__("unlock", entity)

    def apply(self):
        self.entity.state.unlock()
        self.entity.add_attribute(gv.Lockable)

class UnlockWithAction(DoubleAction):
    def __init__(self, entity1, entity2):
        super().__init__("unlock", entity1, "with", entity2)

    def apply(self):
        self.entity1.state.unlock()
        self.entity1.add_attribute(gv.Lockable)

class TurnOnAction(SingleAction):
    def __init__(self, entity):
        super().__init__("turn on", entity)

    def apply(self):
        self.entity.state.turn_on()
        self.entity.add_attribute(gv.Switchable)


class TurnOffAction(SingleAction):
    def __init__(self, entity):
        super().__init__("turn off", entity)

    def apply(self):
        self.entity.state.turn_off()
        self.entity.add_attribute(gv.Switchable)


class ConsumeAction(SingleAction):
    """ An action that consumes the entity. """
    def __init__(self, verb, entity):
        super().__init__(verb, entity)

    def apply(self):
        self.entity.state.remove()
        self.entity.add_attribute(gv.Edible)


class MoveItemAction(DoubleAction):
    """ An action that moves an item. """
    def __init__(self, verb, entity1, prep, entity2):
        super().__init__(verb, entity1, prep, entity2)

    def apply(self):
        # TODO: Should entity contain a reference to its own container?
        # move_entity(self.entity1, source_container, self.entity2)
        pass
