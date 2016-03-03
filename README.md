# jupyter_kernelspec_creator

Designed for use with [jupyterhub](https://github.com/jupyter/jupyterhub) and [slurmspawner](https://github.com/mkgilbert/slurmspawner).

## Overview

Sime file manipulation and creation in a user's home directories to create the appropriate kernel folders and kernel.json files for any conda envs they may have created.

## Usage

If using with slurmspawner, just include a call to this file in the "extra_launch_script". Other usage is untested, but should theoretically work similarly. Just call this when single-user servers spawn
