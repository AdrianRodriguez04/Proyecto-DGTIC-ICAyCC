#!/usr/bin/env python3
import subprocess
import os
import sys
import random
import string

def create_agent(*args):
    """
    Crea un agente OIDC, eliminando primero cualquier agente activo si existe
    """
    #Verificar si hay un agente activo
    try:
        env = os.environ.copy()
        result = subprocess.run(
            ['oidc-agent', '--status'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            env=env
        )
        agent_active = (result.returncode == 0)
    except FileNotFoundError:
        print("Error: oidc-agent no encontrado en el PATH", file=sys.stderr)
        return 1

    if agent_active:
        print ("Eliminando agente activo")
        #Eliminar agente activo
        subprocess.run(
            ['oidc-agent', '-k'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )

    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

    socket_path = f"/tmp/oidc-{random_str}/oidc-agent.{os.getpid()}"

    cmd = ['oidc-agent', '-a', socket_path] + list(args)

    print("Nuevo agente creado")
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        output = result.stdout.strip()
        
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
            if cmd_line == 'export OIDC_SOCK' or cmd_line == 'export OIDCD_PID':
                continue

            if '=' in cmd_line and not cmd_line.startswith('echo'):
                parts = cmd_line.split('=',1)
                key = parts[0].strip()
                value = parts[1].strip().strip('"').strip("'")
                os.environ[key] = value

            elif cmd_line.startswith('echo '):
                echo_content = cmd_line[5:]
                import re
                def replace_var(match):
                    var_name = match.group(1)
                    return os.environ.get(var_name, '')

                expanded = re.sub(r'\$(\w+)', replace_var, echo_content)
                print(expanded)
        return result.returncode
    
    except Exception as e:
        print(f"Error al crear el agente: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    exit_code = create_agent(*sys.argv[1:])
    sys.exit(exit_code)