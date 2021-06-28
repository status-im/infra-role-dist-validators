# Description

This role copies secrets and validators required for testnets to which [Nimbus beacon nodes](https://nimbus.team/) contribute.

# Configuration

You need to provide the start and end indices of validators to be fetched from the repo:
```yaml
dist_validators_start: 1500
dist_validators_end: 3000
dist_validators_data_path: '/docker/node/data/network'
```
The data path is assumed to be the correct location of `validators` and `secrets` folders.

# Warning

__This role does not take into account the currently existing layout of validators and secrets!__

Take into account what is already in place and which nodes are running and in what order you run this role to avoid a case in which validators on two or more nodes overlap.

# Details

You can read about validators and secrets here:

* https://status-im.github.io/nimbus-eth2/faq.html#what-exactly-is-a-validator
* https://status-im.github.io/nimbus-eth2/keys.html#storage
