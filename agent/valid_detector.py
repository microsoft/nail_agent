from abc import ABC, abstractmethod

class ValidDetector(ABC):
    """
    After an action is taken, detect whether the action was valid or
    invalid based on the game's reponse.

    """

    def __init__(self):
        pass


    @abstractmethod
    def action_valid(self, action, response_text):
        """
        Returns p(Valid), the probability that the action was valid.

        """
        raise NotImplementedError()
