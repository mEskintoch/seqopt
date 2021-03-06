from collections import Counter
import random
from seqopt.optimizers.helpers import reposition_by_index


class Logs:
    """
    class : seqopt.process.Logs
    Hosts the experiment logs, in a fixed manner.
    Schema for the experiment logs cannot be changed.

        :param population: population keys (list[str])
        :param population_growth: allow popu. growth (bool)

    logs schema:
        [{
            'episode' : int,
            'is_opt_episode' : bool,
            'feed' : list[dict],
            'feed_opt' : list[dict],
            'items_added' : list[str]
        }]
    """

    def __init__(self, population=None, population_growth=False):
        self.initial_population = population
        self.population_growth = population_growth
        self.feeds = []
        self.experiment_logs = []
        self.counter = Counter()
        self.feed = None
        self.feed_out = None
        self.items_to_try = None

    @property
    def population(self):
        """
        Gets population. If initial population is
        set to None, only the keys in the feeds
        will be taken as population.
        :return:
            list[str]
        """
        if not self.initial_population:
            return set(self.counter.keys())
        elif self.population_growth:
            return set.union(set(self.initial_population), set(self.counter.keys()))
        else:
            return self.initial_population

    def log_feed(self, feed):
        self.feeds.append(feed)
        self.feed = feed
        self.counter.update([i['key'] for i in feed])

    def log_episode(self, episode, is_opt):
        self.experiment_logs.append({'episode': episode,
                                     'is_opt_episode': is_opt,
                                     'feed': self.feed,
                                     'feed_out': self.feed_out,
                                     'items_added': self.items_to_try
                                     })

    @property
    def unused_items(self):
        """
        Collects items that are not seen in the
         feeds of the current experiment, or tried
         by the model.
        :return:
            list[str]
        """
        if self.initial_population:
            return [item for item in self.population if item not in self.counter.keys()]
        else:
            return []

    def reset_logs(self):
        """
        Reset experiment logs of the experiment.
         Everything except the population is reset
         here (assuming that if a key appeared in
         the feed before, it's part of the population).
        """
        self.feeds = []
        self.experiment_logs = []
        self.counter = Counter()
        self.feed = None
        self.feed_out = None
        self.items_to_try = None


class Experiments(Logs):
    """
    Experiments class inherits the Logs (seqopt.process.Logs)
     and manages the experiments within the model.

        :param population: population keys (list[str])
        :param population_growth: allow popu. growth (bool)
    """

    def __init__(self, population, population_growth):
        super().__init__(population, population_growth)
        self.episode = 0
        self.experiment_id = 0
        self.logged_experiments = {}

    def add_experiment(self):
        if self.experiment_logs:
            self.logged_experiments[self.experiment_id] = self.experiment_logs

    def reset_experiment(self):
        self.add_experiment()
        self.reset_logs()
        self.episode = 0
        self.experiment_id += 1

    @property
    def experiments(self):
        return {**self.logged_experiments, self.experiment_id : self.experiment_logs}

    @property
    def output(self):
        return self.experiments.get(max(self.experiments))[-1].get('feed_out')


class Trials:
    """
    Manages the item trials. At the end of each episode,
     adds the new items from the population, that is not
     yet seen.

     :param n: number of items to add (int)
     :param add_to: add items to location (str)
        can take values:
            last, first, middle, random.
    """

    def __init__(self, n, add_to='last'):
        self.n = n
        if add_to is None:
            self.add_to = 'last'
        else:
            self.add_to = add_to

    @property
    def add_to(self):
        return self._add_to

    @add_to.setter
    def add_to(self, add_to):
        acceptable = ['last', 'first', 'middle', 'random']
        if isinstance(add_to, str) and add_to in acceptable:
            self._add_to = add_to
        else:
            raise ValueError(f"add_to should be one of the following : {', '.join(acceptable)}")

    @staticmethod
    def add_keys(feed, items, indices):
        """
        Add keys to existing feed, in given
            indices.
        :param feed: feed (list)
        :param items: items (iterable)
        :param indices: indices to add (tuple)
        :return:
            feed added (list)
        """
        feed_added = feed.copy()
        items = set([item for item in items if item not in [f['key'] for f in feed_added]])
        for ix, i in enumerate(items):
            feed_added.insert(indices[ix], {'key': i, 'pos': ix, 'reward': 0})
        return reposition_by_index(feed_added)

    @staticmethod
    def _find_indices_to_add(n, length, add_to):
        if add_to == 'last':
            return tuple(length + i for i in range(n))
        elif add_to == 'first':
            return tuple(0 + i for i in range(n))
        elif add_to == 'middle':
            return tuple(round(length / 2) + i for i in range(n))
        else:  # random
            return tuple(random.randint(0, n) for _ in range(n))

    def run(self, feed_out, unused_items):
        """
        Add n unused items to the feed, to
            create circular process.
        :param feed_out: experiments.feed_out
        :param unused_items: experiments.unused_items
        :return:
            feed added (list)
        """
        n_add = len(unused_items) if len(unused_items) < self.n else self.n
        items = random.sample(unused_items, n_add)
        indices = self._find_indices_to_add(n_add, length=len(feed_out), add_to=self.add_to)
        return items, self.add_keys(feed_out, items, indices)




