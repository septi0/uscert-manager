import sys
import argparse
from uscertbot_manager.manager import UsCertbotManager, UsCertbotManagerError, UsCertbotManagerConfigError
from uscertbot_manager.info import __app_name__, __version__, __description__, __author__, __author_email__, __author_url__, __license__

def main():
    # get args from command line
    parser = argparse.ArgumentParser(description=__description__)

    parser.add_argument('--config-dir', dest='config_dir', help='Config file(s) directory')
    parser.add_argument('--data-dir', dest='data_dir', help='Data directory')
    parser.add_argument('--log', dest='log_file', help='Log file where to write logs')
    parser.add_argument('--log-level', dest='log_level', help='Log level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO')
    parser.add_argument('--pip-bin', dest='pip_bin', help='Pip binary to use', default='pip3')
    parser.add_argument('--certbot-bin', dest='certbot_bin', help='Certbot binary to use', default='certbot')
    parser.add_argument('--version', action='version', version=f'{__app_name__} {__version__}')

    args = parser.parse_args()

    try:
        uscertbot_manager = UsCertbotManager({
            'config_dir': args.config_dir,
            'data_dir': args.data_dir,
            'log_file': args.log_file,
            'log_level': args.log_level,
            'pip_bin': args.pip_bin,
            'certbot_bin': args.certbot_bin,
        })
    except UsCertbotManagerConfigError as e:
        print(f"Config error: {e}\nCheck documentation for more information on how to configure {__app_name__} identities")
        sys.exit(2)

    uscertbot_manager.run()

    sys.exit(0)