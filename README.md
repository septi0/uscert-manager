# UsCert-Manager

## Description

**UsCert-Manager** is a simple certificate manager based on certbot and openssl. It is designed to manage let's encrypt or self-signed certificates for multiple domains and subdomains.

## Features

- Manage multiple domains and subdomains
- Generate and renew let's encrypt certificates
- Generate self-signed certificates

## Software requirements

- python3
- certbot
- openssl

## Installation

#### 1. As a package

```
pip install --upgrade <git-repo>
```

or 

```
git clone <git-repo>
cd <git-repo>
python setup.py install
```

#### 2. As a standalone script

```
git clone <git-repo>
```

## Usage

UsCert-Manager can be used in 3 ways:

#### 1. As a package (if installed globally)

```
/usr/bin/uscert-manager <parameters>
```

#### 2. As a package (if installed in a virtualenv)

```
<path-to-venv>/bin/uscert-manager <parameters>
```

#### 3. As a standalone script

```
<git-clone-dir>/run.py <parameters>
```

Check "Command line arguments" section for more information about the available parameters.

## Command line arguments

```
uscert-manager [-h] [--config-dir CONFIG_DIR] [--certs-dir CERTS_DIR] [--data-dir DATA_DIR] [--hooks-dir HOOKS_DIR] [--log LOG_FILE] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--bin-path BIN_PATH] [--version]

A simple certificate manager based on certbot and openssl

options:
  -h, --help            show this help message and exit
  --config-dir CONFIG_DIR
                        Config file(s) directory
  --certs-dir CERTS_DIR
                        Certs directory
  --data-dir DATA_DIR   Data directory
  --hooks-dir HOOKS_DIR
                        Hooks directory
  --log LOG_FILE        Log file where to write logs
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Log level
  --bin-path BIN_PATH   Path to binaries
  --version             show program's version number and exit

```

## Configuration file

For a sample configuration file see `config.sample.conf` file. Aditionally, you can copy the file to `/etc/uscert-manager/config.conf`, `/etc/opt/uscert-manager/config.conf` or `~/.config/uscert-manager/config.conf` (or where you want as long as you provide the `--config-dir` parameter) and adjust the values to your needs.

## Systemd service

To run UsCert-Manager as a service, have it start on boot and restart on failure, create a systemd service file in `/etc/systemd/system/uscert-manager.service` and copy the content from `uscert-manager.sample.service` file, adjusting the `ExecStart` parameter based on the installation method.

After that, run the following commands:

```
systemctl daemon-reload
systemctl enable usbackup.service
systemctl start usbackup.service
```

## Disclaimer

This software is provided as is, without any warranty. Use at your own risk. The author is not responsible for any damage caused by this software.

## License

This software is licensed under the GNU GPL v3 license. See the LICENSE file for more information.