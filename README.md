<p align="center">
  <img alt="TensorBoard Manager" src="https://raw.githubusercontent.com/parsiad/tbman/refs/heads/main/logo.png">
</p>

# TensorBoard Manager (`tbman`)

## Motivation

[TensorBoard](https://www.tensorflow.org/tensorboard) is useful for visualizing results from machine learning experiments.

However, TensorBoard has the following issues:

1. **Single log directory**: The server allows only a single `--logdir` ([more details here](#support-for-multiple-log-directories)).
2. **No multi-server management**: Each server has to be spawned individually (tedious!).
3. **Lack of sessions**: Servers do not persist across reboots.

## Features

TensorBoard Manager solves the above problems.
It has...

1. Support for **multiple log directories** per server ([more details here](#support-for-multiple-log-directories))
2. An easy to use **web interface** to spawn and kill servers.
3. **Session management** so that servers are re-spawned on launch.

## Screenshot

![](https://raw.githubusercontent.com/parsiad/tbman/refs/heads/main/screenshot.png)

## Requirements

```
pip install flask tensorboard
```

## Usage

```
git clone https://github.com/parsiad/tbman.git
cd tbman
python tbman.py
```

## Sessions

By default, the session file is stored at `$HOME/.tbman.json`.
An example session is shown below:

```json
[
  {
    "paths": [
      "/home/cool_guy/mnist/linear",
      "/home/cool_guy/mnist/linear_cosine_annealing",
      "/home/cool_guy/mnist/linear_cosine_annealing_big_period"
    ],
    "title": "MNIST Linear"
  },
  {
    "paths": [
      "/home/cool_guy/mnist/cnn_small_kernel",
      "/home/cool_guy/mnist/cnn_big_kernel"
    ],
    "title": "MNIST CNN Models"
  }
]
```

You can use the `-s` flag to change the location of the session file (you can even have multiple `tbman` instances, each with its own session).

## Support for multiple log directories

For each TensorBoard instance, TensorBoard Manager automatically makes a temporary directory containing symlinks to each log directory.
This is the recommended approach from `tensorboard --help`:

```
--logdir PATH         Directory where TensorBoard will look to find TensorFlow event files that it can display. TensorBoard will recursively walk the directory
                      structure rooted at logdir, looking for .*tfevents.* files. A leading tilde will be expanded with the semantics of Python's os.expanduser
                      function.
--logdir_spec PATH_SPEC
                      Like `--logdir`, but with special interpretation for commas and colons: commas separate multiple runs, where a colon specifies a new name for a
                      run. For example: `tensorboard --logdir_spec=name1:/path/to/logs/1,name2:/path/to/logs/2`. This flag is discouraged and can usually be avoided.
                      TensorBoard walks log directories recursively; for finer-grained control, prefer using a symlink tree. Some features may not work when using
                      `--logdir_spec` instead of `--logdir`.
```
