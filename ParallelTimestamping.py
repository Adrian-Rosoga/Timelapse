#!/usr/bin/env python3

"""
Timestamp in parallel all the .jpgs from a directory
"""


import argparse
import multiprocessing as mp
import os
import signal
import subprocess
import sys
from multiprocessing import Value
import yaml


g_finish_flag = Value('i', 0)


def signal_handler(sig, _):
    """ Handler for CTRL-C """

    global g_finish_flag

    if sig == signal.SIGINT:
        print('Ctrl+C pressed! Shutting down...')
        g_finish_flag.value = 1
        sys.exit(0)


def process_queue(file_queue, convert_params):
    """ Process queue """

    while g_finish_flag.value == 0:

        filename = file_queue.get()

        print(filename)

        cmd = f'convert "{filename}" {convert_params} "{filename}"'

        if subprocess.call(cmd, shell=True):
            print("Error processing file", filename)

        file_queue.task_done()

    print(f'{os.getpid()} worker process done!')


def timestamp(directory, concurrency, convert_params):
    """ Timestamp files from directory """

    file_queue = mp.JoinableQueue()

    for filename in os.listdir(directory):
        full_path = os.path.join(directory, filename)
        if os.path.isfile(full_path) and filename.lower().endswith('.jpg'):
            file_queue.put(full_path)

    print(f'\nConcurrency (worker processes): {concurrency}')
    print(f'Files to process: {file_queue.qsize()}')
    print(f'Directory: {directory}')

    for _ in range(concurrency):
        mp.Process(target=process_queue, args=(file_queue, convert_params), daemon=True).start()

    signal.signal(signal.SIGINT, signal_handler)

    file_queue.join()


def main():
    """ main """

    parser = argparse.ArgumentParser(description='Parallel Timestamping')
    parser.add_argument('directory', help='directory containing the jpgs')
    parser.add_argument('-c', '--concurrency', help='concurrency level')
    args = parser.parse_args()

    directory = args.directory
    path_to_config_file = os.path.join('/'.join(sys.argv[0].split('/')[0:-1]), 'config.yaml')

    with open(path_to_config_file) as config_file:
        data = yaml.full_load(config_file)
        print('"convert" parameters:', *data['convert_params'], sep='\n')

    convert_params = ' '.join(data['convert_params'])

    concurrency_level = int(args.concurrency) if args.concurrency else len(os.sched_getaffinity(0))

    timestamp(directory, concurrency_level, convert_params)


if __name__ == '__main__':
    main()
