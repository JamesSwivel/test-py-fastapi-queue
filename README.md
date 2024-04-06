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

## test api
- `testApi.http` is the file to test APIs using extension `REST Client`