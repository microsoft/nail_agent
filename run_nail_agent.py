#!/usr/bin/env python3

import argparse
import os, sys

from jericho import FrotzEnv
from agent.nail import NailAgent

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

parser = argparse.ArgumentParser(description='Run the NAIL agent on a game.')
parser.add_argument("game", type=str,
                    help="Path to game to run")
parser.add_argument("--steps", type=int, default=300,
                    help="Number of steps to run")
parser.add_argument("--seed", type=int, default=1010,
                    help="Random Seed")


def main():
    # Parse the arguments.
    args = parser.parse_args()

    # Create the environment.
    env = FrotzEnv(args.game, seed=args.seed)

    # Create the NAIL agent.
    agent = NailAgent(seed=args.seed, env=env, rom_name=os.path.basename(args.game))

    # Get the first observation from the environment.
    obs, info = env.reset()

    # Keep track of the maximum score achieved.
    max_score = 0

    # Run the agent on the environment for the specified number of steps.
    for step_num in range(args.steps):
        # Get one action from the agent.
        action = agent.take_action(obs)

        # Pass the action to the environment.
        new_obs, reward, done, info = env.step(action)
        max_score = max(info["score"], max_score)

        # Update the agent.
        agent.observe(obs, action, reward, new_obs, done)
        obs = new_obs

        # Output this step.
        print("Step {}   Action [{}]   Score {}\n{}".format(step_num, action, info["score"], obs))

        # Check for done (such as on death).
        if done:
            print("Environment returned done=True. So reset the environment.\n")
            obs, info = env.reset()

    # Clean up the agent.
    agent.finalize()

    print(f"Max score achieved: {max_score}")


if __name__ == "__main__":
    main()
