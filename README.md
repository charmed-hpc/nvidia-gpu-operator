# nvidia-gpu-operator

This operator charm installs and removes the nvidia drivers on a machine when
the `juju-info` integration is created with a principle charm.


# Example Usage
```bash
juju deploy slurmd --series centos7
juju deploy nvidia-gpu

juju integrate slurmd nvidia-gpu
```

### Copyright
* Omnivector, LLC <admin@omnivector.solutions>

### License
* Apache v2 - see [LICENSE](./LICENSE)
