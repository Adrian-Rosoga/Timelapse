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

g_convert_params = ''
g_pid_main_process = None
g_finish_flag = Value('i', 0)


def signal_handler(sig, _):

    global g_finish_flag

    if sig == signal.SIGINT:
        print('Ctrl+C pressed! Shutting down...')
        if os.getpid() == g_pid_main_process:
            g_finish_flag.value = 1
            sys.exit(0)
        else:
            return


def timestamp_file(file_queue):
    """ Get file from queue and timestamp it """

    while g_finish_flag.value == 0:

        filename = file_queue.get()

        print(filename)

        cmd = f'convert "{filename}" {g_convert_params} "{filename}"'
        #print(cmd)

        if subprocess.call(cmd, shell=True):
            print("Error processing file", filename)

        file_queue.task_done()

    print(f'{os.getpid()} worker process done!')


def timestamp(directory, concurrency):
    """ Timestamp files from directory """

    file_queue = mp.JoinableQueue()

    workers = []
    for _ in range(concurrency):
        worker = mp.Process(target=timestamp_file, args=(file_queue,))
        worker.daemon = True
        workers.append(worker)
        worker.start()

    signal.signal(signal.SIGINT, signal_handler)

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

    global g_convert_params, g_pid_main_process
    g_pid_main_process = os.getpid()

    parser = argparse.ArgumentParser(description='Parallel Timestamping')
    parser.add_argument('directory', help='directory containing the jpgs')
    parser.add_argument('-c', '--concurrency', help='concurrency level')
    args = parser.parse_args()

    directory = args.directory

    path_to_config_file = os.path.join('/'.join(sys.argv[0].split('/')[0:-1]), 'config.yaml')

    with open(path_to_config_file) as config_file:
        data = yaml.full_load(config_file)

        print('"convert" parameters:')
        for convert_param in data['convert_params']:
            print(convert_param)

    g_convert_params = ' '.join(data['convert_params'])

    concurrency_level = int(args.concurrency) if args.concurrency else len(os.sched_getaffinity(0))

    timestamp(directory, concurrency_level)


if __name__ == '__main__':
    main()
