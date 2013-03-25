mongoSuite
==========

Manage multiple instances of MongoDB on multiple hosts with one command line tool

## Features

* Deal with many host (node) via SSH
* Create instance of `MongoDB` on nodes
* Remote start/stop instances
* Check status of your instances

## Installation

### From PyPI
```
pip install mongoSuite
```

### From sources (devel version)
```
pip install git+https://github.com/william-p/mongoSuite.git
```

## Configuration

For init configuration file, you can run:
```
mongoSuite init
```

Now, you can configure `mongoSuite` on `~/mongoSuite/etc/mongoSuite.conf`

### Section: [mongoSuite]

`todo`

### Section: [node-<NAME>]

`todo`

### Section: [instance-<NAME>]

`todo`

## Screenshots

![Screenshot 01](https://raw.github.com/william-p/mongoSuite/master/screenshots/01.png)

![Screenshot 02](https://raw.github.com/william-p/mongoSuite/master/screenshots/02.png)

## License
License is AGPL3, it fully compatible with [`Canopsis`](https://github.com/capensis/canopsis). See LICENSE.
