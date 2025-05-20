import sys, pathlib, qiskit
from utils.feature_extractors import extract_all
from utils.save_utils import save_circuit
from generator import *

def main():
    print("Hello from inferq!")

# if __name__ == "__main__":
#     main()


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    circ = ghz(n)
    feats = extract_all(circ)
    save_circuit(circ, feats, pathlib.Path("circuits"))