#!/usr/bin/env python

import argparse
import getpass
import json
import os
import random
import shutil
import signal
import socket
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)


class _Config(NamedTuple):
    paths: list[str]
    title: str


class _Instance(NamedTuple):
    cfg: _Config
    ident: int
    logdir: str
    port: int


class _TensorBoard(NamedTuple):
    instance: _Instance
    proc: subprocess.Popen


def _make_logdir(paths: list[Path]) -> Path:
    logdir = Path(tempfile.mkdtemp())
    for path in paths:
        count = 0
        while (link_path := logdir / f"{path.name}_{count}").exists():
            count += 1
        link_path.symlink_to(path.absolute())
    return logdir


def _find_port(port_lo: int, port_hi: int, max_attempts: int = 32) -> int:
    for _ in range(max_attempts):
        port = random.randint(port_lo, port_hi - 1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
    return -1


class _Manager:
    def __init__(
        self,
        db_path: Path,
        host: str,
        port_lo: int,
        port_hi: int,
        tb_path: str,
    ) -> None:
        self._count = 0
        self._db_path = db_path
        self._host = host
        self._port_lo = port_lo
        self._port_hi = port_hi
        self._tbs: dict[int, _TensorBoard] = {}
        self._tb_path = tb_path
        self._load()

    def _load(self):
        if not os.path.exists(self._db_path):
            return
        with open(self._db_path, "r") as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError:
                msg = f"Unable to parse database {self._db_path}"
                print(msg, file=sys.stderr)
                sys.exit(1)
            for item in data:
                cfg = _Config(**item)
                self.launch(cfg)

    @property
    def host(self) -> str:
        return self._host

    def save(self) -> None:
        data = [instance.instance.cfg._asdict() for instance in self._tbs.values()]
        with open(self._db_path, "w") as handle:
            json.dump(data, handle)

    def get_instances(self) -> list[_Instance]:
        return [tb.instance for tb in self._tbs.values()]

    def launch(self, cfg: _Config) -> None:
        logdir = _make_logdir([Path(path) for path in cfg.paths])
        port = _find_port(port_lo=self._port_lo, port_hi=self._port_hi)
        if port < 0:
            msg = "Unable to find open port"
            print(msg, file=sys.stderr)
            return
        args = (
            self._tb_path,
            "--host",
            self._host,
            "--logdir",
            str(logdir),
            "--port",
            str(port),
            "--window_title",
            cfg.title,
        )
        proc = subprocess.Popen(args)
        instance = _Instance(cfg=cfg, ident=self._count, logdir=str(logdir), port=port)
        self._tbs[self._count] = _TensorBoard(instance=instance, proc=proc)
        self._count += 1

    def stop(self, instance_id: int) -> None:
        tb = self._tbs.pop(instance_id)
        proc = tb.proc
        proc.terminate()
        proc.wait()
        try:
            shutil.rmtree(tb.instance.logdir, ignore_errors=True)
        except Exception:
            pass

    def stop_all(self) -> None:
        # Copy the IDs so that we do not iterate over a collection that is changing
        instance_ids = list(self._tbs.keys())
        for instance_id in instance_ids:
            self.stop(instance_id)


@app.route("/cleanup")
def cleanup():
    global manager
    manager.stop_all()
    return redirect(url_for("index"))


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        paths_str = request.form.get("paths")
        title = request.form.get("title")
        if paths_str is None or title is None:
            msg = "Ignoring incorrect form submission"
            print(msg, file=sys.stderr)
        else:
            paths = [d for d in paths_str.splitlines()]
            manager.launch(cfg=_Config(paths=paths, title=title))
            manager.save()
            return redirect(url_for("index"))

    instances = manager.get_instances()
    return render_template("index.html", host=manager.host, instances=instances)


@app.route("/stop/<int:instance_id>")
def stop(instance_id: int):
    global manager
    manager.stop(instance_id)
    return redirect(url_for("index"))


def _handle_sigint(sig, frame):
    del sig, frame
    global manager
    manager.save()
    manager.stop_all()
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TensorBoard Manager")
    default_db_path = str(Path.home() / ".tbman.json")
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8093,
        help="tbman web server port",
    )
    parser.add_argument(
        "-L",
        "--low-port",
        type=int,
        default=8000,
        help="upper bound for ports for TensorBoard servers to listen on",
    )
    parser.add_argument(
        "-H",
        "--high-port",
        type=int,
        default=9000,
        help="lower bound for ports for TensorBoard servers to listen on",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="host for servers to listen on (use 0.0.0.0 to bind to all)",
    )
    parser.add_argument(
        "-s",
        "--session",
        type=str,
        default=default_db_path,
        help=f"path to session file (default: {default_db_path})",
    )
    parser.add_argument(
        "-t",
        "--tensorboard",
        type=str,
        default="tensorboard",
        help="path to tensorboard binary",
    )
    args = parser.parse_args()

    manager = _Manager(
        db_path=args.session,
        host=args.host,
        port_lo=args.low_port,
        port_hi=args.high_port,
        tb_path=args.tensorboard,
    )

    signal.signal(signal.SIGINT, _handle_sigint)

    app.run(host=args.host, port=args.port, use_reloader=False)
