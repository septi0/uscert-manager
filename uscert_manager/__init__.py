import sys
import argparse
from uscert_manager.manager import UsCertManager, UsCertManagerError, UsCertManagerConfigError
from uscert_manager.info import __app_name__, __version__, __description__, __author__, __author_email__, __author_url__, __license__

def main():
    # get args from command line
    parser = argparse.ArgumentParser(description=__description__)

    parser.add_argument('--config-dir', dest='config_dir', help='Config file(s) directory', default='/config')
    parser.add_argument('--certs-dir', dest='certs_dir', help='Certs directory', default='/certs')
    parser.add_argument('--data-dir', dest='data_dir', help='Data directory', default='/data')
    parser.add_argument('--hooks-dir', dest='hooks_dir', help='Hooks directory', default='/hooks')
    parser.add_argument('--log', dest='log_file', help='Log file where to write logs')
    parser.add_argument('--log-level', dest='log_level', help='Log level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO')
    parser.add_argument('--bin-path', dest='bin_path', help='Path to binaries')
    parser.add_argument('--version', action='version', version=f'{__app_name__} {__version__}')

    args = parser.parse_args()

    try:
        uscert_manager = UsCertManager({
            'config_dir': args.config_dir,
            'certs_dir': args.certs_dir,
            'data_dir': args.data_dir,
            'hooks_dir': args.hooks_dir,
            'log_file': args.log_file,
            'log_level': args.log_level,
            'bin_path': args.bin_path,
        })
    except UsCertManagerConfigError as e:
        print(f"Config error: {e}\nCheck documentation for more information on how to configure {__app_name__} identities")
        sys.exit(2)

    uscert_manager.run()

    sys.exit(0)