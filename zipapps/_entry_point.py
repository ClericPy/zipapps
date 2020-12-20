# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from runpy import run_path, run_module
from subprocess import run

import ensure_zipapps_{output_name}


def main():
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
                fp = Path(args[2])
                if fp.is_dir() and (fp / '__main__.py').is_file():
                    sys.argv = args[2:]
                    return run_module(args[2], run_name='__main__')
                else:
                    raise RuntimeError('%s should be a folder which includes a __main__.py file.' % fp)
            else:
                if Path(arg1).is_file():
                    return run_path(arg1)
                else:
                    # python [-bBdEhiIOqsSuvVWx?]
                    shell_args = [sys.executable] + args[1:]
                    run(shell_args, shell={shell})
        else:
            import code
            code.interact()


if __name__ == "__main__":
    main()
