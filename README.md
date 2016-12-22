# Qrtmp

### What is this?

Qrtmp ("Quick RTMP") is a lightweight package to interface, as a client, with applications and platforms (e.g. servers) that work by using the Real Time Message Protocol. 

This package is aimed at maintaing this aged protocol and keeping it up-to-date in comparison to the older libraries that are available to use out there (for client purposes) for the Python language.

Originally adapted from [Prekageo's rtmp-python](https://github.com/prekageo/rtmp-python/) (which was derived from the [RTMPy](https://github.com/hydralabs/rtmpy) project), this library provides various layers of abstraction to allow the user to interface more directly with any application they want connect to and transfer data over.

### Dependencies

The only dependency at the moment is that the package can only be used with Python 2.7 (10+) which can be downloaded from [python.org](https://www.python.org/downloads/).

### Installation

The package can be installed simply by executing:

```python
>>> python setup.py install
```

### Example

To demonstrate some basic functionality, a very basic RTMP connection is illustrated within the [*rtmp_connect.py*](https://github.com/) script.

### Usage

