"""Tax CLI."""
import argparse


def main():
    parser = argparse.ArgumentParser(description='Tax Management')
    parser.add_argument('command', choices=['uva', 'euer', 'collect', 'validate'])
    parser.add_argument('--year', type=int, required=True, help='Tax year')
    parser.add_argument('--quarter', type=int, help='Quarter (for UVA)')
    args = parser.parse_args()
    
    print(f'🧮 Tax: {args.command} for {args.year}')
    print('   TODO: Implement')


if __name__ == '__main__':
    main()
