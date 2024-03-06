#!/usr/bin/env python
import sys
import yaml
import glob
import os

RUN_DIRS = ["RUN1", "RUN2", "RUN3"]
RUN_DIRS = ["RUN1", "RUN2", "RUN3"]


def to_tuple(numbers, round_to=3):
    import statistics

    print(len(numbers))

    mean = round(statistics.mean(numbers), round_to)
    median = round(statistics.median(numbers), round_to)
    amin = round(min(numbers), round_to)
    amax = round(max(numbers), round_to)
    return tuple([amin, amax, median, mean])


def check_stats(results_dir, prefix):
    rundirs = RUN_DIRS

    dir_paths = []

    for run_dir in rundirs:
        temp = os.path.join(results_dir, run_dir, "*" + prefix + "*")
        temp_dir_paths = glob.glob(temp)

        if not temp_dir_paths:
            print(f"Did not find matching directories using pattern {temp} Exiting ...")
            sys.exit(1)

        dir_paths.extend(temp_dir_paths)

    for dir_path in dir_paths:
        has_failures = False

        for action in ["apply"]:
            file_path = os.path.join(dir_path, "stats-" + action + ".yml")

            with open(file_path, 'r') as stream:
                ret = yaml.load(stream, Loader=yaml.SafeLoader)

                if not ret:
                    # print(f"No stats in {file_path}. Exiting ...")
                    has_failures = True

                # print(file_path)
                if ret['stats']['has_failures']:
                    # print(f"Found failures in {file_path}. Exiting ...")
                    has_failures = True

        # if has_failures:
        #     sys.exit(1)


def print_stats_for_action(results_dir, prefix, action):
    rundirs = RUN_DIRS

    dir_paths = []

    for run_dir in rundirs:
        temp = os.path.join(results_dir, run_dir, "*" + prefix + "*")
        temp_dir_paths = glob.glob(temp)
        dir_paths.extend(temp_dir_paths)

    provider_stats_map = dict()
    workflow_durations = list()

    for dir_path in dir_paths:
        file_path = os.path.join(dir_path, "stats-" + action + ".yml")
        with open(file_path, 'r') as stream:
            ret = yaml.load(stream, Loader=yaml.SafeLoader)
            provider_stats = ret["stats"]['provider_stats']
            workflow_durations.append(ret['stats']['workflow_duration']['duration'])

            for stats in provider_stats:
                provider = stats['provider']
                provider_duration = stats['provider_duration']['duration']
                #
                # if 'fabric' in provider:
                #     # print(file_path, ":", provider_duration)
                #     continue

                if stats["has_failures"]:
                    print(stats["has_failures"], file_path, provider_duration)

                if provider_duration < 250:
                     continue

                if provider_duration > 600:
                    print("too a long time", file_path, provider_duration)



                if not provider_stats_map.get(provider):
                    provider_stats_map[provider] = list()
                provider_stats_map[provider].append(provider_duration)

    print("\tMIN, MAX, MEDIAN, MEAN IN SECONDS")
    for provider in provider_stats_map:
        temp = to_tuple(provider_stats_map[provider])
        print("\t" + provider + ":", str(temp))

    # print("\tworkflow_duration: ", to_tuple(workflow_durations))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Provide a result directory and a pattern matchin subdirectories .... Exiting")
        sys.exit(3)

    check_stats(sys.argv[1], sys.argv[2])
    print("****************** BEGIN HELLO *********************")
    print("Using", sys.argv[1], sys.argv[2])
    print("APPLY:")
    print_stats_for_action(sys.argv[1], sys.argv[2], 'apply')
    print()
    # print("DESTROY:")
    # print_stats_for_action(sys.argv[1], sys.argv[2], 'destroy')
    print("****************** END *********************")
