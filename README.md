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

## environment
- Python `3.11.8`
- WSL/Ubuntu `22.04.x` (should run on other platforms I guess but not thoroughly tested)
- virtualenv
  ```bash
  $ pyenv update
  $ pyenv install 3.11.8
  $ pyenv virtualenv 3.11.8 test-py-fastapi-queue
  $ pyenv activate test-py-fastapi-queue
  ```
- Install packages on virtualenv
  ```bash
  $ pip install -r requirements.txt
  ```

## vscode extension
- Commonly used extension for Python  
  - python   
    `ext install ms-python.python`   
  - pylance  
    `ext install ms-python.vscode-pylance`   
  - Black Formatter  
  - `ext install ms-python.black-formatter`   
- REST Client  
  `ext install humao.rest-client`

## Run the API server and how to test it
- First and foremost, activate the virtualenv.
- Run the API server by `python src/main.py`
- `testApi.http` is the file to test APIs using extension `REST Client`