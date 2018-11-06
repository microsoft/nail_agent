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
        doc = gv.nlp(observation_text)
        nouns = []
        for chunk in doc.noun_chunks:
            noun = chunk.root.text.lower()
            if noun in self.disallowed:
                continue
            if noun not in nouns:
                nouns.append(noun)
        return nouns
