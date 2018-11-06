from abc import ABC, abstractmethod


class EntityDetector(ABC):
    """
    Detect and extract entities from text.

    """
    def __init__(self):
        self.disallowed = ['i', 'you', 'it', 'north', 'south', 'east', 'west',
                           'northeast', 'northwest', 'southeast', 'southwest']

    @abstractmethod
    def detect(self, observation_text):
        raise NotImplementedError()
