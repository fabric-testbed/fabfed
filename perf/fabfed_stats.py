#!/usr/bin/env python
import sys
import yaml
import glob
import os


def to_tuple(numbers, round_to=3):
    import statistics

    mean = round(statistics.mean(numbers), round_to)
    median = round(statistics.median(numbers), round_to)
    amin = round(min(numbers), round_to)
    amax = round(max(numbers), round_to)
    return tuple([amin, amax, median, mean])


def check_stats(results_dir, prefix):
    dir_paths = glob.glob(os.path.join(results_dir, prefix + "*"))

    if not dir_paths:
        print(f"Did not find matching directories under {results_dir} using pattern {prefix}. Exiting ...")
        sys.exit(1)

    for dir_path in dir_paths:
        for action in ["apply", "destroy"]:
            file_path = os.path.join(dir_path, "stats-" + action + ".yml")

            with open(file_path, 'r') as stream:
                ret = yaml.load(stream, Loader=yaml.SafeLoader)

                if ret['stats']['has_failures']:
                    print(f"Found failures in {file_path}. Exiting ...")
                    sys.exit(2)


def print_stats_for_action(results_dir, prefix, action):
    dir_paths = glob.glob(os.path.join(results_dir, prefix + "*"))
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

                if not provider_stats_map.get(provider):
                    provider_stats_map[provider] = list()
                provider_stats_map[provider].append(provider_duration)

    print("\tMIN, MAX, MEDIAN, MEAN IN SECONDS")
    for provider in provider_stats_map:
        temp = to_tuple(provider_stats_map[provider])
        print("\t" + provider + ":", str(temp))

    print("\tworkflow_duration: ", to_tuple(workflow_durations))
    
def write_stats_for_action_to_csv(results_dir, prefix, csv_dir):
    
    dir_paths = glob.glob(os.path.join(results_dir, prefix + "*"))
    
    record_table = list()
    for index in range(0, len(dir_paths)):
        record={}
        dir_path = dir_paths[index]
        record['workflow_index']= index+1
        for action in ['apply', 'destroy']:
            file_path = os.path.join(dir_path, "stats-" + action + ".yml")
            with open(file_path, 'r') as stream:
                ret = yaml.load(stream, Loader=yaml.SafeLoader)
                provider_stats = ret["stats"]['provider_stats']
                if action == 'apply':
                    record['workflow_apply']=ret['stats']['workflow_duration']['duration']
                    providers=[]
                    for stats in provider_stats:
                        provider = stats['provider']
                        providers.append(provider)
                        if 'fabric_provider' in provider:
                            record['fabric_apply'] = stats['provider_duration']['duration']
                        else:
                            record['remote_apply'] = stats['provider_duration']['duration']
                            
                    record['senario']='.'.join(providers)
                    record['concurrency']=len(dir_paths)

                elif action == 'destroy':
                    record['workflow_destroy']=ret['stats']['workflow_duration']['duration']
                    for stats in provider_stats:
                        provider = stats['provider']
                        if 'fabric_provider' in provider:
                            record['fabric_destroy'] = stats['provider_duration']['duration']
                        else:
                            record['remote_destroy'] = stats['provider_duration']['duration']
                else:
                    raise Exception("Illegal")
        record_table.append(record)
    
    title = ['senario', 'concurrency', 'workflow_index', 'workflow_apply', 'workflow_destroy', 'fabric_apply', 'fabric_destroy', 'remote_apply', 'remote_destroy']
    with open(csv_dir, 'w') as csv_file:
        csv_file.write(','.join(title))
        csv_file.write('\n')
        for record in record_table:
            x=[record[k] if isinstance(record[k],str) else str(record[k]) for k in title]
            csv_file.write(','.join(x))
            csv_file.write("\n")
        
        


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Provide a result directory and a pattern matchin subdirectories .... Exiting")
        print("example: fabfed_stats /tmp gcpx mydata.csv")
        sys.exit(3)

    check_stats(sys.argv[1], sys.argv[2])
    print("****************** BEGIN *********************")
    print("Using", sys.argv[1], sys.argv[2])
    print("APPLY:")
    print_stats_for_action(sys.argv[1], sys.argv[2], 'apply')
    print()
    print("DESTROY:")
    print_stats_for_action(sys.argv[1], sys.argv[2], 'destroy')
    print("****************** END *********************")
    
    if len(sys.argv) > 3:
        write_stats_for_action_to_csv(sys.argv[1], sys.argv[2], sys.argv[3])
