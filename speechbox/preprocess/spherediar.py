"""
We need to run the extraction in a different process since SphereDiar is written for TensorFlow 1.
The spherediar_to_numpy.sh script runs a specific Python binary (e.g. from a virtualenv), writes embeddings as numpy arrays, and prints to stdout the paths to the written arrays.
"""
import os
import json

import numpy as np

import speechbox.system as system
from speechbox import get_package_root


def speech_dataset_to_embeddings(labels, paths, label_to_index, tmpdir, spherediar_python, spherediar_stderr):
    spherediar_script = os.path.join(get_package_root(), "scripts", "spherediar_to_numpy.sh")
    spherediar_cmd = "{} {} {} {}".format(spherediar_script, spherediar_stderr, spherediar_python, tmpdir)
    paths_to_numpyfiles = {}
    for res in system.run_for_files(spherediar_cmd, paths):
        batch = json.loads(res)
        intersection = batch.keys() & paths_to_numpyfiles.keys()
        assert not intersection, "system.run_for_files failed, it returned some paths that already have results: {}".format(' '.join(intersection))
        paths_to_numpyfiles.update(batch)
    for label, wavpath in zip(labels, paths):
        numpyfile = paths_to_numpyfiles[wavpath]
        embedding = np.load(numpyfile, allow_pickle=False, fix_imports=False)
        os.remove(numpyfile)
        onehot = np.zeros(len(label_to_index), dtype=np.float32)
        onehot[label_to_index[label]] = 1.0
        yield embedding, onehot