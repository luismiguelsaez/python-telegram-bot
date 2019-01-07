import psutil
import subprocess


def check_running(name):

    exists = -1

    for proc in psutil.process_iter():
        if proc.name() == name:
            exists = proc.pid

    return exists


def run(command):

    exec_command = command.split(' ')

    return_code = -1

    try:
        p = subprocess.run(args=exec_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return_code = p.returncode
    except Exception as err:
        return_code = 1

    return return_code
