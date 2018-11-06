from abc import ABC, abstractmethod

class AffordanceExtractor(ABC):
    """
    AffordanceExtractor gives likely actions that can be performed on an object or object pair.

    """

    def __init__(self):
        pass


    @abstractmethod
    def extract_single_object_actions(self, entity):
        """ Generate actions afforded by the given entity.
            Returns: List of (action, probability) tuples.
        """
        raise NotImplementedError()


    @abstractmethod
    def extract_double_object_actions(self, entity1, entity2):
        """ Generate actions afforded by the given entity pair.
            Returns: List of (action, probability) tuples.
        """
        raise NotImplementedError()
