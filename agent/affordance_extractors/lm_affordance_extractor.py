import os, sys, math
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from affordance_extractor import AffordanceExtractor
from gv import Take, Open, Eat, Drink, Move, Push, Pull, Lift, TurnOn, TurnOff, Light, Extinguish, Open, Close, Lock, Unlock, Search, Ask, Talk, Kiss, Bribe, Attack, Kill
from gv import rng
import action
from ctypes import *
from action import DoubleAction

LANGUAGE_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'language_model')
LM_READER_PATH = os.path.join(LANGUAGE_MODEL_DIR, 'lm_reader.so')
FORWARD_LM_PATH = os.path.join(LANGUAGE_MODEL_DIR, 'nail_agent_lm/st')

LM_AFFORDANCE_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lm_affordance_data')
ATTR_DET_VERBS_PATH = os.path.join(LM_AFFORDANCE_DATA_DIR, 'attribute_detection_verbs.csv')
TARG_ATTR_SCORES_PATH = os.path.join(LM_AFFORDANCE_DATA_DIR, 'target_attribute_scores.csv')
TARG_CMD_SCORES_PATH = os.path.join(LM_AFFORDANCE_DATA_DIR, 'target_command_scores.csv')
CALIBRATION_THRESHOLDS_PATH = os.path.join(LM_AFFORDANCE_DATA_DIR, 'calibration_thresholds.tsv')
ACTION_PRIORS_PATH = os.path.join(LM_AFFORDANCE_DATA_DIR, 'action_priors.csv')


complex_verbs = [
    ('put', 'in'), ('put','on'),
    ('unlock','with'), ('open','with'),
    ('break','with'), ('attack','with'),
    ('ask', 'for'), ('ask','about'),
    ('give','to'), ('throw','at')
]


class AffordableAttribute:
    def __init__(self, attribute_name, detection_verbs):
        self.attribute_name = attribute_name
        self.detection_verbs = detection_verbs
        self.target_probs = []
        self.known_actions_to_try = []
        self.unknown_actions_to_exclude = []
        self.known_action_extraction_threshold = 0.15


class LmAffordanceExtractor(AffordanceExtractor):
    """
    Uses an ngram language model to extract affordances.

    """
    def __init__(self):
        super().__init__()
        self.lib = CDLL(LM_READER_PATH)
        self.configure_ctypes(self.lib)
        self.forward_model = self.open_language_model(FORWARD_LM_PATH)
        self.affordable_attributes = []
        self.affordable_attributes_by_name = {}
        self.attribute_probs = {}

        self.num_commands_to_return = 30

        self.cached_unknown_actions = {}
        self.cached_extractions = {}

        self.init_affordable_attributes()
        self.get_log_prob_calibration_thresholds()
        self.unknown_action_extraction_threshold = 0.4

        self.double_object_action_lp_offset = 12.  # Higher numbers give higher probs.
        self.double_object_action_lp_scale = 2.0  # Higher numbers give wider prob variance.
        self.double_object_action_extraction_threshold = 0.05  # Probably good to match the Idler's eagerness.
        self.cached_double_object_actions = {}

        self.action_prior_table = {}
        self.filtered_action_list = []
        self.read_action_priors()

    def __del__(self):
        self.lib.NgramTrieLM_Close(self.forward_model)

    def configure_ctypes(self, lib):
        lib.NgramTrieLM_Open.argtypes = [c_char_p, c_int, c_int]
        lib.NgramTrieLM_Open.restype = c_void_p

        lib.NgramTrieLM_Close.argtypes = [c_void_p]
        lib.NgramTrieLM_Close.restype = None

        lib.NgramTrieLM_GetJointProb.argtypes = [c_void_p, c_char_p, c_int]
        lib.NgramTrieLM_GetJointProb.restype = c_uint

    def open_language_model(self, path):
        if not os.path.isfile(path + '.utrie'):
            print("Language model not found. Please follow the README steps to download it.")
        model = self.lib.NgramTrieLM_Open(path.encode('utf-8'), 0, 512)
        return model

    def get_joint_log_prob(self, model, string, order):
        encoded_log_prob = self.lib.NgramTrieLM_GetJointProb(model, string.encode('utf-8'), order)
        return encoded_log_prob / -1000.

    def read_action_priors(self):
        action_priors_file = open(ACTION_PRIORS_PATH, 'r')
        for line in action_priors_file:
            fields = line[:-1].split(',')
            action_text = fields[0]
            prior = int(fields[1]) / 8.
            self.action_prior_table[action_text] = prior
            self.filtered_action_list.append(action_text)
        action_priors_file.close()

    def extract_single_object_actions(self, entity):
        if id(entity) in self.cached_extractions:
            return self.cached_extractions[id(entity)]

        # Collect known actions for the given entity.
        noun = entity.name
        actions_to_try = []
        unknown_actions_to_exclude = {}
        for affordable_attribute in self.affordable_attributes:
            est_prob = self.estimate_attribute_prob(noun, affordable_attribute.attribute_name)
            if est_prob >= affordable_attribute.known_action_extraction_threshold:
                for known_action in affordable_attribute.known_actions_to_try:
                    actions_to_try.append((known_action(entity), est_prob))
                for unknown_action in affordable_attribute.unknown_actions_to_exclude:
                    unknown_actions_to_exclude[unknown_action] = True

        # Collect unknown actions for the given entity.
        unknown_actions_to_try = self.extract_unknown_actions_with_log_probs(noun)

        for a_lp in unknown_actions_to_try:
            if a_lp[0] not in self.action_prior_table:
                self.action_prior_table[a_lp[0]] = -1.  # Needs human review.

        for a_lp in unknown_actions_to_try:
            prob = self.estimate_unknown_action_prob(a_lp[1])
            prob *= max(0., self.action_prior_table[a_lp[0]])  # Treat unreviewed actions (-1) as 0.0
            if prob > self.unknown_action_extraction_threshold:
                action_text = a_lp[0]
                action_minus_the = action_text[:-4]
                if action_minus_the not in unknown_actions_to_exclude.keys():
                    if action_minus_the in self.unknown_actions_to_promote:
                        target_action = rng.choice(self.unknown_actions_to_promote[action_minus_the])
                        action_object = target_action(entity)
                    else:
                        action_object = action.SingleAction(action_text, entity)
                    actions_to_try.append((action_object, prob))

        # Sort by descending probability of expected value of taking the action.
        actions_to_try.sort(key=lambda tup: tup[1], reverse=True)
        self.cached_extractions[id(entity)] = actions_to_try
        return actions_to_try

    def extract_double_object_actions(self, entity1, entity2):
        key = (id(entity1), id(entity2))
        if key in self.cached_double_object_actions:
            return self.cached_double_object_actions[key]

        action_prob_dict = {}
        num_actions = 0
        tie_breaker = 0.00000001
        for verb, prep in complex_verbs:
            phrase = verb + ' the ' + entity1.name + ' ' + prep + ' the ' + entity2.name
            log_prob = self.get_joint_log_prob(self.forward_model, phrase, 5)
            num_actions += 1
            action_prob_dict[DoubleAction(verb, entity1, prep, entity2)] = log_prob + num_actions * tie_breaker

        sorted_actions = sorted(action_prob_dict, key=action_prob_dict.get, reverse=True)
        scored_actions = []
        for action in sorted_actions:
            log_prob = action_prob_dict[action]
            prob = 1. / (1. + math.exp(min(20., -(log_prob + self.double_object_action_lp_offset) * self.double_object_action_lp_scale)))
            if prob > self.double_object_action_extraction_threshold:
                scored_actions.append((action, prob))

        self.cached_double_object_actions[key] = scored_actions
        return scored_actions

    def estimate_attribute_prob(self, entity_name, attribute_name):
        combined_string = "[{}][{}]".format(entity_name, attribute_name)
        if combined_string in self.attribute_probs.keys():
            return self.attribute_probs[combined_string]

        affordable_attribute = self.affordable_attributes_by_name[attribute_name]
        thresh_hi = affordable_attribute.thresholds[2]
        thresh_md = affordable_attribute.thresholds[1]
        thresh_lo = affordable_attribute.thresholds[0]
        log_prob = self.conditional_log_prob_of_attribute_given_noun(affordable_attribute.attribute_name, entity_name)
        if log_prob >= thresh_hi:
            est_prob = 1.
        elif log_prob <= thresh_lo:
            est_prob = 0.
        elif log_prob >= thresh_md:
            est_prob = 0.5 + 0.5 * (log_prob - thresh_md) / (thresh_hi - thresh_md)
        else:
            est_prob = 0.5 * (log_prob - thresh_lo) / (thresh_md - thresh_lo)

        self.attribute_probs[combined_string] = est_prob
        return est_prob

    def estimate_unknown_action_prob(self, log_prob):
        thresh_hi = self.unknown_action_calibration_thresholds[2]
        thresh_md = self.unknown_action_calibration_thresholds[1]
        thresh_lo = self.unknown_action_calibration_thresholds[0]

        if log_prob >= thresh_hi:
            est_prob = 1.
        elif log_prob <= thresh_lo:
            est_prob = 0.
        elif log_prob >= thresh_md:
            est_prob = 0.5 + 0.5 * (log_prob - thresh_md) / (thresh_hi - thresh_md)
        else:
            est_prob = 0.5 * (log_prob - thresh_lo) / (thresh_md - thresh_lo)

        return est_prob

    def conditional_log_prob_of_attribute_given_noun(self, attribute_name, noun):
        affordable_attribute = self.affordable_attributes_by_name[attribute_name]
        overall_score = 0.
        noun_phrase = 'the ' + noun
        log_prob_of_noun_phrase = self.get_joint_log_prob(self.forward_model, noun_phrase, 5)
        for verb in affordable_attribute.detection_verbs:
            log_prob_of_verb_and_noun = self.get_joint_log_prob(self.forward_model, verb + ' ' + noun_phrase, 5)
            score = log_prob_of_verb_and_noun - log_prob_of_noun_phrase  # Conditional probability
            if score > 0.:
                assert(score <= 0.)
            overall_score += score
        overall_score /= len(affordable_attribute.detection_verbs)
        return overall_score

    def calc_error_with_1_threshold(self, score, threshold, i_noun, attrib):
        if score >= threshold:
            est_prob = 1.
        else:
            est_prob = 0.
        target_prob = attrib.target_probs[i_noun]
        error = est_prob - target_prob
        return est_prob, target_prob, error * error

    def calc_error_with_3_thresholds(self, score, thresh_lo, thresh_md, thresh_hi, i_noun, attrib):
        if score >= thresh_hi:
            est_prob = 1.
        elif score <= thresh_lo:
            est_prob = 0.
        elif score >= thresh_md:
            est_prob = 0.5 + 0.5 * (score - thresh_md) / (thresh_hi - thresh_md)
        else:
            est_prob = 0.5 * (score - thresh_lo) / (thresh_md - thresh_lo)
        target_prob = attrib.target_probs[i_noun]
        error = est_prob - target_prob
        return est_prob, target_prob, error * error

    def init_affordable_attributes(self):
        # Create the affordable attributes, and load their detection verbs.
        attribute_detection_verbs = open(ATTR_DET_VERBS_PATH, encoding='utf-8-sig')
        lines = attribute_detection_verbs.readlines()
        attribute_detection_verbs.close()
        for line in lines:
            fields = line[:-1].split(',')
            affordable_attribute = AffordableAttribute(fields[0], fields[1:])
            self.affordable_attributes.append(affordable_attribute)
            self.affordable_attributes_by_name[affordable_attribute.attribute_name] = affordable_attribute

        # Cache more attribute information.
        affordable_attribute = self.affordable_attributes_by_name["portable"]
        affordable_attribute.known_actions_to_try = [Take]
        affordable_attribute.unknown_actions_to_exclude = ["take", "drop", "give", "put", "place", "set", "get", "leave"]
        affordable_attribute.known_action_extraction_threshold = 0.  # LmAffordanceExtractor thinks everything should be taken.

        affordable_attribute = self.affordable_attributes_by_name["edible"]
        affordable_attribute.known_actions_to_try = [Eat, Drink]
        affordable_attribute.unknown_actions_to_exclude = ["eat", "drink", "swallow", "consume"]

        affordable_attribute = self.affordable_attributes_by_name["moveable"]
        affordable_attribute.known_actions_to_try = [Move, Push, Pull, Lift]
        affordable_attribute.unknown_actions_to_exclude = ["move", "push", "pull", "drag", "lift"]

        affordable_attribute = self.affordable_attributes_by_name["switchable"]
        affordable_attribute.known_actions_to_try = [TurnOn]
        affordable_attribute.unknown_actions_to_exclude = ["turn on", "switch on", "turn off", "switch off", "start", "stop"]

        affordable_attribute = self.affordable_attributes_by_name["flammable"]
        affordable_attribute.known_actions_to_try = [Light]
        affordable_attribute.unknown_actions_to_exclude = ["light", "ignite", "extinguish"]

        affordable_attribute = self.affordable_attributes_by_name["openable"]
        affordable_attribute.known_actions_to_try = [Open]
        affordable_attribute.unknown_actions_to_exclude = ["open", "close", "shut"]

        affordable_attribute = self.affordable_attributes_by_name["lockable"]
        affordable_attribute.known_actions_to_try = [Unlock]
        affordable_attribute.unknown_actions_to_exclude = ["lock", "unlock"]

        affordable_attribute = self.affordable_attributes_by_name["container"]
        affordable_attribute.known_actions_to_try = [Search]
        affordable_attribute.unknown_actions_to_exclude = ["look in", "search", "search in", "empty", "fill", "fill up"]

        affordable_attribute = self.affordable_attributes_by_name["person"]
        affordable_attribute.known_actions_to_try = [Talk]
        affordable_attribute.unknown_actions_to_exclude = ["ask", "talk to", "help", "hug", "kiss", "bribe", "pay"]

        affordable_attribute = self.affordable_attributes_by_name["enemy"]
        affordable_attribute.known_actions_to_try = [Attack, Kill]
        affordable_attribute.unknown_actions_to_exclude = ["attack", "hit", "kill", "stab", "slay", "strangle", "fight", "strike", "shoot"]

        # Prepare the set of unknown actions to promote.
        self.unknown_actions_to_promote = {}
        for affordable_attribute in self.affordable_attributes:
            for unknown_action in affordable_attribute.unknown_actions_to_exclude:
                if unknown_action not in self.unknown_actions_to_promote:
                    self.unknown_actions_to_promote[unknown_action] = affordable_attribute.known_actions_to_try

    def get_log_prob_calibration_thresholds(self):
        # Can previously computed thresholds be found?
        threshold_file_header = "# Delete this line to recalculate the thresholds on the next run.\n"
        if os.path.isfile(CALIBRATION_THRESHOLDS_PATH):
            thresholds_file = open(CALIBRATION_THRESHOLDS_PATH, 'r')
            lines = thresholds_file.readlines()
            thresholds_file.close()
            if len(lines) > 0:
                if lines[0] == threshold_file_header:
                    # Yes. Read them from the file.
                    line = lines[-1]
                    fields = line[:-1].split('\t')
                    assert fields[3] == "unknown actions"
                    self.unknown_action_calibration_thresholds = (float(fields[0]), float(fields[1]), float(fields[2]))
                    for line in lines[1:-1]:
                        fields = line[:-1].split('\t')
                        affordable_attribute = self.affordable_attributes_by_name[fields[3]]
                        best_thresh_lo = float(fields[0])
                        best_thresh_md = float(fields[1])
                        best_thresh_hi = float(fields[2])
                        affordable_attribute.thresholds = (best_thresh_lo, best_thresh_md, best_thresh_hi)
                    return

        # No, the thresholds cannot be found. So recompute them.
        print("Recomputing the log-prob calibration thesholds.")
        thresholds_file = open(CALIBRATION_THRESHOLDS_PATH, 'w')
        thresholds_file.write(threshold_file_header)

        # Load the target probs.
        target_nouns = []
        target_attribute_scores = open(TARG_ATTR_SCORES_PATH, 'r')
        lines = target_attribute_scores.readlines()
        target_attribute_scores.close()
        for line in lines[1:]:
            fields = line[:-1].split(',')
            target_nouns.append(fields[0])
            scores = fields[1:]
            for i, score in enumerate(scores):
                self.affordable_attributes[i].target_probs.append(int(score) / 8.)

        # Tune each attribute separately.
        mean_lowest_error = 0.
        num_attributes_examined = 0
        for affordable_attribute in self.affordable_attributes:
            # if attrib.name != "enemy":
            #     continue
            num_attributes_examined += 1
            scores = []

            # Collect the raw scores for the target nouns.
            for i_noun in range(len(target_nouns)):
                scores.append(self.conditional_log_prob_of_attribute_given_noun(affordable_attribute.attribute_name, target_nouns[i_noun]))

            # Find the best middle threshold, for pinning to 0.5.
            lowest_error = 100.
            best_thresh_md = -1
            for i_thresh in range(1000):
                thresh = 0. - i_thresh * 0.01
                mean_squared_error = 0.
                for i_noun in range(len(target_nouns)):
                    est_prob, target_prob, squared_error = self.calc_error_with_1_threshold(scores[i_noun], thresh, i_noun, affordable_attribute)
                    mean_squared_error += squared_error
                mean_squared_error /= len(target_nouns)
                if mean_squared_error < lowest_error:
                    lowest_error = mean_squared_error
                    best_thresh_md = thresh

            lowest_error = 100.
            best_thresh_hi = -1
            best_thresh_lo = -1
            thresh_lo = best_thresh_md
            thresh_md = best_thresh_md

            # Find the best hi threshold, for clipping to 1.
            for i in range(1000):
                thresh_hi = thresh_md + i * 0.01
                mean_squared_error = 0.
                for i_noun in range(len(target_nouns)):
                    est_prob, target_prob, squared_error = self.calc_error_with_3_thresholds(scores[i_noun], thresh_lo, best_thresh_md, thresh_hi, i_noun, affordable_attribute)
                    mean_squared_error += squared_error
                mean_squared_error /= len(target_nouns)
                if mean_squared_error < lowest_error:
                    lowest_error = mean_squared_error
                    best_thresh_hi = thresh_hi

            # Find the best lo threshold, for clipping to 0.
            for i in range(1000):
                thresh_lo = thresh_md - i * 0.01
                mean_squared_error = 0.
                for i_noun in range(len(target_nouns)):
                    est_prob, target_prob, squared_error = self.calc_error_with_3_thresholds(scores[i_noun], thresh_lo, best_thresh_md, thresh_hi, i_noun, affordable_attribute)
                    mean_squared_error += squared_error
                mean_squared_error /= len(target_nouns)
                if mean_squared_error < lowest_error:
                    lowest_error = mean_squared_error
                    best_thresh_lo = thresh_lo

            thresholds_file.write("{:7.3f}\t{:7.3f}\t{:7.3f}\t{}\n".format(best_thresh_lo, best_thresh_md, best_thresh_hi, affordable_attribute.attribute_name))
            mean_lowest_error += lowest_error
            affordable_attribute.thresholds = (best_thresh_lo, best_thresh_md, best_thresh_hi)

        # Now compute the calibration thresholds for unknown actions.

        # Load the target command scores. (The manual labels.)
        target_command_scores_file = open(TARG_CMD_SCORES_PATH, 'r')
        lines = target_command_scores_file.readlines()
        target_command_scores_file.close()
        target_command_scores = {}
        for line in lines:
            fields = line[:-1].split(',')
            target_command_scores[fields[0]] = int(fields[1])

        # Gather the numbers to be used for tuning.
        x_y_pairs = []
        for noun in target_nouns:
            scored_actions = self.extract_unknown_actions_with_log_probs(noun)
            for scored_action in scored_actions:
                command = scored_action[0] + ' ' + noun
                if command in target_command_scores.keys():
                    lp = max(-25.0, scored_action[1])
                    prob_times_8 = target_command_scores[command]
                    x_y_pairs.append((lp, prob_times_8 / 8.))
        for x_y_pair in x_y_pairs:
            print("{}\t{}".format(x_y_pair[0], x_y_pair[1]))

        # Find the best middle log-prob threshold, for pinning output probs to 0.5.
        lowest_error = 100.
        best_thresh_md = -1
        num_pairs = len(x_y_pairs)
        for i_thresh in range(100):
            thresh = 0. - i_thresh * 0.1
            mean_squared_error = 0.
            for x_y_pair in x_y_pairs:
                x = x_y_pair[0]
                y = x_y_pair[1]
                if x > thresh:
                    y_est = 1.
                else:
                    y_est = 0.
                error = y_est - y
                squared_error = error * error
                mean_squared_error += squared_error
            mean_squared_error /= num_pairs
            if mean_squared_error < lowest_error:
                lowest_error = mean_squared_error
                best_thresh_md = thresh

        # Find the best hi log-prob threshold, for clipping output probs to 1.
        lowest_error = 100.
        best_thresh_hi = -1
        thresh_md = best_thresh_md
        for i in range(100):
            thresh_hi = thresh_md + i * 0.1
            mean_squared_error = 0.
            count = 0
            for x_y_pair in x_y_pairs:
                x = x_y_pair[0]
                y = x_y_pair[1]
                if x > thresh_md:
                    count += 1
                    if x >= thresh_hi:
                        y_est = 1.
                    else:
                        y_est = 0.5 + 0.5 * (x - thresh_md) / (thresh_hi - thresh_md)
                    error = y_est - y
                    squared_error = error * error
                    mean_squared_error += squared_error
            mean_squared_error /= count
            if mean_squared_error < lowest_error:
                lowest_error = mean_squared_error
                best_thresh_hi = thresh_hi

        # Find the best lo log-prob threshold, for clipping output probs to 0.
        lowest_error = 100.
        best_thresh_lo = -1
        for i in range(100):
            thresh_lo = thresh_md - i * 0.1
            mean_squared_error = 0.
            count = 0
            for x_y_pair in x_y_pairs:
                x = x_y_pair[0]
                y = x_y_pair[1]
                if x < thresh_md:
                    count += 1
                    if x >= thresh_lo:
                        y_est = 0.5 * (x - thresh_lo) / (thresh_md - thresh_lo)
                    else:
                        y_est = 0.
                    error = y_est - y
                    squared_error = error * error
                    mean_squared_error += squared_error
            mean_squared_error /= count
            if mean_squared_error < lowest_error:
                lowest_error = mean_squared_error
                best_thresh_lo = thresh_lo

        self.unknown_action_calibration_thresholds = (best_thresh_lo, best_thresh_md, best_thresh_hi)
        thresholds_file.write("{:7.3f}\t{:7.3f}\t{:7.3f}\tunknown actions\n".format(best_thresh_lo, best_thresh_md, best_thresh_hi))
        thresholds_file.close()

    def extract_unknown_actions_with_log_probs(self, entity_text):
        if entity_text in self.cached_unknown_actions.keys():
            return self.cached_unknown_actions[entity_text]

        noun_log_prob = self.get_joint_log_prob(self.forward_model, entity_text, 5)
        verbose = False
        commands = {}
        num_commands = 0
        tie_breaker = 0.00000001

        for action_text in self.filtered_action_list:
            verb_noun_phrase = action_text + ' ' + entity_text
            joint_log_prob = self.get_joint_log_prob(self.forward_model, verb_noun_phrase, 5)
            joint_log_prob -= noun_log_prob  # Make the prob conditional on the noun.
            if not action_text in commands:
                commands[action_text] = joint_log_prob + num_commands * tie_breaker
                num_commands += 1
                if verbose:
                    print("{:8.3f}  Command  {}    {}    {}".format(joint_log_prob, forward_string.rjust(30), tags, verb_noun_phrase))

        sorted_commands = sorted(commands, key=commands.get, reverse=True)
        scored_commands = []
        for command in sorted_commands[:self.num_commands_to_return]:
            scored_commands.append((command, commands[command]))

        self.cached_unknown_actions[entity_text] = scored_commands
        return scored_commands
