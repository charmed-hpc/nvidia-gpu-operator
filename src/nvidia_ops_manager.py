#!/usr/bin/env python3
"""Nvidia driver install, remove and return version."""
import tempfile
from pathlib import Path
from subprocess import CalledProcessError, check_output, run

import requests


def os_release():
    """Return /etc/os-release as a dict."""
    os_release_data = Path("/etc/os-release").read_text()
    os_release_list = [
        item.split("=") for item in os_release_data.strip().split("\n") if item != ""
    ]
    return {k: v.strip('"') for k, v in os_release_list}


class NvidiaDriverOpsError(Exception):
    """Error raised for nvidia driver installation errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class NvidiaOpsManagerBase:
    """NvidiaOpsManagerBase."""

    def __init__(self):
        pass

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

    def install(self) -> None:
        """Install nvidia-drivers here."""
        raise Exception("Inheriting object needs to define this method.")

    def remove(self) -> None:
        """Remove nvidia-drivers here."""
        raise Exception("Inheriting object needs to define this method.")

    def version(self) -> None:
        """Return the cuda-drivers version."""
        raise Exception("Inheriting object needs to define this method.")


class NvidiaOpsManagerUbuntu(NvidiaOpsManagerBase):
    """NvidiaOpsManager for Ubuntu."""

    OS_RELEASE = os_release()

    def __init__(self, driver_package: str):
        self._driver_package = driver_package
        self._id = self.OS_RELEASE["ID"]
        self._version_id = self.OS_RELEASE["VERSION_ID"].replace(".", "")
        self._distribution = f"{self._id}{self._version_id}"

    def _install_kernel_headers(self) -> None:
        """Install the kernel headers."""
        try:
            run(["apt-get", "install", "-y", f"linux-headers-{self._uname_r}"])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error installing kernel headers.")

    def _install_cuda_keyring(self) -> None:
        """Install the cuda keyring .deb."""
        # Grab the cuda-keyring.deb from the url.
        try:
            r = requests.get(
                "https://developer.download.nvidia.com/compute/cuda/"
                f"repos/{self._distribution}/{self._arch}/cuda-keyring_1.0-1_all.deb"
            )
        except requests.exceptions.HTTPError:
            raise NvidiaDriverOpsError(
                f"Error downloading cuda keyring from {self._cuda_keyring_url}"
            )
        # Write the cuda-keyring.deb to a tmp file and install it with dpkg.
        with tempfile.TemporaryDirectory() as tmpdir:
            cuda_keyring_deb = f"{tmpdir}/cuda-keyring.deb"
            Path(cuda_keyring_deb).write_bytes(r.content)
            try:
                run(["dpkg", "-i", cuda_keyring_deb])
            except CalledProcessError:
                raise NvidiaDriverOpsError("Error installing cuda keyring .deb.")
        # Run apt-get update
        try:
            run(["apt-get", "update"])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error running `apt-get update`.")

    def _install_cuda_drivers(self) -> None:
        """Install the cuda drivers."""
        try:
            run(["apt-get", "install", "-y", self._driver_package])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error installing cuda drivers.")

    def install(self) -> None:
        """Install Nvidia drivers on Ubuntu."""
        self._install_kernel_headers()
        self._install_cuda_keyring()
        self._install_cuda_drivers()

    def remove(self) -> None:
        """Remove cuda drivers from the os."""
        try:
            run(["apt-get", "-y", "remove", "--purge", self._driver_package])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error removing cuda-drivers.")

        Path(f"/etc/apt/sources.list.d/cuda-{self._distribution}-{self._arch}.list").unlink()

        try:
            run(["apt-get", "update"])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error running `apt-get update`.")

    def version(self) -> str:
        """Return the cuda-drivers package version."""
        try:
            p = check_output(["apt-cache", "policy", self._driver_package])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error running `apt-cache policy cuda-drivers.")

        version = ""
        for line in p.decode().strip().split("\n"):
            if "Installed" in line:
                version = line.split("Installed: ")[1]
        if not version:
            raise NvidiaDriverOpsError("Error locating cuda-drivers package version.")
        return version


class NvidiaOpsManagerCentos(NvidiaOpsManagerBase):
    """NvidiaOpsManager for Centos7."""

    def __init__(self, driver_package: str):
        """Initialize class level variables."""
        self._driver_package = driver_package
        self._nvidia_driver_repo_filepath = Path("/etc/yum.repos.d/cuda-rhel7.repo")

    def install(self) -> None:
        """Install nvidia drivers.

        Install the Nvidia drivers as defined in the Nvidia documentation:
            https://docs.nvidia.com/datacenter/tesla/tesla-installation-notes/index.html#centos7
        """
        # Install Nvidia driver dependencies.
        deps = [
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
        try:
            run(["yum", "install", "-y"] + deps)
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error installing driver dependencies.")

        # Grab the repo file and write it to the /etc/yum.repos.d/.
        nvidia_developer_repo = (
            "http://developer.download.nvidia.com/compute/cuda/repos/rhel7/"
            f"{self._arch}/cuda-rhel7.repo"
        )
        try:
            req = requests.get(nvidia_developer_repo)
        except requests.exceptions.HTTPError:
            raise NvidiaDriverOpsError(
                f"Error getting nvidia_developer_repository from {nvidia_developer_repo}."
            )
        self._nvidia_driver_repo_filepath.write_text(req.text)

        # Add the devel kernel and kernel headers.
        try:
            run(
                [
                    "yum",
                    "install",
                    "-y",
                    f"kernel-devel-{self._uname_r}",
                    f"kernel-headers-{self._uname_r}",
                ]
            )
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error installing devel kernel headers.")

        # Expire the cache and update repos.
        try:
            run(["yum", "clean", "expire-cache"])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error flushing the cache.")

        # Install nvidia-driver package..
        try:
            run(["yum", "install", "-y", self._driver_package])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error installing nvidia drivers.")

    def remove(self) -> None:
        """Remove nvidia drivers from the system."""
        # Remove nvidia-driver package..
        try:
            run(["yum", "erase", "-y", self._driver_package])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error removing nvidia drivers from the system.")
        # Remove the drivers repo
        if self._nvidia_driver_repo_filepath.exists():
            self._nvidia_driver_repo_filepath.unlink()
        # Expire the cache and update repos.
        try:
            run(["yum", "clean", "expire-cache"])
        except CalledProcessError:
            raise NvidiaDriverOpsError("Error flushing the cache.")

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
                    self._driver_package,
                ]
            )
        except CalledProcessError:
            raise NvidiaDriverOpsError("Cannot return version for package that isn't installed.")
        return version.decode().strip("'")
