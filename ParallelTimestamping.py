#!/usr/bin/env python3

"""
Timestamp in parallel all the .jpgs from a directory
"""


import os
import sys
import yaml
import multiprocessing as mp
from multiprocessing import Value
import subprocess
import argparse
import atexit
import signal
import time


convert_params = ''
main_pid = None

flag = Value('i', 0)


def signal_handler(sig, frame):

    global flag

    print(f'{os.getpid()}: You pressed Ctrl+C!')
    if os.getpid() == main_pid:
        flag.value = 1
        sys.exit(0)
    else:
        return


def timestamp_file(file_queue, flag):
    """ Get file from queue and timestamp it """

    while flag.value == 0:

        filename = file_queue.get()

        print(filename)

        cmd = f'convert "{filename}" {convert_params} "{filename}"'
        #print(cmd)

        if subprocess.call(cmd, shell=True):
            print("Error processing file", filename)

        file_queue.task_done()

    print(f'{os.getpid()} worker process done!')


def timestamp(directory, concurrency):
    """ Timestamp files from directory """

    global flag

    file_queue = mp.JoinableQueue()

    for _ in range(concurrency):
        worker = mp.Process(target=timestamp_file, args=(file_queue, flag))
        worker.daemon = True
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

    global convert_params, main_pid
    main_pid = os.getpid()

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