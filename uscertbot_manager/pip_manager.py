import logging
import subprocess

class PipManagerError(Exception):
    pass

class PipManager:
    def __init__(self, pip_bin: str, logger: logging.Logger) -> None:
        self._pip_bin = pip_bin if pip_bin else 'pip3'
        
        self._logger = logger.getChild('pip_manager')
        
    def install(self, package: str) -> None:
        # ensure only alphanumeric and hyphen characters are present
        if not package.replace('-', '').isalnum():
            raise PipManagerError(f'Invalid package name "{package}"')
        
        self._logger.info(f'Installing package "{package}"')
        
        command = ['install', package]
        
        self._pip_exec(command)
        
    def _pip_exec(self, cmd: list) -> str:
        cmd_to_exec = [self._pip_bin, *cmd]
        
        self._logger.debug(f'Executing command: {cmd_to_exec}')
        
        # create subprocess
        exec = subprocess.run(cmd_to_exec, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        self._logger.debug(f'Pip command return code: {exec.returncode}')
        
        # if return code is not 0, raise error
        if exec.returncode != 0:
            error_msg = exec.stderr.decode().strip()
            raise PipManagerError(f'Pip command failed with return code {exec.returncode} ({error_msg})')
        
        return exec.stdout.decode().strip()