import os
import logging
import glob
import datetime
import asyncio
import subprocess
from configparser import ConfigParser
from uscert_manager.store import CertsStore
from uscert_manager.pip_manager import PipManager
from uscert_manager.providers import list as providers

__all__ = ['UsCertManager', 'UsCertManagerError', 'UsCertManagerConfigError']

class UsCertManagerError(Exception):
    pass

class UsCertManagerConfigError(Exception):
    pass

class UsCertManager:
    def __init__(self, params: dict) -> None:        
        self._certs_dir = params.get('certs_dir', '/data')
        self._data_dir = params.get('data_dir', '/data')
        self._hooks_dir = params.get('hooks_dir', '/hooks')
        self._bin_path = params.get('bin_path', '')

        self._config = self._parse_config(params.get('config_dir', '/config'))

        self._logger: logging.Logger = self._gen_logger(params.get('log_file', ''), params.get('log_level', 'INFO'))
        self._certs_store = CertsStore(self._data_dir, logger=self._logger)
        self._cert_providers = {x: providers[x](self._certs_dir, self._data_dir, self._bin_path, logger=self._logger) for x in providers}
        self._pip_manager = PipManager(self._bin_path, logger=self._logger)

    def run(self) -> None:
        user = os.getuid()
        self._logger.info(f'Starting uscert-manager as user {user}')
        
        # make sure config is valid
        self._config_check()
        
        # make sure any additional packages are installed
        self._ensure_packages()
        
        # ensure all certs are generated
        self._sync_certs()
        
        # run forever as a service
        self._run_forever()

    def _parse_config(self, config_dir: str) -> dict:
        if not config_dir:
            raise UsCertManagerConfigError("No config directory specified")
        
        config_files = [
            *glob.glob(os.path.join(config_dir, '*.conf')),
        ]

        config_inst = ConfigParser()
        config_inst.read(config_files)

        # check if any config was found
        if not config_inst.sections():
            raise UsCertManagerConfigError("No config found")

        config = {}
        required_options = ['provider', 'domains']

        for section in config_inst.sections():
            section_data = {}

            # make sure we have all required options
            for option in required_options:
                if not config_inst.has_option(section, option):
                    raise UsCertManagerConfigError(f'Config section "{section}" is missing required option "{option}"')

            for key, value in config_inst.items(section):
                if key == 'domains':
                    # split value by comma and remove any leading/trailing whitespace
                    value = [x.strip() for x in value.split(',')]

                section_data[key] = value

            config[section] = section_data

        return config
    
    def _gen_logger(self, log_file: str, log_level: str) -> logging.Logger:
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        if not log_level in levels:
            log_level = "INFO"

        logger = logging.getLogger()
        logger.setLevel(levels[log_level])

        if log_file:
            handler = logging.FileHandler(log_file)
        else:
            handler = logging.StreamHandler()

        handler.setLevel(levels[log_level])
        handler.setFormatter(logging.Formatter(format))

        logger.addHandler(handler)

        return logger
    
    def _config_check(self) -> None:
        self._logger.info('Checking config ...')
        
        for config in self._config.values():
            provider = config.get('provider', '')
            
            if not provider in self._cert_providers:
                raise UsCertManagerConfigError(f'Provider "{provider}" not found')
            
            self._cert_providers[provider].config_check(config)
            
        self._logger.info('Config check passed')
    
    def _ensure_packages(self) -> None:
        self._logger.info('Ensuring required packages are installed')
        
        pks_needed = set()
        
        for config in self._config.values():
            provider = config['provider']
            
            pks = self._cert_providers[provider].get_required_packages(config)
            
            if pks:
                pks_needed.update(pks)
                
        self._logger.info(f'Packages needed: {pks_needed}. Installing them ...')
                
        for pk in pks_needed:
            self._pip_manager.install(pk)
    
    def _sync_certs(self) -> None:
        certs = self._certs_store.get_all()
        
        # loop through all cached certs and check if they are still present in config
        for cert in certs:
            
            if not cert['name'] in self._config:
                self._logger.debug(f"Cert \"{cert['name']}\" is no longer in config. Revoke needed")
                
                try:
                    self._revoke_cert(cert['name'], cert['provider'])
                except Exception as e:
                    self._logger.exception(f'Error revoking certs. Error: {e}', exc_info=True)
        
        # loop through all cert configured and ensure they have a cert
        for name, config in self._config.items():
            record_status = self._certs_store.check(name, config['domains'])

            if record_status == CertsStore.CACHE_MISS:
                self._logger.debug(f'Cert "{name}" is stale. (re)gen needed')
                
                try:
                    self._generate_cert(name, config['provider'], config)
                except Exception as e:
                    self._logger.exception(f'Error generating certs. Error: {e}', exc_info=True)
            else:
                self._logger.debug(f'Cert "{name}" is up to date')
                
    def _renew_certs(self) -> None:
        certs = self._certs_store.get_due_certs(30)
        
        # loop through all certs that are due for renewal
        for cert in certs:
            self._logger.debug(f"Cert \"{cert['name']}\" is due for renewal")
            
            name = cert['name']
            provider = cert['provider']
                
            try:
                self._renew_cert(name, provider)
            except Exception as e:
                self._logger.exception(f'Error renewing certs. Error: {e}', exc_info=True)

    def _generate_cert(self, name: str, provider: str, config: dict) -> None:
        lifetime = self._cert_providers[provider].generate_cert(name, config)
        
        data = {
            'provider': provider,
            'domains': config['domains'],
            'expiry_date': (datetime.datetime.now() + datetime.timedelta(days=lifetime)).isoformat(),
        }
        
        self._certs_store.replace(name, **data)
        
        self._run_hook('post_cert_gen', name)
            
    def _renew_cert(self, name: str, provider: str) -> None:
        lifetime = self._cert_providers[provider].renew_cert(name)
            
        data = {
            'expiry_date': (datetime.datetime.now() + datetime.timedelta(days=lifetime)).isoformat(),
        }
        
        self._certs_store.update(name, **data)
        
        self._run_hook('post_cert_gen', name)
        
    def _revoke_cert(self, name: str, provider: str) -> None:
        self._cert_providers[provider].revoke_cert(name)
        
        self._certs_store.remove(name)
        
        self._run_hook('post_cert_revoke', name)
        
    def _run_hook(self, hook: str, name: str) -> None:
        hook_dir = os.path.join(self._hooks_dir, hook)
        
        if not os.path.exists(hook_dir):
            return
        
        self._logger.info(f'Running hook "{hook}" for "{name}"')
        
        # call run-parts on hook dir
        cmd_to_exec = ['run-parts', hook_dir, '--arg', name]
        
        self._logger.debug(f'Executing command: {cmd_to_exec}')
        
        # create subprocess
        exec = subprocess.run(cmd_to_exec, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        self._logger.debug(f'run-parts command return code: {exec.returncode}')
        
        # if return code is not 0, raise error
        if exec.returncode != 0:
            error_msg = exec.stderr.decode().strip()
            raise UsCertManagerError(f'Error running hook "{hook}": {error_msg}')
        
        return exec.stdout.decode().strip()
        
    def _run_forever(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        tasks = [
            loop.create_task(self._renew_certs_task()),
        ]

        try:
            loop.run_until_complete(asyncio.gather(*tasks))
        except (KeyboardInterrupt, SystemExit):
            self._logger.info('Received termination signal')
        except Exception as e:
            self._logger.exception(e, exc_info=True)
        finally:
            try:
                self._logger.info("Shutting down")

                self._cancel_tasks(loop)
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                asyncio.set_event_loop(None)
                loop.close()
                
    def _cancel_tasks(self, loop: asyncio.AbstractEventLoop) -> None:
        tasks = asyncio.all_tasks(loop=loop)

        if not tasks:
            return

        for task in tasks:
            task.cancel()

        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

        for task in tasks:
            if task.cancelled():
                continue

            if task.exception() is not None:
                loop.call_exception_handler({
                    'message': 'Unhandled exception during task cancellation',
                    'exception': task.exception(),
                    'task': task,
                })
        
    async def _renew_certs_task(self) -> None:
        while True:
            # run renew certs as an asyncio task
            await asyncio.to_thread(self._renew_certs)
            
            # sleep until 02:00
            now = datetime.datetime.now()
            next_run = datetime.datetime(now.year, now.month, now.day, 2, 0)
            
            if now > next_run:
                next_run += datetime.timedelta(days=1)
                
            sleep_time = (next_run - now).seconds
            
            self._logger.info(f'Next certs check in {sleep_time} seconds')
            
            await asyncio.sleep(sleep_time)