import os
import logging
import glob
import datetime
import asyncio
from configparser import ConfigParser
from uscertbot_manager.cache import CertsCache
from uscertbot_manager.certbot import Certbot
from uscertbot_manager.pip_manager import PipManager

__all__ = ['UsCertbotManager', 'UsCertbotManagerError', 'UsCertbotManagerConfigError']

class UsCertbotManagerError(Exception):
    pass

class UsCertbotManagerConfigError(Exception):
    pass

class UsCertbotManager:
    def __init__(self, params: dict) -> None:
        self._logger: logging.Logger = self._gen_logger(params.get('log_file', ''), params.get('log_level', 'INFO'))
        self._config = self._parse_config(params.get('config_dir', '/config'))
        self._data_dir = params.get('data_dir', '/data')

        self._certs_cache = CertsCache(self._data_dir, logger=self._logger)
        self._certbot = Certbot(self._data_dir, params.get('certbot_bin'), logger=self._logger)
        self._pip_manager = PipManager(params.get('pip_bin'), logger=self._logger)

    def run(self) -> None:
        user = os.getuid()
        self._logger.debug(f'Starting uscertbot-manager as user {user}')
        # install any required plugins
        self._ensure_plugins()
        
        # ensure all certs are generated
        self._sync_certs()
        
        # run forever as a service
        self._run_forever()

    def _parse_config(self, config_dir: str) -> dict:
        if not config_dir:
            raise UsCertbotManagerConfigError("No config directory specified")
        
        config_files = [
            *glob.glob(os.path.join(config_dir, '*.conf')),
        ]

        config_inst = ConfigParser()
        config_inst.read(config_files)

        # check if any config was found
        if not config_inst.sections():
            raise UsCertbotManagerConfigError("No config found")

        config = {}
        required_options = ['authenticator', 'domains', 'email']

        for section in config_inst.sections():
            section_data = {}

            # make sure we have all required options
            for option in required_options:
                if not config_inst.has_option(section, option):
                    raise UsCertbotManagerConfigError(f'Config section "{section}" is missing required option "{option}"')

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
    
    def _ensure_plugins(self) -> None:
        # get all unique authenticators from config
        conf_authenticators = set([x['authenticator'] for x in self._config.values()])
        
        certbot_authenticators = self._certbot.get_authenticators()
        
        # loop through all config authenticators and ensure they are installed
        for authenticator in conf_authenticators:
            if not authenticator in certbot_authenticators:
                self._logger.info(f'Installing plugin certbot-"{authenticator}"')
                
                self._pip_manager.install(f'certbot-{authenticator}')
    
    def _sync_certs(self) -> None:
        cached_certs = self._certs_cache.get_all()
        
        # loop through all cached certs and check if they are still present in config
        for name in cached_certs:
            
            if not name in self._config:
                self._logger.debug(f'Cert group "{name}" is no longer in config. Revoke needed')
                
                self._revoke_cert(name)
        
        # loop through all cert configured and ensure they have a cert
        for group, config in self._config.items():
            cache_status = self._certs_cache.check(group, config['domains'])

            if cache_status == CertsCache.CACHE_MISS:
                self._logger.debug(f'Cert group "{group}" is stale. (re)gen needed')
                
                try:
                    self._generate_cert(group, config)
                except Exception as e:
                    self._logger.error(f'Error generating certs. Error: {e}')
            else:
                self._logger.debug(f'Cert group "{group}" is up to date')

    def _generate_cert(self, group: str, config: dict) -> None:
        self._certbot.generate_cert(group, config)
        
        self._certs_cache.set(group, config['domains'])
        
    def _renew_certs(self) -> None:
        self._certbot.renew_certs()
        
    def _revoke_cert(self, name: str) -> None:
        self._certbot.revoke_cert(name)
        
        self._certs_cache.remove(name)
        
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
            
            self._logger.debug(f'Next renew certs run in {sleep_time} seconds')
            
            await asyncio.sleep(sleep_time)