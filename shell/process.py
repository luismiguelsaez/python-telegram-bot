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

    try:
        p = subprocess.run(args=exec_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return_code = p.returncode
    except Exception as err:
        return_code = 1

    return return_code

def run_output(command):

    exec_command = command.split(' ')

    return_code = -1

    result = {}

    try:
        p = subprocess.run(args=exec_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        result['code'] = p.returncode
        result['output'] = p.stdout.decode("utf-8")
    except Exception as err:
        result['code'] = return_code
        result['output'] = str(err)

    return result