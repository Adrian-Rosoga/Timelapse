/*

Add a timestamp to all timelapse images within a folder.

ParallelTimestamping[.exe] [-h] || [<path>] || [<path> <number_threads>]

*/

#include <thread>
#include <vector>
#include <iostream>
#include <string>
#include <algorithm>
#include <iterator>
#include <array>
#include <future>
#include <chrono>
#include <iomanip>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <signal.h>

const char* ConvertProgramPath = "/usr/bin/convert";
const char* ConvertProgramName = "convert";

volatile sig_atomic_t ctrl_c_received = 0;
thread_local unsigned int count = 0;

void signal_handler(int)
{
	ctrl_c_received = 1;
}

// Timestamp the file in a separate process
int timestampFile(const char* file)
{
    pid_t pid = fork();

    if (pid == -1)
    {
		perror("fork");
        exit(1);
    }

	if (pid == 0)
	{
		int rc = execl(ConvertProgramPath, ConvertProgramName,
						file,
						"-font", "courier-bold", "-pointsize", "36",
						"-fill", "white",
						"-undercolor", "black", "-gravity", "SouthEast",
						"-quality", "100",
						"-annotate", "+20+20", " %[exif:DateTimeOriginal] ",
						file, NULL);

		if (rc == -1)
		{
			perror("execl");
			exit(1);
		}
	}
	else
	{
		int status;
		pid_t child_pid = waitpid(pid, &status, 0);

		if (child_pid == -1)
		{
			perror("waitpid");
			exit(1);
		}
	}

	return 0;
}

using PairOutputReturnCode = std::pair<std::string, int>;

// Execute a program and return its output
PairOutputReturnCode exec(const char* cmd)
{
	std::shared_ptr<FILE> pipe(popen(cmd, "r"), pclose);
	if (!pipe) { return std::make_pair("", -1); }
    
    std::array<char, 128> buffer;
	std::string output;
	while (fgets(buffer.data(), buffer.size(), pipe.get()))
	{
		output += buffer.data();
	}
	return std::make_pair(output, 0);
}

// Simplified version of thread pool from https://github.com/Adrian-Rosoga/ThreadPool
class ThreadPool
{
public:
	explicit ThreadPool(int nbThreads) : shutdownFlag_(false), numberActiveWorkers_(0)
	{
		for (int i = 0; i < nbThreads; ++i)
		{
			++numberActiveWorkers_;
			workers_.emplace_back([this]()
			{
				std::function<void()> task;
				while (true)
				{
					{
						std::unique_lock<std::mutex> lock(mutex_);
						cond_var_.wait(lock, [this] { return !queue_.empty() || shutdownFlag_; });
						if (shutdownFlag_)
						{
							--numberActiveWorkers_;
							auto now = std::chrono::system_clock::now();
							auto now_c = std::chrono::system_clock::to_time_t(now);
							std::cout << "0x" << std::this_thread::get_id() << " thread finished at " << now_c
							          << " - Forced shutdown requested - Processed " << count << " tasks" << std::endl;
							return;
						}
						task = queue_.front();
						queue_.pop();
					}
					
					if (!task)
					{
						// Received an empty task, i.e. request of graceful shutdown
						--numberActiveWorkers_;
						auto now = std::chrono::system_clock::now();
						auto now_c = std::chrono::system_clock::to_time_t(now);
						std::cout << "0x" << std::this_thread::get_id() << " thread finished at " << now_c
						          << " - No more tasks - Processed " << count << " tasks" << std::endl;
						return;
					}
					++count;
					task();
				}
			});
		}
	}

	~ThreadPool()
	{
		request_shutdown();
		std::for_each(std::begin(workers_), std::end(workers_), std::mem_fn(&std::thread::join));
	}

	bool active() const
	{
		return numberActiveWorkers_ > 0;
	}

	// Request a forced shutdown even if there are unprocessed work items
	void request_forced_shutdown()
	{
		shutdownFlag_ = true;
	}

	// Request worker threads shutdown by enqueuing empty tasks
	void request_shutdown()
	{
		for (size_t i = 0; i < workers_.size(); ++i)
		{
			enqueue(std::function<void()>()); // Empty task is termination tasks
		}
	}

	void enqueue(const std::function<void()>& task)
	{
		if (shutdownFlag_) { return; }
		{
			std::lock_guard<std::mutex> guard(mutex_);
			queue_.push(task);
		}
		cond_var_.notify_one();
	}

	void enqueue(std::function<void()>&& task)
	{
		if (shutdownFlag_) { return; }
		{
			std::lock_guard<std::mutex> guard(mutex_);
			queue_.push(task);
		}
		cond_var_.notify_one();
	}

private:
	std::mutex mutex_;
	std::condition_variable cond_var_;
	std::queue<std::function<void()>> queue_;
	std::vector<std::thread> workers_;
	std::atomic_bool shutdownFlag_;
	std::atomic_int numberActiveWorkers_;
};

std::vector<std::string> tokenize(const std::string& str)
{
	std::vector<std::string> tokenized;
    const auto size = str.size();

	size_t pos_current = 0;
	while (true)
	{
		auto pos = str.find('\n', pos_current);

		if (pos != std::string::npos)
		{
			tokenized.push_back(str.substr(pos_current, pos - pos_current));
			pos_current = pos + 1;
		}
		else
		{
			if (pos_current != size)
			{
				tokenized.push_back(str.substr(pos_current, size));
			}
			break;
		}
	}

	return tokenized;
}

auto threadConvert = 
    [](const std::vector<std::string>& files)
	{
		int count = 0;
		std::for_each(std::begin(files), std::end(files), [&count](const std::string& file) { timestampFile(file.c_str()); ++count; });
		return count;
	};

// Using batching - split files in equal batches
void process_in_batches(int numberThreads, const std::vector<std::string>& files)
{
	const int noFiles = files.size();
	const int noFilesInBatch = noFiles / numberThreads;

	std::vector<std::vector<std::string>> batches(numberThreads);

	int batchCount = 0;
	int filesInBatch = 0;
	for (int i = 0; i < noFiles; ++i)
	{
		if ((batchCount != numberThreads - 1) && (filesInBatch == noFilesInBatch))
		{
			++batchCount;
			filesInBatch = 0;
		}
		batches[batchCount].push_back(files[i]);
		++filesInBatch;
	}

    // Worker threads
	std::vector<std::future<int>> futures;
	for (int i = 0; i < numberThreads; ++i)
	{
		std::cout << "Batch[" << i << "] size = " << batches[i].size() << std::endl;
		futures.push_back(std::async(std::launch::async, threadConvert, batches[i]));
	}

	std::cout << std::endl;

	// Pretty convoluted trick to print out the time when each worker thread finished
	std::vector<std::thread> resultThreads;
	for (int i = 0; i < numberThreads; ++i)
	{
		resultThreads.emplace_back([&futures, i]()
									{
										int const numberProcessedFiles = futures[i].get();
										auto now = std::chrono::system_clock::now();
										auto now_c = std::chrono::system_clock::to_time_t(now);												
										std::cout << "Thread " << i << " processed " << numberProcessedFiles << " files and finished at " << now_c
										          << std::endl;
									});
	}

	std::for_each(std::begin(resultThreads), std::end(resultThreads), std::mem_fn(&std::thread::join));
}

// Using a thread pool
void process_with_thread_pool(int numberThreads, const std::vector<std::string>& files)
{
	ThreadPool threadPool(numberThreads);

	for (auto& file : files)
	{
		threadPool.enqueue(std::bind(timestampFile, file.c_str()));
	}

	// Ask for thread pool shutdown after all work items are processed
	threadPool.request_shutdown();

	while (threadPool.active())
	{
		std::this_thread::sleep_for(std::chrono::milliseconds(100));

		if (ctrl_c_received)
		{
			std::cout << "Requesting forced thread pool shutdown." << std::endl;
			threadPool.request_forced_shutdown();
			std::cout << "Sleeping for 5 seconds... Why?" << std::endl;
			std::this_thread::sleep_for(std::chrono::seconds(5));
			break;
		}
	}
}

void usage(const char* programName)
{
	std::cout << "Usage: " << programName << "[-h] || [<path>] || [<path> <number_threads>]\n";
	std::cout << "Example: " << programName << " /cygdrive/c/timelapse_out/Ibiza 8\n";
}

int main(int argc, char** argv)
{
	std::string path;
	const int hardwareConcurrency = std::thread::hardware_concurrency();
	int numberThreads = hardwareConcurrency == 0 ? 2 : hardwareConcurrency; // 2 even if one core

	if (argc == 1)
	{
		path = ".";
	}

	if (argc == 2 && std::string(argv[1]) == "-h")
	{
		usage(argv[0]);
		return 0;
	}

	if (argc == 2 && std::string(argv[1]) != "-h")
	{
		path = argv[1];
	}

	if (argc == 3 && std::string(argv[1]) != "-h")
	{
		path = argv[1];
		numberThreads = atoi(argv[2]);
	}

	std::cout << "Hardware Concurrency = " << hardwareConcurrency
		      << "\nNumber threads to use = " << numberThreads << std::endl;

	std::string lsCommand = std::string("ls -1 ") + path + "/*.jpg";

	const PairOutputReturnCode output_return_code = exec(lsCommand.c_str());

    if (std::get<1>(output_return_code))
    {
        std::cerr << "Error: Cannot get files to timestamp" << std::endl;
        exit(1);
    }

    const std::string& images = std::get<0>(output_return_code);
	std::vector<std::string> files = tokenize(images);

	if (!files.empty())
	{
		std::cout << "\n" << files.size() << " files to process" << std::endl;
	}
	else
	{
		std::cout << "No files to process. Exiting." << std::endl;
		return 0;
	}
	
	signal(SIGINT, signal_handler);

#if 1
	std::cout << "Processing using thread pool." << std::endl;
	process_with_thread_pool(numberThreads, files);
#else
	std::cout << "Processing using equal batches." << std::endl;
	process_in_batches(numberThreads, files);
#endif

	return 0;
}