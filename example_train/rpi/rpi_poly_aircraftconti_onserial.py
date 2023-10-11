#  Copyright (c). All Rights Reserved.
#  General Optimal control Problem Solver (GOPS)
#  Intelligent Driving Lab(iDLab), Tsinghua University
#
#  Creator: iDLab
#  Lab Leader: Prof. Shengbo Eben Li
#  Email: lisb04@gmail.com
#
#  Description: example for rpi + aircraftconti + poly + on_serial
#  Update Date: 2021-06-11, Li Jie: create example


import argparse
import os
import math
import numpy as np

from gops.create_pkg.create_alg import create_alg
from gops.create_pkg.create_buffer import create_buffer
from gops.create_pkg.create_env import create_env
from gops.create_pkg.create_evaluator import create_evaluator
from gops.create_pkg.create_sampler import create_sampler
from gops.create_pkg.create_trainer import create_trainer
from gops.utils.init_args import init_args
from gops.utils.plot_evaluation import plot_all
from gops.utils.tensorboard_setup import start_tensorboard, save_tb_to_csv

os.environ["OMP_NUM_THREADS"] = "1"

if __name__ == "__main__":
    # Parameters Setup
    parser = argparse.ArgumentParser()

    ################################################
    # Key Parameters for Users
    parser.add_argument("--env_id", type=str, default="pyth_aircraftconti", help="id of environment")
    parser.add_argument("--algorithm", type=str, default="RPI", help="RL algorithm")
    parser.add_argument("--enable_cuda", default=False, help="Disable CUDA")

    ################################################
    # 1. Parameters for environment
    parser.add_argument("--is_render", type=bool, default=False, help="Draw environment animation")
    parser.add_argument("--is_adversary", type=bool, default=True, help="Adversary training")
    parser.add_argument("--is_constrained", type=bool, default=False, help="Constrained training")

    ################################################
    # 2.1 Parameters of value approximate function
    parser.add_argument(
        "--value_func_name",
        type=str,
        default="StateValue",
        help="Options: StateValue/ActionValue/ActionValueDis/ActionValueDistri",
    )
    parser.add_argument(
        "--value_func_type", type=str, default="POLY", help="Options: MLP/CNN/CNN_SHARED/RNN/POLY/GAUSS"
    )
    parser.add_argument("--value_degree", type=int, default=2)
    parser.add_argument("--value_add_bias", type=bool, default=True)
    parser.add_argument(
        "--gt_weight", type=list, default=[1.657267, 2.790874, -0.332129, 1.657339, -0.360723, 0.437060]
    )

    # 2.2 Parameters of policy approximate function
    parser.add_argument(
        "--policy_func_name",
        type=str,
        default="DetermPolicy",
        help="Options: None/DetermPolicy/FiniteHorizonPolicy/StochaPolicy",
    )
    parser.add_argument(
        "--policy_func_type", type=str, default="POLY", help="Options: MLP/CNN/CNN_SHARED/RNN/POLY/GAUSS"
    )
    parser.add_argument(
        "--policy_act_distribution",
        type=str,
        default="default",
        help="Options: default/TanhGaussDistribution/GaussDistribution",
    )
    parser.add_argument("--policy_degree", type=int, default=1, help="degree of poly function")
    parser.add_argument("--policy_add_bias", type=bool, default=True, help="add 0 degree term")

    ################################################
    # 3. Parameters for algorithm
    parser.add_argument("--learning_rate", type=float, default=1e-3)
    parser.add_argument("--gamma_atte", type=float, default=5)

    ################################################
    # 4. Parameters for trainer
    parser.add_argument(
        "--trainer",
        type=str,
        default="on_serial_trainer",
        help="Options: on_serial_trainer, on_sync_trainer, off_serial_trainer, off_async_trainer",
    )
    # Maximum iteration number
    parser.add_argument("--max_newton_iteration", type=int, default=50)
    parser.add_argument("--max_step_update_value", type=int, default=10000)
    parser.add_argument("--max_iteration", type=int, default=parser.parse_args().max_newton_iteration)
    parser.add_argument(
        "--ini_network_dir",
        type=str,
        default=None)

    ################################################
    # 5. Parameters for sampler
    parser.add_argument("--sampler_name", type=str, default="on_sampler", help="Options: on_sampler/off_sampler")
    # Batch size of sampler for buffer store
    parser.add_argument("--sample_batch_size", type=int, default=64, help="Batch size of sampler for buffer store = 64")
    # Add noise to actions for better exploration
    parser.add_argument("--noise_params", type=dict, default=None, help="Add noise to actions for exploration")
    # Initial state
    parser.add_argument("--fixed_initial_state", type=list, default=[1.0, 1.5, 1.0], help="for env_data")
    parser.add_argument("--initial_state_range", type=list, default=[0.1, 0.2, 0.1], help="for env_model")
    # State threshold
    parser.add_argument("--state_threshold", type=list, default=[2.0, 2.0, 2.0])
    # Rollout steps
    parser.add_argument("--lower_step", type=int, default=200, help="for env_model")
    parser.add_argument("--upper_step", type=int, default=700, help="for env_model")
    parser.add_argument("--max_episode_steps", type=int, default=200, help="for env_data")

    ################################################
    # 6. Parameters for buffer
    parser.add_argument(
        "--buffer_name", type=str, default="replay_buffer", help="Options:replay_buffer/prioritized_replay_buffer"
    )
    # Size of collected samples before training
    parser.add_argument("--buffer_warm_size", type=int, default=parser.parse_args().sample_batch_size)
    # Max size of reply buffer
    parser.add_argument("--buffer_max_size", type=int, default=parser.parse_args().sample_batch_size)

    ################################################
    # 7. Parameters for evaluator
    parser.add_argument("--evaluator_name", type=str, default="evaluator")
    parser.add_argument("--num_eval_episode", type=int, default=1)
    parser.add_argument("--eval_interval", type=int, default=2)
    parser.add_argument("--print_interval", type=int, default=1)

    ################################################
    # 8. Data savings
    parser.add_argument("--save_folder", type=str, default=None)
    # Save value/policy every N updates
    parser.add_argument("--apprfunc_save_interval", type=int, default=10, help="Save value/policy every N updates")
    # Save key info every N updates
    parser.add_argument("--log_save_interval", type=int, default=1, help="Save data every N updates")

    ################################################
    # Get parameter dictionary
    args = vars(parser.parse_args())
    env = create_env(**args)
    args = init_args(env, **args)

    start_tensorboard(args['save_folder'])
    # Step 1: create algorithm and approximate function
    alg = create_alg(**args)
    # Step 2: create sampler in trainer
    sampler = create_sampler(**args)
    # Step 3: create buffer in trainer
    buffer = create_buffer(**args)
    # Step 4: create evaluator in trainer
    evaluator = create_evaluator(**args)
    # Step 5: create trainer
    trainer = create_trainer(alg, sampler, buffer, evaluator, **args)

    ################################################
    # Start training ... ...
    trainer.train()
    print("Training is finished!")

    ################################################
    # Plot and save training figures
    plot_all(args['save_folder'])
    save_tb_to_csv(args['save_folder'])
    print("Plot & Save are finished!")

