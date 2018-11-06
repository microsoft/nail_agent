import gv
import event
import re
from action import Action


def first_sentence(text):
    """ Extracts the first sentence from text. """
    tokens = gv.nlp(text)
    return next(tokens.sents).merge().text


def tokenize(description):
    """ Returns a list of tokens in a string. """
    doc = gv.nlp(description)
    return [word.lower_ for word in doc]


def clean(s):
    """ Clean a string for compact output. """
    return s.replace('\n', ' ').strip()


def move_entity(entity, origin, dest):
    """ Moves entity from origin to destination. """
    assert origin.has_entity(entity), \
        "Can't move entity {} that isn't present at origin {}" \
        .format(entity, origin)
    origin.del_entity(entity)
    dest.add_entity(entity)
    gv.event_stream.push(event.EntityMovedEvent(entity, origin, dest))


# This list covers the common paterns. However, some games like
# loose.z5 and lostpig.z8 write custom responses that aren't included.
REGEXPS = [
    ".*That's not a verb I recognise.*",
    ".*I don't know the word \"(\w+)\.?\".*",
    ".*You used the word \"(\w+)\" in a way that I don't understand.*",
    ".*This story doesn't know the word \"(\w+)\.?\".*",
    ".*This story doesn't recognize the word \"(\w+)\.?\".*",
    ".*The word \"(\w+)\" isn't in the vocabulary that you can use.*",
    ".*You don't need to use the word \"(\w+)\" to finish this story.*",
    ".*You don't need to use the word \"(\w+)\" to complete this story.*",
    ".*Sorry, but the word \"(\w+)\" is not in the vocabulary you can use.*",
    ".*Sorry, but this story doesn't recognize the word \"(\w+)\.?\".*",
]
COMPILED_REGEXPS = [re.compile(regexp) for regexp in REGEXPS]


def get_unrecognized(action, response):
    """
    Returns an unrecognized word based on the response or empty string.

    Args:
      action: The action that was taken
      response: The textual response from the game

    Returns: string containing the unrecognized word or
    empty string if recognized.

    """
    if isinstance(action, Action):
        action = action.text()
    for p in COMPILED_REGEXPS:
        match = p.match(response)
        if match:
            if match.groups():
                return match.group(1)
            else:
                return action.split(' ')[0]
    return ''


def action_recognized(action, response):
    """
    Returns True if the action was recognized based on the response.
    Returns False if the action is not recognized and appends it to
    the list of unrecognized_words.

    """
    unrecognized_word = get_unrecognized(action, response)
    if unrecognized_word:
        if unrecognized_word not in gv.kg._unrecognized_words:
            gv.dbg("[UTIL] Added unrecognized word \"{}\"".format(unrecognized_word))
            gv.kg._unrecognized_words.append(unrecognized_word)
        return False
    return True
