# -*- coding: utf-8 -*-
"""
Author : Milton Rocha
Medium : https://medium.com/@milton-rocha
"""

dependencies = ('copy',
                'datetime',
                'dateutil',
                'numpy',
                'os',
                'pandas',
                'tabulate',
                'tempfile',
                'typeguard',
                'typing')

# Importação de dependências, caso não tenha, retorna um erro
# - Para cada uma das dependências tenta importar, caso não consiga, não possui

missing_dependencies = []

for dependency in dependencies:
    try:
        __import__(dependency)
    except ImportError:
        missing_dependencies.append(dependency)
    
if missing_dependencies:
    raise ImportError(
        "Missing required dependencies {0}".format(missing_dependencies))
    
del dependencies, dependency, missing_dependencies


#from global_variables import * # Importação de variáveis globais
from pyfiglet         import print_figlet as printf

def main():
    printf('Renda Fixa v1.0', colors = 'CYAN')
    print('\n-- Author : Milton Rocha (GitHub @milton-rocha)')

if __name__ == '__main__':
    main()
