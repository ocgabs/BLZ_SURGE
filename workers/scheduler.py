import schedule
import os
from time import sleep
from argparse import ArgumentParser
import yaml

def main(config_loc=''):
    if config_loc == '':
        parser = ArgumentParser(description='Scheduler')
        parser.add_argument('config_location', help='location of YAML config file')
        args = parser.parse_args()
        config = read_yaml(args.config_location)
    else:
        config = read_yaml(config_loc)

    schedule.every().day.at(config['start_time_weather']).do(run_weather)
    schedule.every().day.at(config['start_time_sar']).do(run_sar)

    while True:
        #print('running any pending jobs...')
        schedule.run_pending()
        #print('going to sleep for 60 seconds')
        sleep(60)
	
def run_weather():
    print('starting weather worker.....')	
    os.system('pm2 start download_weather')
def run_sar():
    print('starting get sar worker......')
    os.system('pm2 start get_sargassium')

'''Read in config file with all parameters required'''
def read_yaml(YAML_loc):
    # safe load YAML file, if file is not present raise exception
    if not os.path.isfile(YAML_loc):
        print('DONT PANIC: The yaml file specified does not exist')
        return 1
    with open(YAML_loc) as f:
        config_file = yaml.safe_load(f)
    config = config_file['SCHEDULER']
    return config

if __name__ == '__main__':
    main()  # pragma: no cover
