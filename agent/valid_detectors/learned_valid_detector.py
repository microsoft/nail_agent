import os, sys
import fastText
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from valid_detector import ValidDetector
import gv
import util

model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "valid_model.bin")

class LearnedValidDetector(ValidDetector):
    """
    Uses a fastText classifier to predict the validity of the response text.

    """
    def __init__(self):
        super().__init__()
        self.model = fastText.load_model(model_path)

    def action_valid(self, action, response_text):
        if not util.action_recognized(action, response_text):
            return 0.
        label, proba = self.model.predict(util.clean(response_text))
        p_valid = 0
        if label[0] == '__label__invalid':
            p_valid = 1-proba[0]
        elif label[0] == '__label__valid':
            p_valid = proba[0]
        else:
            assert False, "Unrecognized Label {}".format(label[0])
        # gv.dbg("[LVD]({}) {} p_Valid={:.2f}".format(action, response_text, p_valid))
        return p_valid
