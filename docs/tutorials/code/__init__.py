# run all tutorials

import os

if __name__ == '__main__':
    files = os.listdir('.')

    for file in files:
        if file.endswith('.py') and file != "__init__.py":
            print("================ execute %s ====================" % file)
            os.system(file)
        