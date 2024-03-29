#!/usr/bin/env python3
import os
import sys
import logging
from pathlib import Path
from optparse import OptionParser
from shutil import copyfile, copytree
from subprocess import check_call, DEVNULL
from os import listdir, rmdir, remove, path, chmod

HELP_DESCRIPTION='This script removes files from s3 bucket.'
HELP_EXAMPLE='''
Example: ./dist_validators.py -i ~/secrets -I ~/validators -o /node/secrets -O /node/validators -s 0 -e 10
'''

# Setup logging.
log_format = '[%(levelname)s] %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
LOG = logging.getLogger(__name__)

# Shorthand for identifying OS type.
is_posix = os.name == 'posix'

def parse_opts():
    parser = OptionParser(description=HELP_DESCRIPTION, epilog=HELP_EXAMPLE)
    parser.add_option('-i', '--input-sec',
                      help='Path that contains all secrets.')
    parser.add_option('-I', '--input-val',
                      help='Path that contains all validators.')
    parser.add_option('-o', '--output-sec',
                      help='Destination path for secrets.')
    parser.add_option('-O', '--output-val',
                      help='Destination path for validators.')
    parser.add_option('-s', '--start', default=0, type=int,
                      help='Starting index of validators/secrets to copy.')
    parser.add_option('-e', '--end', default=0, type=int,
                      help='Ending index of validators/secrets to copy.')
    parser.add_option('-u', '--user', default='nimbus',
                      help='User that should own the created files.')
    parser.add_option('-p', '--print-count', action='store_true',
                      help='Print number of deployed validators to stdout.')
    parser.add_option('-f', '--force', action='store_true',
                      help='Update layout even if no changes are detected.')
    parser.add_option('-P', '--purge', action='store_true', default=False,
                      help='Purge all validators if non are selected.')
    parser.add_option('-d', '--dry-run', action='store_true', default=False,
                      help='Only print files that will be deleted.')
    parser.add_option('-l', '--log-level', default='info',
                      help='Change default logging level.')

    for option in parser.option_list:
        if option.default != ("NO", "DEFAULT"):
            option.help += (" " if option.help else "") + "(default: %default)"

    (opts, args) = parser.parse_args()

    if not opts.input_sec or not opts.input_val:
        parser.error('the --input-sec and --input-val parameters are required')
    if not opts.output_sec or not opts.output_val:
        parser.error('the --output-sec and --output-val parameters are required')

    return (opts, args)

# https://github.com/status-im/nimbus-eth2/blob/v1.4.1/scripts/makedir.sh
def fix_dir_perms(path, user):
    if is_posix: # Linux
        if path.is_file():
            chmod(path, 0o600)
        elif path.is_dir():
            chmod(path, 0o700)
        else:
            raise Exception('Unknown file type!')
    else: # Windows
        if path.is_file():
            perms = '(F)'
        elif  path.is_dir():
            perms = '(OI)(CI)(F)'
        else:
            raise Exception('Unknown file type!')
        check_call([
            'icacls', path,
            '/inheritance:r', # Remove all inherited access from path ACL
            '/grant:r', '%s:%s' % (user, perms),
        ], stdout=DEVNULL)

def main():
    (opts, args) = parse_opts()

    LOG.setLevel(opts.log_level.upper())

    in_dir_val = Path(opts.input_val)
    in_dir_sec = Path(opts.input_sec)

    LOG.debug('Finding new validators/secrets...')
    found_val = sorted(listdir(in_dir_val))
    found_sec = sorted(listdir(in_dir_sec))

    LOG.debug('Found %s new validators.', len(found_val))
    LOG.debug('Found %s new secrets.', len(found_sec))

    LOG.debug('Validating validators and secrets match...')
    # Same validators and secrets available
    if len(set(found_val) - set(found_sec)) != 0:
        raise Exception('New validators and secrets do not match.')

    # Create output directoties if missing
    out_dir_val = Path(opts.output_val)
    out_dir_sec = Path(opts.output_sec)
    if not out_dir_val.is_dir():
        LOG.debug('Creating output validators directory')
        out_dir_val.mkdir(parents=True)
    fix_dir_perms(out_dir_val, opts.user)
    if not out_dir_sec.is_dir():
        LOG.debug('Creating output secrets directory')
        out_dir_sec.mkdir(parents=True)
    fix_dir_perms(out_dir_sec, opts.user)

    LOG.debug('Finding old validators/secrets...')
    old_val = sorted(listdir(out_dir_val))
    old_sec = sorted(listdir(out_dir_sec))

    LOG.debug('Filtering out slashing database...')
    not_slashing_db = lambda p: not p.startswith('slashing')
    old_val = list(filter(not_slashing_db, old_val))

    LOG.debug('Found %s old validators.', len(old_val))
    LOG.debug('Found %s old secrets.', len(old_sec))

    LOG.debug('Extracting validator range...') 
    new_val = found_val[opts.start:opts.end]
    new_sec = found_sec[opts.start:opts.end]

    LOG.debug('Selected %s new validators.', len(new_val))
    LOG.debug('Selected %s new secrets.', len(new_sec))

    if len(new_val) == 0 or len(new_sec) == 0:
        LOG.warning('No new validators or secrets selected!')
        if not opts.purge:
            sys.exit(1)

    LOG.debug('Verifying if a difference exists...') 
    val_diff = set(new_val).symmetric_difference(set(old_val))
    sec_diff = set(new_sec).symmetric_difference(set(old_sec))

    if opts.force:
        LOG.info('Forcing validator layout update.')
    elif len(val_diff) > 0 or len(sec_diff) > 0:
        LOG.info('Difference in validator layout found.')
    else:
        LOG.info('No difference in validator layout found. Nothing to do.')
        sys.exit(0)

    if opts.dry_run:
        LOG.info('This is a DRY run! No files will be copied or removed.')
        sys.exit(0)

    if len(old_val) > 0:
        LOG.info('Removing %s old validators...', len(old_val))
        for val in old_val:
            remove(out_dir_val / val / 'keystore.json')
            rmdir(out_dir_val / val)
    if len(old_sec) > 0:
        LOG.info('Removing %s old secrets...', len(old_sec))
        for sec in old_sec:
            remove(out_dir_sec / sec)

    LOG.info('Copying %s new validators...', len(new_val))
    for val in new_val:
        src = in_dir_val / val
        dst = out_dir_val / val
        LOG.debug('Copying: %s -> %s', src, dst)
        copytree(src, dst)
        fix_dir_perms(dst, opts.user)
        fix_dir_perms(dst / 'keystore.json', opts.user)
    LOG.info('Copying %s new secrets...', len(new_sec))
    for sec in new_sec:
        src = in_dir_sec / sec
        dst = out_dir_sec / sec
        LOG.debug('Copying: %s -> %s', src, dst)
        copyfile(src, dst)
        fix_dir_perms(dst, opts.user)

    LOG.info('SUCCESS')
    # Useful for Ansible to know if anything changed
    if opts.print_count:
        print(len(new_val))

if __name__ == '__main__':
    main()
