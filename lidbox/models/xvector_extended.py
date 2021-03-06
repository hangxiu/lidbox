"""
Extended x-vector architecture by
Villalba et al. (2018) "The JHU-MIT System Description for NIST SRE18"
url: https://pdfs.semanticscholar.org/00a4/e57e9189162dc9875a1cdca527711f373b53.pdf
"""
from tensorflow.keras.layers import (
    Activation,
    Dense,
    Input,
)
from tensorflow.keras.models import Model
import tensorflow as tf

from .xvector import (
    FrameLayer,
    GlobalMeanStddevPooling1D,
    SegmentLayer,
)


def loader(input_shape, num_outputs, output_activation="log_softmax", channel_dropout_rate=0):
    inputs = Input(shape=input_shape, name="input")
    x = inputs
    if channel_dropout_rate > 0:
        x = Dropout(rate=channel_dropout_rate, noise_shape=(None, 1, input_shape[1]), name="channel_dropout")(x)
    x = FrameLayer(512, 5, 1, name="frame1")(x)
    x = FrameLayer(512, 1, 1, name="frame2")(x)
    x = FrameLayer(512, 3, 2, name="frame3")(x)
    x = FrameLayer(512, 1, 1, name="frame4")(x)
    x = FrameLayer(512, 3, 3, name="frame5")(x)
    x = FrameLayer(512, 1, 1, name="frame6")(x)
    x = FrameLayer(512, 3, 4, name="frame7")(x)
    x = FrameLayer(512, 1, 1, name="frame8")(x)
    x = FrameLayer(512, 1, 1, name="frame9")(x)
    x = FrameLayer(512, 1, 1, name="frame10")(x)
    x = GlobalMeanStddevPooling1D(name="stats_pooling")(x)
    x = SegmentLayer(512, name="segment1")(x)
    x = SegmentLayer(512, name="segment2")(x)
    outputs = Dense(num_outputs, name="output", activation=None)(x)
    if output_activation:
        outputs = Activation(getattr(tf.nn, output_activation), name=str(output_activation))(outputs)
    return Model(inputs=inputs, outputs=outputs, name="x-vector-extended")


def predict(model, inputs):
    return model.predict(inputs)
