"""Invoice CLI."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Invoice Management')
    parser.add_argument('command', choices=['new', 'list', 'send'])
    parser.add_argument('--client', help='Client name')
    parser.add_argument('--hours', type=float, help='Hours worked')
    args = parser.parse_args()
    
    print(f'🧾 Invoicing: {args.command}')
    print('   TODO: Implement - migrate from corporate/neue-rechnung.py')


if __name__ == '__main__':
    main()
