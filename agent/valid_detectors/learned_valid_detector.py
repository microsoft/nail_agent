import os, sys
import fasttext
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from valid_detector import ValidDetector
import gv
import util

# Monkey patch to remove warning message in fasttext 0.9.2.
# Ref: https://github.com/facebookresearch/fastText/issues/1067
fasttext.FastText.eprint = lambda x: None

model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "valid_model.bin")

class LearnedValidDetector(ValidDetector):
    """
    Uses a fasttext classifier to predict the validity of the response text.

    """
    def __init__(self):
        super().__init__()
        self.model = fasttext.load_model(model_path)

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
