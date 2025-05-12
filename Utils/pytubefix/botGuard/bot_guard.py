import os
import subprocess
import sys

PLATFORM = sys.platform

NODE = 'node' if PLATFORM == 'linux' else 'node.exe'

NODE_PATH = os.path.dirname(os.path.realpath(__file__)) + f'/binaries/{NODE}'

if not os.path.isfile(NODE_PATH):
    NODE_PATH = 'node'

VM_PATH = os.path.dirname(os.path.realpath(__file__)) + '/vm/botGuard.js'

if NODE_PATH == "node":
    print("Nodejs is required to run botGuard. Searching for alternatives...")
    try:
        from .nodejs import node
        NODE_PATH = node.path
    except ImportError:
        print("Nodejs not found. Please install nodejs.")

if NODE_PATH != "node":
    print(f"Using {NODE_PATH} for nodejs. VM path: {VM_PATH}")

def generate_po_token(visitor_data: str) -> str:
    """
    Run nodejs to generate poToken through botGuard.

    Requires nodejs installed.
    """
    result = subprocess.check_output(
        [NODE_PATH, VM_PATH, visitor_data]
    ).decode()
    print("result: ", result)
    return result.replace("\n", "")