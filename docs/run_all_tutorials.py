import os
import sys


if __name__ == "__main__":
    path = "tutorials/code"
    files = [
        f
        for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f))
        and f[0].isnumeric()
        and f.endswith(".py")
    ]

    python = sys.executable

    os.chdir(path)
    for file in files:
        system_str = f"{python} {file}"
        print(f"executing {system_str}")
        os.system(system_str)

    print(f"{files} all done")