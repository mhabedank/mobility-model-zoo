"""A Keras callback that logs each epoch to a tracked run (feature 017 T043).

Keras is imported only when the callback is built, so the tracking package never pulls TensorFlow.
"""

from __future__ import annotations


def callback(run):
    """`keras.callbacks.Callback` sending each epoch's logs (loss, accuracy, val_*) as one step."""
    from tensorflow import keras

    class TrackingCallback(keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            run.log_step(epoch + 1, {k: float(v) for k, v in (logs or {}).items()})

    return TrackingCallback()
