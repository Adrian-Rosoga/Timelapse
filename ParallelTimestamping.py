#!/usr/bin/env python3

"""
Timestamp in parallel all the .jpgs from a directory
"""


import os
import multiprocessing as mp
import subprocess
import argparse


def timestamp_file(file_queue):
    """ Get file from queue and timestamp it """

    while True:

        filename = file_queue.get()

        cmd = f'convert "{filename}" -font courier-bold -pointsize 36 -fill white -undercolor black -gravity SouthEast\
               -quality 100 -annotate +20+20 " %[exif:DateTimeOriginal] " "{filename}"'

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

    print("\nConcurrency (worker processes):", concurrency_level)
    print("Files to process:", count)
    print("Directory:", directory)

    file_queue.join()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Parallel Timestamping')
    parser.add_argument('directory', help='directory containing the jpgs')
    parser.add_argument('-c', '--concurrency', help='concurrency level')
    args = parser.parse_args()

    directory = args.directory

    concurrency_level = int(args.concurrency) if args.concurrency else len(os.sched_getaffinity(0))

    timestamp(directory, concurrency_level)
