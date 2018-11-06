import os, sys, queue, logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from decision_modules import Examiner, Interactor, Navigator, Hoarder, YesNo, YouHaveTo, Darkness, Idler
from event import *
from knowledge_graph import *
from gv import kg, event_stream, dbg, rng
from util import clean, action_recognized
from valid_detectors.learned_valid_detector import LearnedValidDetector


class NailAgent():
    """
    NAIL Agent: Navigate, Acquire, Interact, Learn

    NAIL has a set of decision modules which compete for control over low-level
    actions. Changes in world-state and knowledge_graph stream events to the
    decision modules. The modules then update how eager they are to take control.

    """
    def __init__(self, seed, env, rom_name, output_subdir='.'):
        self.setup_logging(rom_name, output_subdir)
        rng.seed(seed)
        dbg("RandomSeed: {}".format(seed))
        self.knowledge_graph  = gv.kg
        self.knowledge_graph.__init__() # Re-initialize KnowledgeGraph
        gv.event_stream.clear()
        self.modules = [Examiner(True), Hoarder(True), Navigator(True), Interactor(True),
                        Idler(True), YesNo(True), YouHaveTo(True), Darkness(True)]
        self.active_module    = None
        self.action_generator = None
        self.first_step       = True
        self._valid_detector  = LearnedValidDetector()
        if env and rom_name:
            self.env = env
            self.step_num = 0


    def setup_logging(self, rom_name, output_subdir):
        """ Configure the logging facilities. """
        for handler in logging.root.handlers[:]:
            handler.close()
            logging.root.removeHandler(handler)
        self.logpath = os.path.join(output_subdir, 'nail_logs')
        if not os.path.exists(self.logpath):
            os.mkdir(self.logpath)
        self.kgs_dir_path = os.path.join(output_subdir, 'kgs')
        if not os.path.exists(self.kgs_dir_path):
            os.mkdir(self.kgs_dir_path)
        self.logpath = os.path.join(self.logpath, rom_name)
        logging.basicConfig(format='%(message)s', filename=self.logpath+'.log',
                            level=logging.DEBUG, filemode='w')


    def elect_new_active_module(self):
        """ Selects the most eager module to take control. """
        most_eager = 0.
        for module in self.modules:
            eagerness = module.get_eagerness()
            if eagerness >= most_eager:
                self.active_module = module
                most_eager = eagerness
        dbg("[NAIL](elect): {} Eagerness: {}"\
            .format(type(self.active_module).__name__, most_eager))
        self.action_generator = self.active_module.take_control()
        self.action_generator.send(None)


    def generate_next_action(self, observation):
        """Returns the action selected by the current active module and
        selects a new active module if the current one is finished.

        """
        next_action = None
        while not next_action:
            try:
                next_action = self.action_generator.send(observation)
            except StopIteration:
                self.consume_event_stream()
                self.elect_new_active_module()
        return next_action.text()


    def consume_event_stream(self):
        """ Each module processes stored events then the stream is cleared. """
        for module in self.modules:
            module.process_event_stream()
        event_stream.clear()


    def take_action(self, observation):
        if self.env:
            # Add true locations to the .log file.
            loc = self.env.get_player_location()
            if loc and hasattr(loc, 'num') and hasattr(loc, 'name') and loc.num and loc.name:
                dbg("[TRUE_LOC] {} \"{}\"".format(loc.num, loc.name))

            # Output a snapshot of the kg.
            # with open(os.path.join(self.kgs_dir_path, str(self.step_num) + '.kng'), 'w') as f:
            #     f.write(str(self.knowledge_graph)+'\n\n')
            # self.step_num += 1

        observation = observation.strip()
        if self.first_step:
            dbg("[NAIL] {}".format(observation))
            self.first_step = False
            return 'look' # Do a look to get rid of intro text

        if not kg.player_location:
            loc = Location(observation)
            kg.add_location(loc)
            kg.player_location = loc
            kg._init_loc = loc

        self.consume_event_stream()

        if not self.active_module:
            self.elect_new_active_module()

        next_action = self.generate_next_action(observation)
        return next_action


    def observe(self, obs, action, score, new_obs, terminal):
        """ Observe will be used for learning from rewards. """
        p_valid = self._valid_detector.action_valid(action, new_obs)
        dbg("[VALID] p={:.3f} {}".format(p_valid, clean(new_obs)))
        if kg.player_location:
            dbg("[EAGERNESS] {}".format(' '.join([str(module.get_eagerness()) for module in self.modules[:5]])))
        event_stream.push(NewTransitionEvent(obs, action, score, new_obs, terminal))
        action_recognized(action, new_obs) # Update the unrecognized words
        if terminal:
            kg.reset()


    def finalize(self):
        with open(self.logpath+'.kng', 'w') as f:
            f.write(str(self.knowledge_graph)+'\n\n')
