#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys
import yaml

import ray
from ray.tune.config_parser import make_parser, resources_to_json
from ray.tune.tune import _make_scheduler, run_experiments


EXAMPLE_USAGE = """
Training example:
    ./train.py --run DQN --env CartPole-v0

Grid search example:
    ./train.py -f tuned_examples/cartpole-grid-search-example.yaml

Note that -f overrides all other trial-specific command-line options.
"""


parser = make_parser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description="Train a reinforcement learning agent.",
    epilog=EXAMPLE_USAGE)

# See also the base parser definition in ray/tune/config_parser.py
parser.add_argument(
    "--cluster", action='store_true')
parser.add_argument(
    "--ray-num-cpus", default=None, type=int,
    help="--num-cpus to pass to Ray. This only has an affect in local mode.")
parser.add_argument(
    "--ray-num-gpus", default=None, type=int,
    help="--num-gpus to pass to Ray. This only has an affect in local mode.")
parser.add_argument(
    "--experiment-name", default="default", type=str,
    help="Name of the subdirectory under `local_dir` to put results in.")
parser.add_argument(
    "--env", default=None, type=str, help="The gym environment to use.")
parser.add_argument(
    "--queue-trials", action='store_true',
    help=(
        "Whether to queue trials when the cluster does not currently have "
        "enough resources to launch one. This should be set to True when "
        "running on an autoscaling cluster to enable automatic scale-up."))
parser.add_argument(
    "-f", "--config-file", default=None, type=str,
    help="If specified, use config options from this file. Note that this "
    "overrides any trial-specific options set via flags above.")


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    if args.config_file:
        with open(args.config_file) as f:
            experiments = yaml.load(f)
    else:
        # Note: keep this in sync with tune/config_parser.py
        experiments = {
            args.experiment_name: {  # i.e. log to ~/ray_results/default
                "run": args.run,
                "checkpoint_freq": args.checkpoint_freq,
                "local_dir": args.local_dir,
                "trial_resources": (
                    args.trial_resources and
                    resources_to_json(args.trial_resources)),
                "stop": args.stop,
                "config": dict(args.config, env=args.env),
                "restore": args.restore,
                "repeat": args.repeat,
                "upload_dir": args.upload_dir,
            }
        }

    for exp in experiments.values():
        if not exp.get("run"):
            parser.error("the following arguments are required: --run")
        if not exp.get("env") and not exp.get("config", {}).get("env"):
            parser.error("the following arguments are required: --env")

    from ray.tune.async_hyperband import AsyncHyperBandScheduler
    sched = AsyncHyperBandScheduler(grace_period=3, reduction_factor=4)

    ray.init(
        redis_address="localhost:6379" if args.cluster else None,
        num_cpus=args.ray_num_cpus, num_gpus=args.ray_num_gpus, redirect_output=True)
    run_experiments(
        experiments, scheduler=sched,
        queue_trials=args.queue_trials)
