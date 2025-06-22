#!/usr/bin/env python3

import sys
import subprocess

# Service definitions
services = {
    'db': 'docker-compose-db.yml',
    'backend': 'docker-compose-backend.yml', 
    'frontend': 'docker-compose-frontend.yml',
    'ollama': 'docker-compose-ollama.yml',
    'chromadb': 'docker-compose-chromadb.yml'
}

def run_service(action, service_file, build=True):
    cmd = ['docker', 'compose', '-f', service_file]
    if action == 'up':
        cmd.extend(['up', '-d'])
        if build:
            cmd.append('--build')
    else:
        cmd.append('down')
    subprocess.run(cmd)

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'up'
    service = sys.argv[2] if len(sys.argv) > 2 else None
    
    if action in ['up', 'start']:
        if service and service in services:
            run_service('up', services[service])
        else:
            # Start all services (except ollama)
            for name, file in services.items():
                if name != 'ollama':  # Skip ollama by default
                    run_service('up', file)
                    
    elif action in ['down', 'stop']:
        if service and service in services:
            run_service('down', services[service], build=False)
        else:
            # Stop all services
            for file in services.values():
                run_service('down', file, build=False)

if __name__ == '__main__':
    main()
