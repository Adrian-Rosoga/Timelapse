# timelapse
Utilities and workflow for producing timelapses with Raspberry Pi.

Examples:
* [London 28 January 2014] (https://www.youtube.com/watch?v=o3ewjVVeY2w)
* [Night timelapse with the infrared camera] (https://www.youtube.com/watch?v=QOZFBpmTjF0)

For a start, an utility that adds a timestamp to every image within a directory. For thousands of images the processing can easily take more than 15 minutes if timestamping is done serially. Taking advantage of multiple cores is a way to speed up the processing.

There are two flavors: C++ and Python. I started with the C++ one and then wondered how the Python version would perform.
The Python is as fast as the C++ one (as processing is IO bound) but much, much simpler.

Dependencies:
* 'convert' program - part of ImageMagick (http://www.imagemagick.org/script/convert.php)

C++ dependencies and details:
* A fairly recent C++ compiler - used gcc 5.3.0 on cygwin
* Compile: ``` g++ -std=c++11 -U__STRICT_ANSI__ -Wall -Wextra -O3 -o ParallelTimestamping ParallelTimestamping.cpp ```
* Run: ```ParallelTimestamping[.exe] [-h] || [<path>] || [<path> <number_threads>]```

Python dependencies and details:
* Python 2
* Run: ```python ParallelTimestamping.py <directory> [<concurrency>]```
