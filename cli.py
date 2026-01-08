#!/usr/bin/env python3
"""Unified CLI for Freelancer Admin.

Usage:
    python cli.py applications --help
    python cli.py invoicing --help
    python cli.py timesheets --help
    python cli.py controlling --help
    python cli.py tax --help
"""
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='🪓 Freelancer Admin - Viking Edition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modules:
  applications  Job applications & CV management
  invoicing     Invoice generation
  timesheets    Time tracking
  controlling   Financial analysis
  tax           Tax preparation

Examples:
  python cli.py applications list
  python cli.py applications send ibsc --mode draft
  python cli.py invoicing new --client "nemensis AG" --hours 40
  python cli.py timesheets log --project nemensis --hours 8 -d "Architecture review"
  python cli.py controlling summary --year 2025
  python cli.py tax uva --year 2025 --quarter 4
"""
    )
    
    parser.add_argument(
        'module',
        choices=['applications', 'invoicing', 'timesheets', 'controlling', 'tax'],
        help='Module to run'
    )
    
    # Parse just the module, pass rest to submodule
    args, remaining = parser.parse_known_args()
    
    # Dispatch to module CLI
    if args.module == 'applications':
        from modules.applications.bewerbung import main as app_main
        sys.argv = ['bewerbung'] + remaining
        app_main()
    
    elif args.module == 'invoicing':
        from modules.invoicing.cli import main as inv_main
        sys.argv = ['invoicing'] + remaining
        inv_main()
    
    elif args.module == 'timesheets':
        from modules.timesheets.cli import main as ts_main
        sys.argv = ['timesheets'] + remaining
        ts_main()
    
    elif args.module == 'controlling':
        from modules.controlling.cli import main as ctrl_main
        sys.argv = ['controlling'] + remaining
        ctrl_main()
    
    elif args.module == 'tax':
        from modules.tax.cli import main as tax_main
        sys.argv = ['tax'] + remaining
        tax_main()


if __name__ == '__main__':
    main()
