"""Controlling CLI."""
import argparse


def main():
    parser = argparse.ArgumentParser(description='Financial Controlling')
    parser.add_argument('command', choices=['summary', 'forecast', 'export'])
    parser.add_argument('--year', type=int, help='Year')
    parser.add_argument('--month', type=int, help='Month')
    args = parser.parse_args()
    
    print(f'📊 Controlling: {args.command}')
    print('   TODO: Implement')


if __name__ == '__main__':
    main()
