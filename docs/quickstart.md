# Try it in five minutes

This page takes you from nothing to a printed result for two models: picket-forest (CAN bus intrusion detection) and scout-large (jobs, pains and gains in mobility texts). It works on macOS and Linux. Every model needs **Python 3.12 or newer**, and the steps below give you one in a minute.

The install lines and programs on this page are the ones on the model cards. If you read a card instead, you will find the same.

## 1. One environment with Python 3.12

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (for example `brew install uv` on macOS), then make an empty folder with its own environment:

```bash
mkdir try-zoo && cd try-zoo
uv venv --python 3.12
source .venv/bin/activate
python --version
```

The last line must say `Python 3.12` or newer. uv downloads Python 3.12 if your machine only has an older one. Without uv, `python3.12 -m venv .venv` does the same, and you then use `pip install` where this page says `uv pip install`.

## 2. picket-forest

Install it. The edge extra holds what the model needs (numpy, scikit-learn) and no deep-learning framework, roughly 150 to 250 MB:

```bash
uv {install:picket-forest}
```

Save this program as `demo.py`. It downloads the model, an example capture of CAN frames and the calibration table of the example vehicle from the model repository, scores the frames and prints the result:

```python
{snippet:picket-forest}
```

Run it:

```bash
python demo.py
```

You see something like this:

```text
{output:picket-forest}
```

The model flags frames that break the rules calibrated on one vehicle, and the alarm stage raises an alarm when several flagged frames follow each other. To use it on your own vehicle, calibrate it on benign traffic of that vehicle first; the model page shows how.

## 3. scout-large

This is the text model. Its extra holds PyTorch and Transformers, so the install is larger than the first one (several hundred MB). Use the same environment:

```bash
uv {install:scout-large}
```

Save this program as `demo_text.py`, then run it with `python demo_text.py`:

```python
{snippet:scout-large}
```

The first run downloads the model (about 2.2 GB, once) and takes a few seconds to load; with a fast connection plan a few minutes for this step. The result is JSON: for every job, pain or gain in the text, the exact sentence it was found in (`quote`, with its position), a score and a few attributes. An empty list is a valid result.

## When something goes wrong

**`requires a different Python: 3.11.x not in '>=3.12'`.** The environment is not Python 3.12. Run `python --version` inside the activated environment. Create it again with `uv venv --python 3.12`.

**IPython starts with another Python version than the environment.** A banner such as `Python 3.11.7` after you activated a 3.12 environment means `ipython` comes from another interpreter, and it cannot see the packages you just installed (`No module named 'mobility_model_zoo'`). Run your program with `python demo.py`, or install IPython into the environment (`uv pip install ipython`) and start it with `python -m IPython`.

**`No module named pip`.** Environments made by uv do not contain pip. Use `uv pip install ...`, or create the environment with `uv venv --seed`.

**`command not found: from` (or `import`).** The program was pasted into the shell. Save it as a file (`demo.py`) and run it with `python demo.py`.

**`No module named 'joblib'`, `'pandas'` or `'sklearn'` after the install.** You installed without the extra on the install line, or into another environment. Copy the install line from the card as it is, and check `which python` points into `.venv`.

**Windows.** Not tested. Nothing in the picket-forest path needs a compiler, so it should work in a Python 3.12 environment there too.

## Where to go next

The model pages show quality, speed, limits and the worked examples of every model: [the model list](https://mhabedank.github.io/mobility-model-zoo/#models). For picket-forest on a microcontroller, the card also shows the C code for the device.
