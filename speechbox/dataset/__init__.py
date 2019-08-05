class UnknownDatasetException(Exception): pass
class DatasetRecursionError(RecursionError): pass

from speechbox.dataset.walkers import all_walkers
from speechbox.dataset.parsers import all_parsers

all_datasets = (
    tuple(all_walkers.keys()) +
    tuple(all_parsers.keys())
)
all_split_types = (
    "by-speaker",
    "by-file",
)

def get_dataset_parser(dataset, config=None):
    if config is None:
        config = {}
    if dataset not in all_parsers:
        raise UnknownDatasetException(str(dataset))
    return all_parsers[dataset](**config)

def get_dataset_walker(dataset, config=None):
    if config is None:
        config = {}
    # FIXME hack for mgb3
    # if "test_dir" in config and config["test_dir"] == config["dataset_root"]:
        # dataset = dataset + "-testset"
    if dataset not in all_walkers:
        error_msg = "'{}' has no SpeechDatasetWalker defined".format(dataset)
        raise UnknownDatasetException(error_msg)
    walker = all_walkers[dataset](**config)
    return walker