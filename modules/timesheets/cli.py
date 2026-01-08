"""Timesheet CLI."""
import argparse
from datetime import date


def main():
    parser = argparse.ArgumentParser(description='Timesheet Tracking')
    parser.add_argument('command', choices=['log', 'report', 'summary'])
    parser.add_argument('--project', help='Project ID')
    parser.add_argument('--hours', type=float, help='Hours worked')
    parser.add_argument('--date', help='Date (YYYY-MM-DD)')
    parser.add_argument('--description', '-d', help='Work description')
    args = parser.parse_args()
    
    print(f'⏱️  Timesheets: {args.command}')
    print('   TODO: Implement')


if __name__ == '__main__':
    main()
