import logging
import os
import json
import shutil
import subprocess

class OpenSslProviderError(Exception):
    pass

class OpenSslProvider:
    def __init__(self, data_dir: str, bin_path: str, *, logger: logging.Logger) -> None:
        self._certs_dir = os.path.join(data_dir, 'certs')
        self._renewal_dir = os.path.join(data_dir, 'renewal_openssl')
        self._openssl_bin = 'openssl'
        
        self._logger = logger.getChild('openssl')
        
    def config_check(self, config: dict) -> None:
        required_keys = ['domains']
        
        # check if all required keys are present in config
        for key in required_keys:
            if not key in config:
                raise OpenSslProviderError(f'Config is missing required key "{key}"')
        
    def get_required_packages(self, config: dict) -> list:
        return []
    
    # generate self-signed certificate using .pem files
    def generate_cert(self, name: str, config: dict) -> int:
        required_keys = ['domains']
        
        # check if all required keys are present in config
        for key in required_keys:
            if not key in config:
                raise OpenSslProviderError(f'Config is missing required key "{key}"')
            
        target_dir = os.path.join(self._certs_dir, name)
        
        # create cert dir if it doesn't exist
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        # create renewal dir if it doesn't exist
        if not os.path.exists(self._renewal_dir):
            os.makedirs(self._renewal_dir)
            
        key_file = os.path.join(target_dir, 'private.pem')
        crt_file = os.path.join(target_dir, 'cert.pem')
        
        # parse int
        lifetime = int(config.get('days', 365))
        
        command = [
            'req',
            '-x509',
            '-nodes',
            '-days', str(lifetime),
            '-newkey', 'rsa:2048',
            '-keyout', key_file,
            '-out', crt_file,
            '-subj', f'/O=uscert-manager/CN={name}',
            '-addext', 'subjectAltName=DNS:{}'.format('\,DNS:'.join(config['domains'])),
        ]
        
        self._logger.info(f'Generating self-signed certificate for "{name}"')
        
        self._openssl_exec(command)
        
        # write generation config to renewal config file
        renewal_config_data = {
            'name': name,
            'domains': config['domains'],
            'days': lifetime,
        }
        
        self._write_renewal_config(name, renewal_config_data)
        
        self._gen_cert_variants(name)
            
        return lifetime
    
    def renew_cert(self, name: str, ) -> int:
        # read renewal config
        renewal_config = os.path.join(self._renewal_dir, f'{name}.conf')
        
        if not os.path.exists(renewal_config):
            raise OpenSslProviderError(f'No renewal config found for "{name}"')
        
        # parse renewal config file into dict
        with open(renewal_config, 'r') as f:
            renewal_data = json.loads(f.read())
            
        return self.generate_cert(name, renewal_data)
    
    def revoke_cert(self, name: str) -> None:
        # remove cert dir
        target_dir = os.path.join(self._certs_dir, name)
        
        if os.path.exists(target_dir):
            self._logger.info(f'Revoking certificate for "{name}"')
            shutil.rmtree(target_dir)
            
        # remove renewal config
        renewal_config = os.path.join(self._renewal_dir, f'{name}.conf')
        
        if os.path.exists(renewal_config):
            os.remove(renewal_config)
            
    def _write_renewal_config(self, name: str, data: dict) -> None:
        # write renewal config file
        with open(os.path.join(self._renewal_dir, f'{name}.conf'), 'w') as f:
            f.write(json.dumps(data))
            
    def _gen_cert_variants(self, name: str) -> None:
        target_dir = os.path.join(self._certs_dir, name)
        
        # create a combined.pem file
        with open(os.path.join(target_dir, 'combined.pem'), 'wb') as f:
            for file in ['cert.pem', 'private.pem']:
                with open(os.path.join(target_dir, file), 'rb') as src:
                    shutil.copyfileobj(src, f)
    
    def _openssl_exec(self, cmd: list) -> str:
        cmd_to_exec = [self._openssl_bin, *cmd]
        
        self._logger.debug(f'Executing command: {cmd_to_exec}')
        
        # create subprocess
        exec = subprocess.run(cmd_to_exec, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        self._logger.debug(f'Openssl command return code: {exec.returncode}')
        
        # if return code is not 0, raise error
        if exec.returncode != 0:
            error_msg = exec.stderr.decode().strip()
            raise OpenSslProviderError(f'Openssl command failed with return code {exec.returncode} ({error_msg})')
        
        return exec.stdout.decode().strip()