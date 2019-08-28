import functools
import importlib
import io
import os

import numpy as np
import tensorflow as tf


# Check if the KerasWrapper instance has a tf.device string argument and use that when running the method, else let tf decide
def with_device(method):
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        if self.device_str:
            with tf.device(self.device_str):
                return method(self, *args, **kwargs)
        else:
            return method(self, *args, **kwargs)
    return wrapped


class KerasWrapper:

    @classmethod
    def get_model_filepath(cls, basedir, model_id):
        return os.path.join(basedir, cls.__name__.lower() + '-' + model_id)

    def __init__(self, model_id, model_definition, device_str=None, tensorboard=None, early_stopping=None, checkpoints=None):
        self.model_id = model_id
        self.device_str = device_str
        self.model = None
        import_path = "speechbox.models." + model_definition["name"]
        self.model_loader = functools.partial(importlib.import_module(import_path).loader, **model_definition["kwargs"])
        self.callbacks = []
        if tensorboard:
            self.callbacks.append(tf.keras.callbacks.TensorBoard(**tensorboard))
        if early_stopping:
            self.callbacks.append(tf.keras.callbacks.EarlyStopping(**early_stopping))
        if checkpoints:
            self.callbacks.append(tf.keras.callbacks.ModelCheckpoint(**checkpoints))

    @with_device
    def to_disk(self, basedir):
        model_path = self.get_model_filepath(basedir, self.model_id)
        self.model.save(model_path, overwrite=True)
        return model_path

    def enable_dataset_logger(self, dataset_name, dataset):
        tensorboard = [callback for callback in self.callbacks if "TensorBoard" in callback.__class__.__name__]
        assert len(tensorboard) == 1, "TensorBoard is not enabled for model or it has too many TensorBoard instances, there is nowhere to write the output of the logged metrics"
        tensorboard = tensorboard[0]
        metrics_dir = os.path.join(tensorboard.log_dir, "dataset", dataset_name)
        summary_writer = tf.summary.create_file_writer(metrics_dir)
        summary_writer.set_as_default()
        def inspect_batches(batch_idx, batch):
            targets = batch[1]
            print("\nLogger enabled for dataset '{}', targets of shape {} from each batch will be written as histograms for TensorBoard".format(dataset_name, targets.shape[1:]))
            tf.summary.histogram("{}-targets".format(dataset_name), tf.math.argmax(targets, 1), step=batch_idx)
            return batch
        dataset = dataset.enumerate().map(inspect_batches)
        return metrics_dir, dataset

    @staticmethod
    def parse_metrics(metrics):
        keras_metrics = []
        for m in metrics:
            metric = None
            if m == "accuracy":
                #FIXME why aren't Accuracy instances working?
                # metric = tf.keras.metrics.Accuracy()
                metric = m
            elif m == "precision":
                metric = tf.keras.metrics.Precision()
            elif m == "recall":
                metric = tf.keras.metrics.Recall()
            assert metric is not None, "Invalid metric {}".format(m)
            keras_metrics.append(metric)
        return keras_metrics

    @with_device
    def prepare(self, features_meta, training_config):
        input_shape = features_meta["sequence_length"], features_meta["num_features"]
        output_shape = features_meta["num_labels"]
        self.model = self.model_loader(input_shape, output_shape)
        opt_conf = training_config["optimizer"]
        optimizer = getattr(tf.keras.optimizers, opt_conf["cls"])(**opt_conf.get("kwargs", {}))
        self.model.compile(
            loss=training_config["loss"],
            optimizer=optimizer,
            metrics=self.parse_metrics(training_config["metrics"])
        )

    @with_device
    def load_weights(self, path):
        self.model.load_weights(path)

    @with_device
    def fit(self, training_set, validation_set, model_config):
        self.model.fit(
            training_set,
            validation_data=validation_set,
            epochs=model_config["epochs"],
            steps_per_epoch=model_config.get("steps_per_epoch"),
            validation_steps=model_config.get("validation_steps"),
            callbacks=self.callbacks,
            verbose=model_config.get("verbose", 2),
            class_weight=model_config.get("class_weight"),
        )

    @with_device
    def evaluate(self, test_set, verbose):
        metrics = {}
        for path, data in test_set.items():
            metrics[path] = self.model.evaluate(
                [data["utterances"]],
                [data["target"]],
                verbose=verbose
            )
        return metrics

    @with_device
    def predict(self, utterances):
        expected_num_labels = self.model.layers[-1].output_shape[-1]
        predictions = np.zeros(expected_num_labels)
        for i, sequences in enumerate(utterances):
            print("predicting", sequences.shape)
            predictions[i] = self.model.predict(sequences)
        print("predictions", predictions.shape)
        return predictions.mean(axis=0)

    @with_device
    def evaluate_confusion_matrix(self, utterances, real_labels):
        predicted_labels = np.int8(self.predict(utterances).argmax(axis=1))
        real_labels = np.int8(np.array(real_labels).argmax(axis=1))
        print(predicted_labels, real_labels)
        return tf.math.confusion_matrix(real_labels, predicted_labels).numpy()

    @with_device
    def count_params(self):
        return sum(layer.count_params() for layer in self.model.layers)

    def __str__(self):
        string_stream = io.StringIO()
        def print_to_stream(*args, **kwargs):
            kwargs["file"] = string_stream
            print(*args, **kwargs)
        self.model.summary(print_fn=print_to_stream)
        return string_stream.getvalue()
