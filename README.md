# Timelapse Utilities
Utilities and workflow for producing timelapses with Raspberry Pi.

Examples:
* [Snowstorm in London...](https://www.youtube.com/watch?v=IVVAfh1jaSY)
* [Night timelapse with infrared camera](https://www.youtube.com/watch?v=QOZFBpmTjF0) (babies dance a lot...)

For a start, an utility that adds a timestamp to every image within a directory. For thousands of images the processing can easily take 15 minutes if timestamping is done image after image. Taking advantage of multiple cores speeds up the processing.

There are two flavors: C++ and Python. The Python one is as fast as the C++ one (processing is IO bound and is done by convert below) but much, much simpler to implement.

Dependencies:
* [convert](http://www.imagemagick.org/script/convert.php) - [ImageMagick](http://www.imagemagick.org) utility

C++:
* C++11 compiler
* Compile: ``` g++ -std=c++11 -U__STRICT_ANSI__ -Wall -Wextra -O3 -o ParallelTimestamping ParallelTimestamping.cpp ```
* Run: ```ParallelTimestamping[.exe] [-h] || [<path>] || [<path> <number_threads>]```

Python:
* Python 3
* Run: ```python ParallelTimestamping.py <directory> [<concurrency>]```
