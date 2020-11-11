# -*- coding: utf-8 -*-
import sys
from subprocess import call

import ensure_zipapps_{output_name}


def main():
    has_main = {has_main}
    if has_main:
        if {main_shell}:
            shell_args = [sys.executable, '-c', '{import_main};{run_main}']
            call(shell_args, shell={shell})
        else:
            {import_main}
            {run_main}
            return
    else:
        shell_args = [sys.executable] + sys.argv[1:]
        call(shell_args, shell={shell})


if __name__ == "__main__":
    main()
