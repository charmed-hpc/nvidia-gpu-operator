#!/usr/bin/env python3
"""Nvidia driver install, remove and return version."""
import requests

from pathlib import Path
from subprocess import CalledProcessError, check_output, run
from typing import List


class NvidiaDriverOpsError(Exception):
    """Error raised for nvidia driver installation errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class NvidiaOpsManager:
    """NvidiaOpsManager."""

    def __init__(self, driver_package):
        """Initialize class level variables."""
        self.PACKAGE_DEPS = [
            "tar",
            "bzip2",
            "make",
            "automake",
            "gcc",
            "gcc-c++",
            "pciutils",
            "elfutils-libelf-devel",
            "libglvnd-devel",
            "iptables",
            "firewalld",
            "vim",
            "bind-utils",
            "wget",
        ]
        self.EPEL_RELEASE_REPO = (
            "https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm"
        )
        self.NVIDIA_DRIVER_PACKAGE = driver_package
        self.NVIDIA_DRIVER_REPO_FILEPATH = Path("/etc/yum.repos.d/cuda-rhel7.repo")

    @property
    def _arch(self) -> str:
        """Return the system architecture."""
        try:
            arch = check_output(["/bin/arch"])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error detecting system architecture.")
        return arch.decode().strip()

    @property
    def _uname_r(self) -> str:
        """Return the kernel version."""
        try:
            kernel_version = check_output(["/usr/bin/uname", "-r"])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error detecting kernel version.")
        return kernel_version.decode().strip()

    @property
    def _nvidia_developer_repo(self) -> str:
        """Generate and return the Nvidia developer repo url."""
        return (
            "http://developer.download.nvidia.com/compute/cuda/repos/rhel7/"
            f"{self._arch}/cuda-rhel7.repo"
        )

    @property
    def _kernel_packages(self) -> List:
        """Return the appropriate kernel devel and header packages for the current kernel."""
        return [f"kernel-devel-{self._uname_r}", f"kernel-headers-{self._uname_r}"]

    def install(self) -> None:
        """Install nvidia drivers.

        Install the Nvidia drivers as defined in the Nvidia documentation:
            https://docs.nvidia.com/datacenter/tesla/tesla-installation-notes/index.html#centos7
        """
        # Install Nvidia driver dependencies.
        try:
            run(["yum", "install", "-y"] + self.PACKAGE_DEPS)
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error installing driver dependencies.")
        # Grab the correct repo file and write it to the /etc/yum.repos.d/.
        try:
            req = requests.get(self._nvidia_developer_repo)
        except requests.exceptions.HTTPError:
            raise NvidiaDriverOpsError(
                f"Error getting nvidia_developer_repository from {self._nvidia_developer_repo}."
            )
        self.NVIDIA_DRIVER_REPO_FILEPATH.write_text(req.text)
        # Add the devel kernel and kernel headers.
        try:
            run(["yum", "install", "-y"] + self._kernel_packages)
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error installing devel kernel headers.")
        # Expire the cache and update repos.
        try:
            run(["yum", "clean", "expire-cache"])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error flushing the cache.")
        # Install nvidia-driver package..
        try:
            run(["yum", "install", "-y", self.NVIDIA_DRIVER_PACKAGE])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error installing nvidia drivers.")

    def remove(self) -> None:
        """Remove nvidia drivers from the system."""
        # Remove nvidia-driver package..
        try:
            run(["yum", "erase", "-y", self.NVIDIA_DRIVER_PACKAGE])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error removing nvidia drivers from the system.")
        # Remove the drivers repo
        if self.NVIDIA_DRIVER_REPO_FILEPATH.exists():
            self.NVIDIA_DRIVER_REPO_FILEPATH.unlink()
        # Expire the cache and update repos.
        try:
            run(["yum", "clean", "expire-cache"])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error flushing the cache.")
        # Remove the devel kernel and kernel headers.
        try:
            run(["yum", "erase", "-y"] + self._kernel_packages)
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error removing devel kernel headers.")
        # Remove Nvidia driver dependencies.
        for i in self.PACKAGE_DEPS:
            try:
                run(["yum", "erase", "-y", i])
            except CalledProcessError:
                raise NvidiaDriverOpsError(f"Error removing {i}.")

    def version(self):
        """Return the version of nvidia-driver-latest-dkms."""
        # Use rpm -q to get the package version
        try:
            version = check_output(
                [
                    "rpm",
                    "-q",
                    "--queryformat",
                    "'%{VERSION}'",
                    self.NVIDIA_DRIVER_PACKAGE,
                ]
            )
        except CalledProcessError:
            raise NvidiaDriverOpsError("Cannot return version for package that isn't installed.")
        return version.decode().strip("'")
