import logging
import os
import shutil
import subprocess

class CertbotProviderError(Exception):
    pass

class CertbotProvider:
    def __init__(self, certs_dir: str, data_dir: str, bin_path: str, *, logger: logging.Logger) -> None:
        self._certs_dir = certs_dir
        self._data_dir = data_dir
        
        self._certbot_bin = os.path.join(bin_path, 'certbot') if bin_path else 'certbot'
        self._cert_lifetime = 90
        
        self._logger = logger.getChild('certbot')
        
        self._available_authenticators = self._get_authenticators()
        
    def config_check(self, config: dict) -> None:
        required_keys = ['authenticator', 'email', 'domains']
        
        # check if all required keys are present in config
        for key in required_keys:
            if not key in config:
                raise CertbotProviderError(f'Config is missing required key "{key}"')
        
    def get_required_packages(self, config: dict) -> list:
        pks = []
        
        if not config['authenticator'] in self._available_authenticators:
            pks.append(f'certbot-{config["authenticator"]}')
            
        return pks
        
    def generate_cert(self, name: str, config: dict) -> int:
        required_keys = ['authenticator', 'email', 'domains']
        
        # check if all required keys are present in config
        for key in required_keys:
            if not key in config:
                raise CertbotProviderError(f'Config is missing required key "{key}"')
        
        command = [
            'certonly',
            '--non-interactive',
            '--agree-tos',
            '--renew-with-new-domains',
            '--config-dir', self._data_dir,
            '--work-dir', self._data_dir,
            '--max-log-backups', '0',
            '--cert-name', name,
            '--domains', ','.join(config['domains']),
        ]
        
        disallowed_config_opts = [
            'provider',
            'non-interactive',
            'agree-tos',
            'renew-with-new-domains',
            'config-dir',
            'work-dir',
            'max-log-backups',
            'cert-name',
            'domains',
        ]
        
        # add config opts
        for key, value in config.items():
            if key in disallowed_config_opts:
                continue
            
            command.append(f'--{key}')
            command.append(value)
            
        self._logger.info(f'Generating certificate for "{name}". Members: {config["domains"]}')
            
        self._certbot_exec(command)
        
        self._copy_cert_files(name)
        
        return self._cert_lifetime
        
    def renew_cert(self, name: str) -> int:
        command = [
            'renew',
            '--non-interactive',
            '--no-random-sleep-on-renew',
            '--force-renewal',
            '--config-dir', self._data_dir,
            '--work-dir', self._data_dir,
            '--max-log-backups', '0',
            '--cert-name', name,
        ]
        
        self._logger.info(f'Renewing certificate for "{name}"')
        
        self._certbot_exec(command)
        
        self._copy_cert_files(name)
        
        return self._cert_lifetime
        
    def revoke_cert(self, name: str) -> None:
        command = [
            'revoke',
            '--non-interactive',
            '--delete-after-revoke',
            '--config-dir', self._data_dir,
            '--work-dir', self._data_dir,
            '--max-log-backups', '0',
            '--cert-name', name,
        ]
        
        self._logger.info(f'Removing certificate "{name}"')
        
        self._certbot_exec(command)
        
        self._remove_cert_files(name)
    
    def _get_authenticators(self) -> None:        
        # get authenticators list fro certbot cli
        certbot_authenticators = self._certbot_exec(['plugins', '--authenticators'])
        
        # keep only lines that start with * (plugin name)
        certbot_authenticators = [x.lstrip('*').strip() for x in certbot_authenticators.split('\n') if x.startswith('* ')]
        
        return certbot_authenticators

    def _copy_cert_files(self, name: str) -> None:
        le_dir = os.path.join(self._data_dir, 'live', name)
        target_dir = os.path.join(self._certs_dir, name)
        
         # create cert dir if it doesn't exist
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
        for file in os.listdir(le_dir):
            if file.endswith('.pem'):
                src_file = os.path.join(le_dir, file)
                dst_file = os.path.join(target_dir, file)
                
                self._logger.debug(f'Copying "{src_file}" to "{dst_file}"')
                
                shutil.copyfile(src_file, dst_file)
                
        self._gen_cert_variants(name)
                
    def _remove_cert_files(self, name: str) -> None:
        target_dir = os.path.join(self._certs_dir, name)
        
        if os.path.exists(target_dir):
            self._logger.debug(f'Removing certificate files for "{name}"')
            shutil.rmtree(target_dir)
            
    def _gen_cert_variants(self, name: str) -> None:
        target_dir = os.path.join(self._certs_dir, name)
        
        # create a combined.pem file
        with open(os.path.join(target_dir, 'combined.pem'), 'wb') as f:
            for file in ['fullchain.pem', 'privkey.pem']:
                with open(os.path.join(target_dir, file), 'rb') as src:
                    shutil.copyfileobj(src, f)
    
    def _certbot_exec(self, cmd: list) -> str:
        cmd_to_exec = [self._certbot_bin, *cmd]
        
        self._logger.debug(f'Executing command: {cmd_to_exec}')
        
        # create subprocess
        exec = subprocess.run(cmd_to_exec, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        self._logger.debug(f'certbot command return code: {exec.returncode}')
        
        # if return code is not 0, raise error
        if exec.returncode != 0:
            error_msg = exec.stderr.decode().strip()
            raise CertbotProviderError(f'certbot command failed with return code {exec.returncode} ({error_msg})')
        
        return exec.stdout.decode().strip()