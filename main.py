import sys, pathlib, qiskit
<<<<<<< HEAD
from utils.feature_extractors import extract_all
from utils.save_utils import save_circuit
from generator import *

=======
from feature_extractors.main import extract_all
from utils.save_utils import save_circuit
from generator import *


>>>>>>> 0846e197500375a325dfb8401f6ad8c6fea888b1
def main():
    print("Hello from inferq!")

# if __name__ == "__main__":
#     main()


# if __name__ == "__main__":
#     main()


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    circ = ghz(n)
    feats = extract_all(circ)
<<<<<<< HEAD
    save_circuit(circ, feats, pathlib.Path("circuits"))
=======
    save_circuit(circ, feats, pathlib.Path("circuits"))
>>>>>>> 0846e197500375a325dfb8401f6ad8c6fea888b1
