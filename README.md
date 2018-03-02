# Terminus

A simple C/C++ package manager written in Python3, WORK IN PROGRESS.

## Install:
```
pip install terminus-tool
```

Create terminus.yaml:
```
---
dependencies:
  lua: 5.3.4
  
make:
  commands:
  - make -j$make_concurrency ROOT="$root" CFLAGS="-I./dependencies/include" LDFLAGS="-L./dependencies/lib"

remake:
  commands:
  - make clean
  - make -j$make_concurrency ROOT="$root" CFLAGS="-I./dependencies/include" LDFLAGS="-L./dependencies/lib"
```

Create a Makefile:
```
# GENERICS
ROOT_DIR := $(ROOT)
HEADERS_DIR = $(ROOT_DIR)/include
LIBS_DIR = $(ROOT_DIR)/lib
...
```

Run:
```
terminus install
terminus make
terminus remake
```























