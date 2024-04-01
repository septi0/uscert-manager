import os
import sqlite3
import hashlib
import json
import logging

class CertsStore:
    CACHE_MISS = 'MISS'
    CACHE_HIT = 'HIT'
    
    def __init__(self, data_dir: str, *, logger: logging.Logger) -> None:
        self._logger = logger.getChild('certs_store')
        self._db = None
        
        self._init_db(os.path.join(data_dir, 'certs.db'))
        
    def replace(self, name: str, *, provider: str, domains: dict, expiry_date: str) -> None:
        # sort members list to ensure consistent hash
        checksum = hashlib.sha256(''.join(sorted(domains)).encode()).hexdigest()
        
        sql = 'REPLACE INTO certs (name, provider, domains, expiry_date, checksum) VALUES (?, ?, ?, ?, ?)'
        
        # insert or replace cert data
        cursor = self._db.cursor()
        cursor.execute(sql, (name, provider, json.dumps(domains), expiry_date, checksum))
        self._db.commit()
        
        self._logger.debug(f'Replaced cert record for "{name}"')
        
    def remove(self, name: str) -> None:
        cursor = self._db.cursor()
        
        cursor.execute('DELETE FROM certs WHERE name = ? LIMIT 1', (name,))
        self._db.commit()
        
        self._logger.debug(f'Removed cert record for "{name}"')
        
    def update(self, name: str, expiry_date: str) -> None:
        cursor = self._db.cursor()
        
        cursor.execute('UPDATE certs SET expiry_date = ? WHERE name = ?', (expiry_date, name))
        self._db.commit()
        
        self._logger.debug(f'Updated expiry date for "{name}"')

    def check(self, name: str, members: list[str]) -> str:
        cert = self.get(name)
        
        if not cert:
            return self.CACHE_MISS

        # sort members list to ensure consistent hash
        checksum = hashlib.sha256(''.join(sorted(members)).encode()).hexdigest()

        # check if cache content matches members hash
        if cert['checksum'] == checksum:
            return self.CACHE_HIT
        
        return self.CACHE_MISS
    
    def get(self, name: str) -> str:
        cursor = self._db.cursor()
        
        cursor.execute('SELECT * FROM certs WHERE name = ?', (name,))
        
        res = cursor.fetchone()
        
        if not res:
            return None
        
        res = dict(res)
        res['domains'] = json.loads(res['domains'])
        
        return res
    
    def get_all(self) -> list:
        cursor = self._db.cursor()
        
        cursor.execute('SELECT * FROM certs')
        
        res_obj = cursor.fetchall()
        
        res_dict = [dict(row) for row in res_obj]
        
        # convert domains to list
        for res in res_dict:
            res['domains'] = json.loads(res['domains'])
            
        return res_dict
    
    def get_due_certs(self, days: int) -> list:
        cursor = self._db.cursor()
        
        cursor.execute('SELECT * FROM certs WHERE expiry_date < datetime("now", ?)', (f'+{days} days',))
        
        res_obj = cursor.fetchall()
        
        res_dict = [dict(row) for row in res_obj]
        
        # convert domains to list
        for res in res_dict:
            res['domains'] = json.loads(res['domains'])
            
        return res_dict
    
    def _init_db(self, db_path: str) -> None:
        self._db = sqlite3.connect(db_path)
        
        self._db.row_factory = sqlite3.Row
        
        cursor = self._db.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS certs (name TEXT PRIMARY KEY, provider TEXT, domains TEXT, expiry_date TEXT, checksum TEXT)')
        self._db.commit()