#!/usr/bin/env python3

"""
Timestamp in parallel all the .jpgs from a directory
"""


import os
import sys
import yaml
import multiprocessing as mp
import subprocess
import argparse


convert_params = ''


def timestamp_file(file_queue):
    """ Get file from queue and timestamp it """

    while True:

        filename = file_queue.get()

        cmd = f'convert "{filename}" {convert_params} "{filename}"'
        #print(cmd)

        if subprocess.call(cmd, shell=True):
            print("Error processing file", filename)

        file_queue.task_done()


def timestamp(directory, concurrency):
    """ Timestamp files from directory """

    file_queue = mp.JoinableQueue()

    for _ in range(concurrency):
        worker = mp.Process(target=timestamp_file, args=(file_queue,))
        worker.daemon = True
        worker.start()

    count = 0
    for filename in os.listdir(directory):
        full_path = os.path.join(directory, filename)
        if os.path.isfile(full_path) and filename.lower().endswith('.jpg'):
            file_queue.put(full_path)
            count += 1

    print(f'\nConcurrency (worker processes): {concurrency}')
    print(f'Files to process: {count}')
    print(f'Directory: {directory}')

    file_queue.join()


def main():

    global convert_params

    parser = argparse.ArgumentParser(description='Parallel Timestamping')
    parser.add_argument('directory', help='directory containing the jpgs')
    parser.add_argument('-c', '--concurrency', help='concurrency level')
    args = parser.parse_args()

    directory = args.directory

    path_to_config_file = os.path.join('/'.join(sys.argv[0].split('/')[0:-1]), 'config.yaml')

    with open(path_to_config_file) as config_file:
        data = yaml.full_load(config_file)

        for convert_param in data['convert_params']:
            print(convert_param)

    convert_params = ' '.join(data['convert_params'])

    concurrency_level = int(args.concurrency) if args.concurrency else len(os.sched_getaffinity(0))

    timestamp(directory, concurrency_level)


if __name__ == '__main__':
    main()