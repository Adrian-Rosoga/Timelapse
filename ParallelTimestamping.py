#!/usr/bin/env python3

"""
Timestamp timelapse images.
Usage: python ParallelTimestamping.py <directory> [<concurrency>]
"""

import sys
import multiprocessing as mp
import subprocess
from os import listdir
from os.path import isfile, join


def timestamp_file(file_queue):
    """ Get file from queue and timestamp it """

    while True:

        item = file_queue.get()

        #cmd = "convert \"" + item + "\" -font courier-bold -pointsize 36 -fill white -undercolor black -gravity SouthEast\
        #       -quality 100 -annotate +20+20 \" %[exif:DateTimeOriginal] \" \"" + item + "\""
        cmd = f'convert "{item}" -font courier-bold -pointsize 36 -fill white -undercolor black -gravity SouthEast\
               -quality 100 -annotate +20+20 " %[exif:DateTimeOriginal] " "{item}"'

        if subprocess.call(cmd, shell=True):
            print("Error processing file", item)

        file_queue.task_done()

        
def timestamp(directory, concurrency):
    """ Timestamp files from directory """

    file_queue = mp.JoinableQueue()

    for _ in range(concurrency):
        worker = mp.Process(target=timestamp_file, args=(file_queue,))
        worker.daemon = True
        worker.start()

    count = 0
    for filename in listdir(directory):
        full_path = join(directory, filename)
        if isfile(full_path) and filename.lower().endswith('.jpg'):
            file_queue.put(full_path)
            count += 1

    print("\nWorker processes:", concurrency_level)
    print("Files to process:", count)
    print("Directory:", directory)
            
    file_queue.join()

    
if __name__ == "__main__":

    nb_args = len(sys.argv)
    directory = ''

    if nb_args == 2 or nb_args == 3:
        directory = sys.argv[1]
    else:
        print("\nUsage:", sys.argv[0], "<directory> [<concurrency>]")
        sys.exit(1)

    concurrency_level = int(sys.argv[2]) if nb_args == 3 else 4 # Default (guess)

    timestamp(directory, concurrency_level)
