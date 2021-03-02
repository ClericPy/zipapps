# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from runpy import run_module, run_path
from subprocess import run
from tempfile import gettempdir

from activate_zipapps import activate


def activate_envs():
    activate()
    # try to activate the --zipapps env paths
    HANDLE_OTHER_ENVS_FLAG = "{HANDLE_OTHER_ENVS_FLAG}"
    try:
        index = sys.argv.index(HANDLE_OTHER_ENVS_FLAG)
        sys.argv.pop(index)
        env_paths = sys.argv.pop(index)
    except ValueError:
        env_paths = None
    if not env_paths:
        flag = HANDLE_OTHER_ENVS_FLAG + '='
        index_to_pop = None
        for index, value in enumerate(sys.argv):
            if value.startswith(flag):
                env_paths = value[len(flag):]
                index_to_pop = index
                break
        if index_to_pop is not None:
            sys.argv.pop(index_to_pop)
    if not env_paths:
        env_paths = r'''{env_paths}'''
    if env_paths:
        for env_path in env_paths.split(','):
            _env_path = ensure_env_path(env_path)
            if not _env_path.is_file():
                raise RuntimeError('%s is not exist.' % _env_path)
            activate(_env_path)


def ensure_env_path(env_path):
    if env_path.startswith('HOME'):
        env_path_path = Path.home() / (env_path[4:].lstrip('/\\'))
    elif env_path.startswith('SELF'):
        env_path_path = Path(__file__).parent.parent / (
            env_path[4:].lstrip('/\\'))
    elif env_path.startswith('TEMP'):
        env_path_path = Path(gettempdir()) / (env_path[4:].lstrip('/\\'))
    else:
        env_path_path = Path(env_path)
    return env_path_path


def main():
    activate_envs()
    has_main = {has_main}
    if has_main:
        if {main_shell}:
            shell_args = [sys.executable, '-c', '{import_main};{run_main}']
            run(shell_args, shell={shell})
        else:
            {import_main}
            {run_main}
            return
    else:
        args = sys.argv
        if len(args) > 1:
            arg1 = args[1]
            if arg1 == '-c':
                source = args[2]
                sys.argv = [arg1] + args[3:]
                return exec(source)
            elif arg1 == '-':
                source = sys.stdin.read()
                sys.argv = [arg1] + args[2:]
                return exec(source)
            elif arg1 == '-m':
                sys.argv = args[2:]
                return run_module(args[2], run_name='__main__')
            else:
                if Path(arg1).is_file():
                    sys.argv = args[1:]
                    return run_path(arg1, run_name='__main__')
                else:
                    # python [-bBdEhiIOqsSuvVWx?]
                    shell_args = [sys.executable] + args[1:]
                    run(shell_args, shell={shell})
        else:
            import code
            code.interact()


if __name__ == "__main__":
    main()
