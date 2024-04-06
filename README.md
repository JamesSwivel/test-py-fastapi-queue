## Overview
A repo to demonstrate how to use Python to construct a FastAPI Server using advanced async and multi-threading approach.  There are a few highlights.
- Construct the API endpoint in async function
- The async API receives request payload and enqueue the item to a thread safe worker queue.
- After job submission, it waits for the result using `await`, i.e. wait in async way.  
  Thus, the request will **NOT** block the main thread, which means new incoming requests will **NOT** be blocked.
- A worker process, running in separated worker thread, and dequeue the job item and process it sequentially.
- The worker processes the job like simulating a CPU intensive task that may run for a few seconds.  
  Even though the worker may block self worker thread during the job processing, it will **NOT** block the main thread.
- Job item is a TypeDict that includes data payload and a asyncio.Future like JavaScript `promise`.  When the worker finishes the job processing, it will notify the result to the original API who is awaiting for the result.  
- If API finds the worker queue is already full, i.e. too many pending jobs, it may return HTTP status code `429 too many requests`. 
  
Use cases
- This repo uses single worker.  However, multiple workers running in multiple threads can be implemented in similar way.  Also, there can be multiple worker queues that the jobs can be delivered to different workers.
- The methodologies of this repo may be applied to some use case like `PaddleOCR` or `pdf-to-image` processing which are CPU intensive tasks by nature, but the processing should **NOT** block incoming http requests.


## Environment
- Python `3.11.8`
- `WSL/Ubuntu` 22.04.x or `Windows` 
- virtualenv using pyenv (Linux/Ubuntu)
  ```bash
  $ pyenv update
  $ pyenv install 3.11.8
  $ pyenv virtualenv 3.11.8 test-py-fastapi-queue
  $ pyenv activate test-py-fastapi-queue
  ```
- virtualenv using py (Windows)
  ```bat
  > cd <projectDir>
  > py -3.11.8 -m venv winEnv
  > winEnv\Scripts\activate
  ```
- Install packages on virtualenv
  ```bash
  $ pip install -r requirements.txt
  ```

## About fastapi package
- It is suggested to install by `pip install fastapi[all]` as it will include extra dependent packages like `uvicorn` and `uvloop` for optimal async performance
- This repo is based on a specific version `fastapi[all]==0.110.1`.  
  For details, refer to [requirements.txt](./requirements.txt)

## vscode extension
- Commonly used extension for Python  
  - python   
    `ext install ms-python.python`   
  - pylance  
    `ext install ms-python.vscode-pylance`   
  - Black Formatter  
  - `ext install ms-python.black-formatter`   
- REST Client (like postman)  
  `ext install humao.rest-client`

## Run the API server and how to test it
- First and foremost, activate the virtualenv.
- Run the API server by `python src/main.py`
- `testApi.http` is the file to test APIs using extension `REST Client`

## References
- https://superfastpython.com/thread-queue/
- https://superfastpython.com/thread-producer-consumer-pattern-in-python/ 
