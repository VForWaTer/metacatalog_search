from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
from setuptools.command.egg_info import egg_info


def requirements():
    with open('requirements.txt') as f:
        return f.read().split('\n')


def version():
    with open('VERSION') as f:
        return f.read().strip()


def readme():
    with open('README.md') as f:
        return f.read()

def install_and_migrate():
    try:
        from metacatalog_search import manage
    except ModuleNotFoundError:
        pass

    try:
        manage.install(verbose=True)
    except:
        pass


class PostDevelopCommand(develop):
    def run(self):
        print('DEVELOP RUNNING')
        develop.run(self)
        install_and_migrate()


class PostInstallCommand(install):
    def run(self):
        print('INSTALL RUNNNIG')
        install.run(self)
        install_and_migrate()


class PostEggInfoCommand(egg_info):
    def run(self):
        print('EGG_INFO RUNNING')
        egg_info.run(self)
        install_and_migrate()


setup(
    name='metacatalog_search',
    author='Mirko Mälicke',
    author_email='mirko.maelicke@kit.edu',
    license='GPL v3',
    install_requires=requirements(),
    version=version(),
    description='Full-Text Search extenstion for Metacatalog',
    long_description=readme(),
    long_description_content_type='text/markdown',
    packages=find_packages(),
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
        'egg_info': PostEggInfoCommand
    },
    include_package_data=True
)
