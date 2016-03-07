#!/usr/bin/env python
# By: Michael Gilbert
# Overview:
#   This script is for use in conjunction with Jupyter as a helper to check the user's directories for
#   custom made envs that will need to have kernels created for them in Jupyter. It creates the kernel.json
#   files and appropriate directories so they will show up in Jupyterhub.

import os
import json
import subprocess as sp
import shutil
from subprocess import Popen
from string import Template


def run_cmd(cmd, args=None, tries=0):
    """
    Runs a Bash command and gets the output
    :param cmd: Bash command-line program
    :param args: Arguments to pass into the "cmd"
    :param tries: number of times the command has been tried (max is 5)
    :return: returns output of calling the cmd
    """
    # setup command to be run
    p = Popen(cmd, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    # check current number of tries
    if tries >= 5:
        print("Max tries exceeded.")
        return -1
    # tries was less than 5, so run the command either with args or without
    print("Running command '%s'" % cmd)
    if args is not None:
        out = p.communicate(args.encode())
    else:
        out = p.communicate()

    # out[1] is a string of the error output, if any. If errors, run again (until max tries exceeded)
    if 'Error' in out[1].decode() or 'error' in out[1].decode():
        print("Try %d: Command returned error: '%s'" % (tries+1, out[1].decode()))
        return run_cmd(cmd, args, tries+1)  # error was returned by shell
    else:
        # everything ran just fine
        out = out[0].decode().strip()
        return out


class JupyterUser:
    """
    User who will be logging into Jupyterhub
    """
    def __init__(self, userid, home):
        """
        :param userid: user's linux name
        :param home: user's home directory
        """
        self.userid = userid
        self.home = home
        self.conda_env_dir = os.path.join(home, ".conda", "envs")
        self.kernel_dir = os.path.join(home, ".local", "share", "jupyter", "kernels")
        self.conda_envs = []    # contains tuples of (env_name, env_python_binary)

    def populate_conda_envs(self):
        """
        Checks user's conda_env_dir for envs and installs ipykernel in each env that doesn't have it installed.
        Then populates conda_envs with tuples of env info
        :return: None if no envs found, True otherwise
        """
        print("Trying to populate conda env list")
        try:
            conda_dir = os.listdir(self.conda_env_dir)
            envs = [directory for directory in conda_dir if os.path.isdir(os.path.join(self.conda_env_dir, directory))]
        except FileNotFoundError:
            print("No conda env directory exists for this user")
            return None

        if len(envs) == 0:
            print("Envs list was empty...returning")
            return None

        for env in envs:
            if env.startswith("."):
                continue  # ignore hidden directories
            print("Found env '%s'" % env)
            bin_dir = os.path.join(self.conda_env_dir, env, 'bin') # where env's binaries are
            bin_list = os.listdir(bin_dir)  # total list of all binaries in env

            if "jupyter-kernelspec" in bin_list:
                print("jupyter-kernelspec found. Skipping ipykernel install.")
                self.conda_envs.append((env, os.path.join(bin_dir, 'python')))
            else:  # they didn't have jupyter-kernelspec, so need to install ipykernel
                # create a tuple of the env name and the binary executable
                # now we need to install "ipykernel" into this env
                print("jupyter-kernelspec not found. Installing ipykernel...")
                result = self.conda_install('ipykernel', env)
                if result == -1:
                    # conda install failed for some reason, so don't add this one to the list
                    print("Conda install of 'ipykernel' in '%s' failed! Skipping..." % env)
                else:
                    # Conda install succeeded, populate conda_envs with tuple of; (env-name, binary/path/of/python)
                    self.conda_envs.append((env, os.path.join(bin_dir, 'python')))

        return True

    def conda_install(self, module, env_name):
        """
        Uses 'conda install...' command to install a python package into a particular env
        :param module: string, name of python module to install
        :param env_name: string, name of env to install package to
        :return: nothing
        """
        print("Attempting to install module '%s' in env '%s'..." % (module, env_name))
        bash_script = Template('''#!/bin/bash\nsource activate $env\nconda install --yes $module\nexit\n''')
        out = run_cmd('/bin/sh', bash_script.substitute(dict(env=env_name, module=module)))
        return out

    def create_kernelspec(self, name, dir):
        """
        Creates the kernelspecs for a python env and outputs the json needed to create the kernel.json file
        :param name: string, name of the juptyerhub kernel
        :param dir: string, path to env python binary
        :return: json-formatted string
        """
        language = "python"
        argv = [dir, "-m", "ipykernel", "-f", "{connection_file}"]

        kernelspec = {"display_name": name + "-conda-env",
                      "language": language,
                      "argv": argv}
        return json.dumps(kernelspec)

    def install_kernelspecs(self):
        """
        Goes through the user's kernels directory, deletes any existing kernels prepended with AUTO_
        and re-installs current kernels
        :return: nothing
        """

        print("Removing existing auto generated kernels...")
        for dir in os.listdir(self.kernel_dir):
            if dir.startswith('AUTO_'):
                print("Removing '%s'" % dir)
                shutil.rmtree(os.path.join(os.path.join(self.kernel_dir, dir)))  # remove directory

        if len(self.conda_envs) == 0:
            print("User does not have any conda envs or user env list has not yet been populated.\nRun populate_conda_envs()")
        else:
            print("Creating kernel.json files...")
            for env_tuple in self.conda_envs:
                # extract info from the tuple
                new_dir = os.path.join(self.kernel_dir, "AUTO_" + env_tuple[0])
                # create directory, create kernelspec and install file in directory
                os.mkdir(new_dir)
                kernel_json_file = os.path.join(new_dir, 'kernel.json')
                spec = self.create_kernelspec(env_tuple[0], env_tuple[1])
                f = open(kernel_json_file, 'w')
                f.write(spec)  # write the json to file
                f.close()
            print("Done")


    def __str__(self):
        s = ""
        s += "userid    : " + str(self.userid) + "\n"
        s += "home      : " + str(self.home) + "\n"
        s += "conda_envs: " + str(self.conda_env_dir) + "\n"
        s += "kernel_dir: " + str(self.kernel_dir) + "\n"
        return s


if __name__ == '__main__':
    user = os.getenv('USER')
    home = os.getenv('HOME')
    u = JupyterUser(user, home)

    print(u)

    did_populate = u.populate_conda_envs()
    if did_populate:
        u.install_kernelspecs()
    print("Exiting jupyter_kernelspec_creator")



