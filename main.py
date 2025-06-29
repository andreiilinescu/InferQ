import sys
import pathlib
from feature_extractors.main import extract_all
from utils.save_utils import save_circuit
from generators import ghz, qft_entangled, wstate, qnn, qwalk


def main():
    print("Hello from inferq!")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    circ = qwalk(n=n, depth=5)
    print(circ)
