
class Attribute:
    """An attribute describes an object and provides a list of actions
    applicable to that object.

    """
    def __init__(self, name, afforded_actions):
        self.name = name
        self.afforded_actions = afforded_actions

    def to_string(self, prefix=''):
        return prefix + self.name
