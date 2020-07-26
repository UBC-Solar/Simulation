import json
import argparse
import sys

def parse_args():
    parser = argparse.ArgumentParser(description='configuration arguments')

    parser.add_argument('-d', '--debug', help='set debug flags', action='store_true')
    parser.add_argument('--seed', help='set seed', type=int, default=0)
    parser.add_argument('--load-config-file', help='which file to load config', type=str)
    parser.add_argument('--save-config-file', help='which file to save config', type=str)

    args = parser.parse_args()
    save_config_file = args.save_config_file
    load_config_file = args.load_config_file
    delattr(args, 'save_config_file')
    delattr(args, 'load_config_file')
    if (save_config_file):
        with open(save_config_file, 'w') as fp:
            json.dump(args.__dict__, fp, indent=2)

    if (load_config_file):
        with open(load_config_file, 'r') as fp:
            args.__dict__ = json.load(fp)
    return args


# example usage: please delete
def main():
    args = parse_args()
    print(args)
    print(args.seed)
    
if __name__ == '__main__':
    main()
