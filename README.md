## Overview

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