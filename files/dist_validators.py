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
HELP_EXAMPLE='Example: ./dist_validators.py -i ~/deposits -o /data/beacon-node -s 0 -e 10'

# Setup logging.
log_format = '[%(levelname)s] %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
LOG = logging.getLogger(__name__)

# Shorthand for identifying OS type.
is_posix = os.name == 'posix'

def parse_opts():
    parser = OptionParser(description=HELP_DESCRIPTION, epilog=HELP_EXAMPLE)
    parser.add_option('-i', '--input',
                      help='Path that contains secrets and validators.')
    parser.add_option('-o', '--output',
                      help='Path used by beacon node for data storage.')
    parser.add_option('-s', '--start', default=0, type=int,
                      help='Starting index of validators/secrets to copy.')
    parser.add_option('-e', '--end', default=0, type=int,
                      help='Ending index of validators/secrets to copy.')
    parser.add_option('-u', '--user', default='nimbus',
                      help='User that should own the created files.')
    parser.add_option('-p', '--print-count', action='store_true',
                      help='Print number of deployed validators to stdout.')
    parser.add_option('-d', '--dry-run', action='store_true', default=False,
                      help='Only print files that will be deleted.')
    parser.add_option('-l', '--log-level', default='info',
                      help='Change default logging level.')

    for option in parser.option_list:
        if option.default != ("NO", "DEFAULT"):
            option.help += (" " if option.help else "") + "(default: %default)"

    (opts, args) = parser.parse_args()

    if not opts.input:
        parser.error('the --input parameter is required')
    if not opts.output:
        parser.error('the --output parameter is required')

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

    in_dir = Path(opts.input)
    out_dir = Path(opts.output)

    LOG.debug('Finding new validators/secrets...')
    found_val = sorted(listdir(in_dir / 'validators'))
    found_sec = sorted(listdir(in_dir / 'secrets'))

    LOG.debug('Found %s new validators.', len(found_val))
    LOG.debug('Found %s new secrets.', len(found_sec))

    LOG.debug('Validating validators and secrets match...')
    # Same validators and secrets available
    if len(set(found_val) - set(found_sec)) != 0:
        raise Exception('New validators and secrets do not match.')

    # Create output directoties if missing
    out_val_dir = out_dir / 'validators'
    out_sec_dir = out_dir / 'secrets'
    if not out_val_dir.is_dir():
        LOG.debug('Creating output validators directory')
        out_val_dir.mkdir(parents=True)
    fix_dir_perms(out_val_dir, opts.user)
    if not out_sec_dir.is_dir():
        LOG.debug('Creating output secrets directory')
        out_sec_dir.mkdir(parents=True)
    fix_dir_perms(out_sec_dir, opts.user)

    LOG.debug('Finding old validators/secrets...')
    old_val = sorted(listdir(out_val_dir))
    old_sec = sorted(listdir(out_sec_dir))

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
        sys.exit(1)

    LOG.debug('Verifying if a difference exists...') 
    val_diff = set(new_val) - set(old_val)
    sec_diff = set(new_sec) - set(old_sec)

    if len(val_diff) > 0 or len(sec_diff) > 0:
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
            remove(out_dir / 'validators' / val / 'keystore.json')
            rmdir(out_dir / 'validators' / val)
    if len(old_sec) > 0:
        LOG.info('Removing %s old secrets...', len(old_sec))
        for sec in old_sec:
            remove(out_dir / 'secrets' / sec)

    LOG.info('Copying %s new validators...', len(new_val))
    for val in new_val:
        src = in_dir / 'validators' / val
        dst = out_val_dir / val
        LOG.debug('Copying: %s -> %s', src, dst)
        copytree(src, dst)
        fix_dir_perms(dst, opts.user)
        fix_dir_perms(dst / 'keystore.json', opts.user)
    LOG.info('Copying %s new secrets...', len(new_sec))
    for sec in new_sec:
        src = in_dir / 'secrets' / sec
        dst = out_sec_dir / sec
        LOG.debug('Copying: %s -> %s', src, dst)
        copyfile(src, dst)
        fix_dir_perms(dst, opts.user)

    LOG.info('SUCCESS')
    # Useful for Ansible to know if anything changed
    if opts.print_count:
        print(len(new_val))

if __name__ == '__main__':
    main()
