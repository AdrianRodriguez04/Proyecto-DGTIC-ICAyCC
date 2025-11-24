#!/usr/bin/env python3
import subprocess
import os
import sys
import glob
import signal
from pathlib import Path
from _create_agent import create_agent

def use_agent(*args):
    """
    Intenta reusar un agente OIDC existente, si no es posible crea uno nuevo.
    """
    username = os.environ.get('USER')
    if not username:
        username = os.environ.get('LOGNAME')

    if not username:
        try:
            import pwd
            username = pwd.getpwuid(os.getuid()).pw_name
        except:
            username = str(os.getuid())

    find_and_chmod('/tmp', username, 'oidc-agent-service', '1777')

    subprocess.run(
        ['oidc-agent', '-k'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False
    )

    pkill_user(username, 'oidc-agent')

    cleanup_temp_dirs('/tmp', username)

    try:
        result = subprocess.run(
            ['oidc-agent-service', 'use'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )

        reuse_success = (result.returncode == 0)

        if reuse_success:
            process_agent_output(result.stdout)

    except FileNotFoundError:
        print("Error: oidc-agent-service no encontrado en el PATH", file=sys.stderr)
        reuse_success = False

    if not reuse_success:
        pkill_user(username, 'oidc-agent')
        print("No se pudo reusar un agente, sre creara uno nuevo")

        cleanup_temp_dirs('/tmp', username)

        if 'OIDCD_PID' in os.environ:
            try: 
                pid = int(os.environ['OIDCD_PID'])
                os.kill(pid, signal.SIGKILL)
            except (ValueError, ProcessLookupError, PermissionError):
                pass

        for var in ['OIDC_SOCK', 'OIDCD_PID', 'OIDCD_PID_FILE']:
            os.environ.pop(var, None)

        return create_agent(*args)
    else:
        print("Se reuso el agente")

        find_and_chmod('/tmp', username, 'oidc-agent-service', '1777')
        return 0

def find_and_chmod(path, user, pattern, mode):
    """
    Busca archivos que coincidan con el patrón y cambia sus permisos.
    """

    try:
        for item in Path(path).glob(pattern):
            if item.is_file() or item.is_dir():
                if item.owner() == user:
                    os.chmod(item, int(mode, 8))
    except (PermissionError, OSError) as e:
        pass

def pkill_user(user, process_name):
    """
    Mata todos los procesos con el nombre dado del usuario.
    """
    try:
        subprocess.run(
            ['pkill', '-u', user, process_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )
    except FileNotFoundError:
        try:
            ps_output = subprocess.run(
                ['ps', 'u', user, '-o', 'pid', 'pid,comm'],
                stdout=subprocess.PIPE,
                text=True,
                check=False
            )
            for line in ps_output.stdout.split('\n')[1:]:
                parts = line.strip().split()
                if len(parts) >=2 and process_name in parts[1]:
                    try:
                        os.kill(int(parts[0]), signal.SIGTERM)
                    except (ValueError, ProcessLookupError, PermissionError):
                        pass
        except:
            pass

def cleanup_temp_dirs(path, user):
    """
    Elimina directorios temporales oidc-* excepto oidc-agent-*.
    """
    try:
        for item in Path(path).glob('oidc-*'):
            if not item.name.startswith('oidc-agent-'):
                try:
                    if item.owner() == user:
                        if item.is_dir():
                            import shutil
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            item.unlink()
                except (PermissionError, OSError):
                    pass
    except Exception:
        pass

def process_agent_output(output):
    """
    Procesa la salida de oidc-agent-service y establece variables de entorno.
    """
    if not output:
        return

    commands = []
    current = ""
    for char in output:
        if char == ';':
            if current.strip():
                commands.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        commands.append(current.strip())

    for cmd_line in commands:
        if cmd_line.startswith('export ') and '=' not in cmd_line:
            continue

        if '=' in cmd_line and not cmd_line.startswith('echo'):
            cmd_line = cmd_line.replace('export ', '')
            parts = cmd_line.split('=', 1)
            key = parts[0].strip()
            value = parts[1].strip().strip('"').strip("'")
            os.environ[key] = value

        elif cmd_line.startswith('echo '):
            import re
            echo_content = cmd_line[5:]
            def replace_var(match):
                var_name = match.group(1)
                return os.environ.get(var_name, '')

            expanded = re.sub(r'\$(\w+)', replace_var, echo_content)
            if expanded and 'Agent pid' in expanded:
                print(expanded)

if __name__ == "__main__":
    exit_code = use_agent(*sys.argv[1:])
    sys.exit(exit_code if exit_code is not None else 0)