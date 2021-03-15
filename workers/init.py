import json
import yaml
from argparse import ArgumentParser
import os



def main(config_loc=''):
    if config_loc == '':
        parser = ArgumentParser(description='RUN NEMO worker')
        parser.add_argument('config_location', help='location of YAML config file')
        args = parser.parse_args()
        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc)

    params = { 'DOWNLOAD_WEATHER': True,
               'PROCESS_FORCING': False,
               'RUN_NEMO': False,
               'WATCH_NEMO': False,
               'STOP_CONTAINER': False

    }

    with open(config['status_dir'] + 'worker_status.json', 'w') as fp:
        json.dump(params, fp)



'''Read in config file with all parameters required'''
def read_yaml(YAML_loc):
    # safe load YAML file, if file is not present raise exception
    if not os.path.isfile(YAML_loc):
        print('DONT PANIC: The yaml file specified does not exist')
        return 1
    with open(YAML_loc) as f:
        config_file = yaml.safe_load(f)
    config = config_file['INIT']
    return config

if __name__ == '__main__':
    main()  # pragma: no cover
