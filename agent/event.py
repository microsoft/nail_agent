import gv
import util

class EventStream:
    """
    An event stream keeps track of incoming events.

    """
    def __init__(self):
        self._stream = []

    def push(self, event):
        gv.dbg("[LOG]({}) {}".format(type(event).__name__, event.message))
        self._stream.append(event)

    def clear(self):
        del self._stream[:]

    def read(self):
        """ Iterate through the events in the stream. """
        for event in self._stream:
            yield event


class Event:
    """ Base class for all events. """
    def __init__(self, message):
        self.message = message

class NewTransitionEvent(Event):
    """ Generated whenever an action is taken. """
    def __init__(self, obs, action, score, new_obs, terminal):
        message = '\"{}\" --> {} Score={}'.format(action, util.clean(new_obs), score)
        super().__init__(message)
        self.obs      = obs
        self.action   = action
        self.score    = score
        self.new_obs  = new_obs
        self.terminal = terminal

class NewLocationEvent(Event):
    """ Generated whenever a new location is discovered. """
    def __init__(self, new_location):
        super().__init__(new_location.name)
        self.new_location = new_location

class NewEntityEvent(Event):
    """ Generated whenever a new entity is discovered. """
    def __init__(self, new_entity):
        message = "{}: {}".format(new_entity.name, new_entity.description)
        super().__init__(message)
        self.new_entity = new_entity

class NewActionRecordEvent(Event):
    """ Generated whenever a new action is applied. """
    def __init__(self, entity, action_record, result_text):
        message = "{} ==({})==> {}".format(entity, action_record, util.clean(result_text))
        super().__init__(message)
        self.entity = entity
        self.action_record = action_record
        self.result_text = result_text

class NewConnectionEvent(Event):
    """ Generated whenever a new connection is discovered. """
    def __init__(self, connection):
        message = "{} ==({})==> {}".format(connection.from_location, connection.action, connection.to_location)
        super().__init__(message)
        self.connection = connection

class LocationChangedEvent(Event):
    """ Generated whenever the player's location changes. """
    def __init__(self, new_location):
        super().__init__(new_location.name)
        self.new_location = new_location

class EntityMovedEvent(Event):
    """ Generated whenever an entity moves. """
    def __init__(self, entity, origin, destination):
        super().__init__("EntityMoved")
        self.entity = entity
        self.origin = origin
        self.destination = destination

class NewAttributeEvent(Event):
    """ Generated whenever an object is given an attribute. """
    def __init__(self, entity, new_attribute):
        message = "{} is {}".format(entity.name, new_attribute.name)
        super().__init__(message)
        self.new_attribute = new_attribute
