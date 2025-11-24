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
    # Verificar si hay un agente activo
    # oidc-agent --status necesita la variable de entorno OIDC-SOCK para verificar
    try:
        # Crear un nuevo entorno que incluya las variables actuales
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

    # Generar cadena aleatoria de 6 caracteres alfanumericos
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

    # Construir la ruta del socket
    socket_path = f"/tmp/oidc-{random_str}/oidc-agent.{os.getpid()}"

    # Construir comando con argumentos adicionales
    cmd = ['oidc-agent', '-a', socket_path] + list(args)

    print("Nuevo agente creado")
    try:
        # Ejecutar oidc-agent y capturar la salida
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        output = result.stdout.strip()

        # Dividir por punto y coma
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

        # Procesar comandos en orden
        for cmd_line in commands:
            # Ignorar comandos 'export' sin asignación
            if cmd_line == 'export OIDC_SOCK' or cmd_line == 'export OIDCD_PID':
                continue

            # Procesar asignaciones
            if '=' in cmd_line and not cmd_line.startswith('echo'):
                parts = cmd_line.split('=',1)
                key = parts[0].strip()
                value = parts[1].strip().strip('"').strip("'")
                os.environ[key] = value

            # Procesar echo con expansión de variables
            elif cmd_line.startswith('echo '):
                echo_content = cmd_line[5:] # Remover 'echo '
                # Expandir variables de entorno $VAR
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