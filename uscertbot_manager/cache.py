import os
import hashlib
import logging

class CertsCache:
    CACHE_MISS = 'MISS'
    CACHE_HIT = 'HIT'
    
    def __init__(self, data_dir: str, logger: logging.Logger) -> None:
        self._cache_dir = os.path.join(data_dir, 'cache')
        self._logger = logger.getChild('certs_cache')
        
    def set(self, name: str, members: list[str]) -> None:
        # sort members list to ensure consistent hash
        members_hash = hashlib.sha256(''.join(sorted(members)).encode()).hexdigest()
        
        # create cache dir if it doesn't exist
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)

        # write members hash to cache file
        cache_file = os.path.join(self._cache_dir, f'{name}.cache')
        with open(cache_file, 'w') as f:
            f.write(members_hash)
        
        self._logger.debug(f'Cache file created for "{name}"')
        
    def remove(self, name: str) -> None:
        # remove cache file
        cache_file = os.path.join(self._cache_dir, f'{name}.cache')
        if os.path.exists(cache_file):
            os.remove(cache_file)
        
        self._logger.debug(f'Cache file removed for "{name}"')

    def check(self, name: str, members: list[str]) -> str:
        # check if cache file exists with provided name.cache
        cache_file = os.path.join(self._cache_dir, f'{name}.cache')

        if not os.path.exists(cache_file):
            return self.CACHE_MISS
        
        # retrieve cache file content
        with open(cache_file, 'r') as f:
            cache_content = f.read().strip()

        # sort members list to ensure consistent hash
        members_hash = hashlib.sha256(''.join(sorted(members)).encode()).hexdigest()

        # check if cache content matches members hash
        if cache_content == members_hash:
            return self.CACHE_HIT
        
        return self.CACHE_MISS
    
    def get_all(self) -> list:
        # get all cache keys
        cache_keys = [x[:-6] for x in os.listdir(self._cache_dir) if x.endswith('.cache')]
        
        return cache_keys