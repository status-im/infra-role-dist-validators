# Description

This role copies secrets and validators required for testnets to which [Nimbus beacon nodes](https://nimbus.team/) contribute.

# Configuration

You need to provide the start and end indices of validators to be fetched from the repo:
```yaml
# Name of folder with validators and secrets in the repo.
dist_validators_name: 'prater_deposits'
# Start and end index of validators for the host.
dist_validators_start: 1500
dist_validators_end: 3000
# Destination where validators and secrets should be copied.
dist_validators_sec_path: '/docker/node-01/data/secrets'
dist_validators_val_path: '/docker/node-01/data/validators'
# Necessary on Windows to impersonate nimbus user.
dist_validators_user_pass: 'super-secret-password'
```
The data path is assumed to be the correct location of `validators` and `secrets` folders.

# Warning

__This role does not take into account the currently existing layout of validators and secrets!__

Take into account what is already in place and which nodes are running and in what order you run this role to avoid a case in which validators on two or more nodes overlap.

# Details

You can read about validators and secrets here:

* https://status-im.github.io/nimbus-eth2/faq.html#what-exactly-is-a-validator
* https://status-im.github.io/nimbus-eth2/keys.html#storage

# Script

The Python script responsible for slecting and copying over validators was implemented to make the process faster and easier to debug. The usage is quite simple:
```
 $ ./dist_validators.py --help
Usage: dist_validators.py [options]

This script removes files from s3 bucket.

Options:
  -h, --help            show this help message and exit
  -i INPUT_SEC, --input-sec=INPUT_SEC
                        Path that contains all secrets.
  -I INPUT_VAL, --input-val=INPUT_VAL
                        Path that contains all validators.
  -o OUTPUT_SEC, --output-sec=OUTPUT_SEC
                        Destination path for secrets.
  -O OUTPUT_VAL, --output-val=OUTPUT_VAL
                        Destination path for validators.
  -s START, --start=START
                        Starting index of validators/secrets to copy.
                        (default: 0)
  -e END, --end=END     Ending index of validators/secrets to copy. (default:
                        0)
  -u USER, --user=USER  User that should own the created files. (default:
                        nimbus)
  -p, --print-count     Print number of deployed validators to stdout.
  -d, --dry-run         Only print files that will be deleted. (default:
                        False)
  -l LOG_LEVEL, --log-level=LOG_LEVEL
                        Change default logging level. (default: info)

 Example: ./dist_validators.py -i ~/secrets -I ~/validators -o /node/secrets -O /node/validators -s 0 -e 10
```
```
 > ./dist_validators.py  --input=dist-validators/prater_deposits --output=beacon-node-prater-stable/data/shared_prater_0 --start=7500 --end=10000          
[INFO] No difference in validator layout found. Nothing to do.
```
