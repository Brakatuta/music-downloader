import threading

# ThreadPool class
# max workers: maximum number of threads to be created
# max retries: maximum number of retries for each thread
class ThreadPool:
    def __init__(self, max_workers, max_retries=3):
        print("Setting up thread pool with max workers:", max_workers, "and max retries:", max_retries)

        self.max_workers = max_workers
        self.max_retries = max_retries
        self.threads = []
        self.queue = []
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)

    def submit(self, func, args):
        with self.lock:
            self.queue.append((func, args, 0))  # Initial retry count is 0
            self._start_next_thread()

    def _start_next_thread(self):
        if len(self.threads) < self.max_workers and self.queue:
            func, args, retry_count = self.queue.pop(0)
            thread = threading.Thread(target=self._worker, args=(func, args, retry_count))
            thread.start()
            self.threads.append(thread)

    def _worker(self, func, args, retry_count):
        try:
            func(*args)
        except Exception as e:
            print(f"Error in thread: {e}")
            with self.condition:
                if retry_count < self.max_retries:
                    print(f"Retrying {args} (attempt {retry_count + 1})")
                    self.queue.append((func, args, retry_count + 1))
                else:
                    print(f"Max retries reached for {args}")
        finally:
            self.finish_thread()

    def finish_thread(self):
        with self.condition:
            current_thread = threading.current_thread()
            self.threads.remove(current_thread)
            self._start_next_thread()
            self.condition.notify()

    def join(self):
        with self.condition:
            while self.threads or self.queue:
                self.condition.wait()

def set_up_thread_pool(max_workers, max_retries):
    return ThreadPool(max_workers, max_retries)