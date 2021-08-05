import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from entity_detector import EntityDetector
import gv


class SpacyEntityDetector(EntityDetector):
    """
    Detects entities using spacy.
    """
    def __init__(self):
        super().__init__()


    def detect(self, observation_text):
        # Spacy has trouble detecting entities ending with \n.
        # Ref: https://github.com/explosion/spaCy/issues/4792#issuecomment-614295948
        observation_text = observation_text.replace("\n", " ")
        doc = gv.nlp(observation_text)
        nouns = []
        for chunk in doc.noun_chunks:
            noun = chunk.root.text.lower()
            if noun in self.disallowed:
                continue
            if noun not in nouns:
                nouns.append(noun)
        return nouns
