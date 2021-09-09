from seqopt import process
from seqopt import callbacks
from seqopt.optimizers import scorers
from seqopt.optimizers import selectors
import pickle


class SeqOpt(process.Experiments):
    """
    :type: seqopt.process.model.OptModel

    The model that optimizes the given initial
    sequence based on the feedback. There are
    two (2) important submodules the model inputs:
        - seqopt.optimizers.optimizers
            Manages the optimization with its given
                configurations / strategy.
        - seqopt.callbacks
            Callbacks

        opt func excepts a feed that is a list of
            dictionary that hosts the feedback for
            keys in following schema:
                [
                    'key' : name (str),
                    'reward'  : reward (int / float)
                    'pos' : position (int) (optional)
                ]

    Args:
        scorer: (scorers.ScoringStrategy)
        selector: (selectors)
        n_try: number of items to try per opt (int)
        add_to: add index strategy (str)
        population: population keys list (list[str])
        episodes: number of episodes (int)
        opt_interval: episodes intervals for optimization (int)
        progress: progress callback (seqopt.callbacks.Progress)
        reset_experiment: reset at the end of trial (bool) (default, False)
    """

    def __init__(self,
                 scorer=None,
                 selector=None,
                 n_try=0,
                 add_to='last',
                 population=None,
                 episodes=None,
                 opt_interval=1,
                 progress=None,
                 reset_experiment=False
                 ):
        super().__init__(logger=process.Logs(population),
                         reset_at_end=reset_experiment,
                         episodes=episodes
                         )
        self.interval = opt_interval
        self.stopper = callbacks.EpisodeLimit(n_episodes=episodes)
        self.selector = selector
        self.scorer = scorer
        self.trials = process.Trials(n=n_try, add_to=add_to)

        if not progress:
            self.progress = callbacks.Progress(patience=None, start_at=0)
        else:
            self.progress = progress

    def reset_model(self):
        self.logger.clear_logs()
        self.progress.reset()
        self.stopper.reset()
        self.episode = 0
        self.experiment_id += 1

    @property
    def is_opt_episode(self):
        return False if bool(self.episode % self.interval) else True

    def select_and_score(self):
        self.logger.feed_out = selectors.do_select(
            self.selector,scorers.do_score(
                self.scorer,self.logger))

    def add_trial_items(self):
        self.logger.items_to_try, self.logger.feed_out = self.trials.run(self.logger)

    def opt(self, feed):
        """
        Optimize the sequence with number of input
            given overtime.
        :param feed: feedback (list)
        :return:
            optimized sequence (list)
        """
        self.stopper.invoke(self.logger.logs)
        if self.stopper.stop or self.progress.stop:
            if self.experiment_id not in self.experiments:
                self.add_experiment()
            return self.logger.feed_out
        self.logger.log_feed(feed)
        if self.is_opt_episode:
            self.select_and_score()
            self.add_trial_items()
        self.logger.log_episode(self.episode, self.is_opt_episode)
        self.progress.invoke(self.logger.logs)
        if self.reset:
            self.add_experiment()
            self.reset_model()
            return None
        else:
            self.episode += 1
            return self.logger.feed_out


def load(path):
    """
    Load process.
    :param path:
    :return:
    """
    with open(path, 'r') as f:
        model = pickle.load(f)
    return model


def save(model, path):
    """
    Checkpoint the process on a given episode.
    :param model: seqopt process.
    :param path: checkpoint location (str)
    """
    with open(f'{path}/seqopt', 'w') as f:
        pickle.dump(model, f)




