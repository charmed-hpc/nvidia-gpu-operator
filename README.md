# nvidia-gpu-operator

This operator charm installs and removes the Nvidia drivers on a machine when
the `juju-info` integration is created with a principle charm.

The Nvidia drivers are installed via the installation procedure defined in the [Nvidia documentation](https://docs.nvidia.com/datacenter/tesla/tesla-installation-notes/index.html#centos7).


# Example Usage
```bash
juju deploy slurmd --series centos7
juju deploy nvidia-gpu --channel edge

juju integrate slurmd nvidia-gpu
```

### Copyright
* Omnivector, LLC &copy; <admin@omnivector.solutions>

### License
* Apache v2 - see [LICENSE](./LICENSE)
