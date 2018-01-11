
import yaml
import os
import sys
import subprocess
import platform
import collections
import hashlib
import shutil
import requests

from getopt import getopt, GetoptError
from string import Template

version_string = '0.5.6'

environment = {
    'make': {
        'concurrency': 3
    },
    'definitions': ''.join([os.getcwd(), '/definitions']),
    'packages': ''.join([os.getcwd(), '/packages']),
    'root': ''.join([os.getcwd(), '/dependencies']),
    'platform': platform.system().lower()
}


def prep_str(ln, params):
    return Template(ln).safe_substitute(params)


def run_cmd(cmd, params):
    params = flatten(params, '', '_')
    subprocess.call(prep_str(cmd, params), shell=True)


def flatten(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def hash_dict(dict):
    return hashlib.sha1(str(dict).encode('utf-8')).hexdigest()


def determine_dependency(name, version):

    # Determine URL for username, repository and name.
    if '/' in name:
        try:
            username, repository, name = name.split('/', 3)
        except:
            username, name = name.split('/', 3)
            repository = name
    else:
        username = "tcmug"
        repository = "terminus"

    url = "https://raw.githubusercontent.com/" + username + "/" + repository + "/master/definitions/" + name + ".yaml"

    # Try loading the yaml file.
    try:
        response = requests.get(url)
        try:
            cfg = yaml.load(response.text)
        except yaml.YAMLError as exc:
            print(exc)
            print("Could not load cart " + url)
            exit(1)
    except:
        print("Could not load cart " + url)
        exit(1)

    # Fill in the details if package with name & version is found.
    if name in cfg:
        if version in cfg[name]:
            package = cfg[name][version].copy()
            package['url'] = url
            package['name'] = name
            package['username'] = username
            package['repository'] = repository
            return package
        else:
            print("Cart has no version '" + version + "' for '" + name + "' in " + url)
            exit(1)
    else:
        print("Cart: '" + name + "' in " + url + ")")
        exit(1)




class Package:

    def __init__(self, name, version, environment):
        if type(version) is str:
            self.config = determine_dependency(name, version)
        else:
            self.config = version.copy()

        self.config['package_path'] = self.config['username']
        self.name = self.config['name']

        if not 'parameters' in self.config:
            self.config['parameters'] = {}

        temp = self.config['parameters'].copy()
        temp.update(environment)
        temp['package_path'] = os.getcwd() + "/" + self.config['package_path']
        if 'version' not in temp:
            temp['version'] = 'N/A'
        self.environment = flatten(temp, '', '_')
        self.build = self.config['build']['default']
        if self.environment['platform'] in self.config['build']:
            self.build.update(self.config['build'][self.environment['platform']])

        # Calculate hash for build
        hashable = self.build.copy()
        hashable['parameters'] = self.config['parameters']
        self.build_hash = hash_dict(self.config)

        # Calculate hash for download
        hashable = self.build['download'].copy()
        hashable['parameters'] = self.config['parameters']
        self.download_hash = hash_dict(hashable)

    def cmd_check(self):
        if not os.path.exists(self.config['package_path']):
            os.makedirs(self.config['package_path'])
        orig_path = os.getcwd()
        os.chdir(self.config['package_path'])
        status = '\033[92mOK\033[0m'
        if self.requires_download():
            status = '\033[93mDOWNLOAD\033[0m'
        if self.requires_make():
            status = '\033[93mUPDATE\033[0m'
        print(self.name.ljust(25), str(self.environment['version']).ljust(25), status)
        os.chdir(orig_path)

    def cmd_install(self):
        if not os.path.exists(self.config['package_path']):
            os.makedirs(self.config['package_path'])
        orig_path = os.getcwd()
        os.chdir(self.config['package_path'])
        if self.requires_unmake() or self.requires_removal():
            self.run_unmake()
        if self.requires_removal():
            self.remove()
        if self.requires_download():
            self.download()
        if self.requires_make():
            self.run_make()
        os.chdir(orig_path)

    def cmd_uninstall(self):
        if not os.path.exists(self.config['package_path']):
            os.makedirs(self.config['package_path'])
        orig_path = os.getcwd()
        os.chdir(self.config['package_path'])
        self.run_unmake()
        self.remove()
        os.chdir(orig_path)

    def call(self, method):
        getattr(self, method)()

    def shell_cmd(self, cmd):
        self.log('EXEC: ', prep_str(cmd, self.environment))
        return subprocess.call(prep_str(cmd, self.environment), shell=True)

    def log(self, *args):
        print('\x1b[6;30;42m ' + " ".join(args) + ' \x1b[0m')

    def run_commands(self, node):
        if 'command' in node:
            self.shell_cmd(command)
        elif 'commands' in node:
            for command in node['commands']:
                self.shell_cmd(command)

    def requires_download(self):
        return self.get_tag('terminus_download') != self.download_hash

    def requires_removal(self):
        return self.get_tag('terminus_download') != self.download_hash

    def requires_unmake(self):
        return self.get_tag('terminus_build') != self.build_hash

    def requires_make(self):
        return self.get_tag('terminus_build') != self.build_hash

    def download(self):

        if 'git' in self.build['download']:

            git_params = ['git', 'clone', '--depth', '1', self.build['download']['git'], self.name]

            if 'checkout' in self.build['download']:
                git_params.append('-b')
                git_params.append(self.build['download']['checkout'])

            print(' '.join(git_params))
            self.shell_cmd(' '.join(git_params))

        if 'url' in self.build['download']:
            url = prep_str(self.build['download']['url'], self.environment)
            filename = url[url.rfind("/")+1:]
            self._downloadUrl(url, filename)

        self.run_commands(self.build['download'])
        self.set_tag('terminus_download', self.download_hash)


    def _downloadUrl(self, url, filename):
        url = prep_str(self.build['download']['url'], self.environment)
        self.log('DOWNLOAD: ', url, " => ", filename)
        response = requests.get(url, stream=True)
        with open(filename, "wb") as f:
            shutil.copyfileobj(response.raw, f)

    def _getUrl(self, url):
        return requests.get(url).text


    def remove(self):
        if not os.path.isdir(self.name):
            return
        self.log("REMOVE: ", self.name)
        shutil.rmtree(self.name)

    def run_make(self):

        prev = os.getcwd()
        os.chdir(self.name)

        if 'make' in self.build:
            make = self.build['make']
            if 'dir' in make:
                build_dir = make['dir']
                if not os.path.isdir(build_dir):
                    os.makedirs(build_dir)
                os.chdir(build_dir)
            self.run_commands(make)

        os.chdir(prev)

        self.set_tag('terminus_build', self.build_hash)

    def run_unmake(self):

        if not os.path.isdir(self.name):
            return

        prev = os.getcwd()
        os.chdir(self.name)

        if 'unmake' in self.build:
            unmake = self.build['unmake']
            if 'dir' in unmake:
                build_dir = unmake['dir']
                if os.path.isdir(build_dir):
                    os.chdir(build_dir)
            self.run_commands(unmake)

        os.chdir(prev)
        filename = self.name + '/terminus_build'
        if os.path.isfile(filename):
            os.remove(filename)

    def set_tag(self, tag, content):
        filename = '/'.join([self.name, tag])
        with open(filename, 'w') as f:
            f.write(content)

    def get_tag(self, tag):
        filename = '/'.join([self.name, tag])
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                s = f.read()
                return s
        return False



def cmdline_help():
    print("terminus [parameters] install|uninstall (package)")
    print("Parameters:")
    print(" -i --init       Initialize project")
    print(" -c --config=    Use given configuration file")
    print(" -v --version=   Version information")
    print(" -h --help       Get help - this!")


def cmdline_version():
    global version_string
    print(version_string)


def cmdline_initialize():
    print("---\n\ndependencies:\n\n")


def run(argv):

    # Parse options:
    try:
        opts, args = getopt(argv, "ihc:v", ["init", "help", "config=", "version"])
    except GetoptError:
        help()
        return

    config_file = 'terminus.yaml'

    for opt, arg in opts:
        if opt in ('-h', "--help"):
            cmdline_help()
            return
        elif opt in ("-c", "--config"):
            config_file = arg
        elif opt in ("-v", "--version"):
            cmdline_version()
            exit(1)
        elif opt in ("-i", "--init"):
            cmdline_initialize()
            return

    try:
        with open('terminus.yaml', 'r') as stream:
            try:
                cfg = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)
                exit(1)
    except FileNotFoundError:
        print('The file terminus.yaml was not found in this directory')
        exit(1)

    try:
        command = args[0]
    except IndexError:
        help()
        return

    try:
        package = args[1]
    except IndexError:
        package = False

    global environment
    path = environment['packages']

    if command in cfg:
        if 'commands' in cfg[command]:
            for command in cfg[command]['commands']:
                run_cmd(command, environment)
    else:

        if not os.path.isdir(path):
            os.makedirs(path)

        root = os.getcwd()
        os.chdir(path)

        if package and package not in cfg['dependencies']:

            name, version = package.split('@', 2)
            module = Package(name, version, environment)

            try:
                module.call('_'.join(['cmd', command]))
            except AttributeError:
                print('Not a valid command:', command)
                exit(1)

            # Write out the new config.
            os.chdir(root)
            cfg['dependencies'][name] = version
            with open('terminus.new', 'w') as outfile:
                yaml.dump(cfg, outfile)

        else:

            for name, config in cfg['dependencies'].items():

                if package and package != name:
                    continue

                module = Package(name, config, environment)

                try:
                    module.call('_'.join(['cmd', command]))
                except AttributeError as e:
                    print(e)
                    print('Not a valid command:', command)
                    exit(1)

            os.chdir(root)

