from qiskit import QuantumCircuit
from feature_extractors.graphs import *



class FeatureExtracter():
    def __init__(self, circuit: QuantumCircuit = None):
        self.circuit = circuit


# ───────────────────────────────────────── static features

class StaticFeatureExtractor(FeatureExtracter):

    def __init__(self, circuit: QuantumCircuit = None):
        """
        Initializes the StaticFeatureExtractor with a given QuantumCircuit.
        Args:
            circuit (QuantumCircuit, optional): The quantum circuit to analyze.
        """
        super().__init__(circuit)
        self.extracted_features = {}

    def getNumberOfQubits(self):
        """
        Returns the number of qubits in the circuit.
        Returns:
            dict: {"num_qubits": int}
        """
        if "num_qubits" in self.extracted_features:
            return {"num_qubits": self.extracted_features["num_qubits"]}
        value = self.circuit.num_qubits if self.circuit else 0
        self.extracted_features["num_qubits"] = value
        return {"num_qubits": value}

    def getGateCounts(self):
        """
        Returns a count of each gate type in the circuit.
        Returns:
            dict: {"gate_counts": {str: int}}
        """
        if "gate_counts" in self.extracted_features:
            return {"gate_counts": self.extracted_features["gate_counts"]}
        if not self.circuit:
            self.extracted_features["gate_counts"] = {}
            return {"gate_counts": {}}
        gate_counts = Counter(instruction.operation.name for instruction in self.circuit.data)
        self.extracted_features["gate_counts"] = dict(gate_counts)
        return {"gate_counts": dict(gate_counts)}

    def getWidth(self):
        """
        Returns the width of the circuit.
        Returns:
            dict: {"width": int}
        """
        if "width" in self.extracted_features:
            return {"width": self.extracted_features["width"]}
        value = self.circuit.width() if self.circuit else 0
        self.extracted_features["width"] = value
        return {"width": value}

    def getName(self):
        """
        Returns the name of the circuit.
        Returns:
            dict: {"name": str}
        """
        if "name" in self.extracted_features:
            return {"name": self.extracted_features["name"]}
        value = self.circuit.name if self.circuit else "Unnamed Circuit"
        self.extracted_features["name"] = value
        return {"name": value}

    def getTwoQubitGateCount(self):
        """
        Returns the number of two-qubit gates in the circuit.
        Returns:
            dict: {"two_qubit_gate_count": int}
        """
        if "two_qubit_gate_count" in self.extracted_features:
            return {"two_qubit_gate_count": self.extracted_features["two_qubit_gate_count"]}
        if not self.circuit:
            self.extracted_features["two_qubit_gate_count"] = 0
            return {"two_qubit_gate_count": 0}
        two_qubit_gates = [inst for inst in self.circuit.data if len(inst.qubits) == 2]
        value = len(two_qubit_gates)
        self.extracted_features["two_qubit_gate_count"] = value
        return {"two_qubit_gate_count": value}

    def getTwoQubitGatePercentage(self):
        """
        Returns the percentage of two-qubit gates in the circuit.
        Returns:
            dict: {"two_qubit_gate_percentage": float}
        """
        if "two_qubit_gate_percentage" in self.extracted_features:
            return {"two_qubit_gate_percentage": self.extracted_features["two_qubit_gate_percentage"]}
        two_qubit_gates = self.getTwoQubitGateCount()["two_qubit_gate_count"]
        total_gates = len(self.circuit.data) if self.circuit else 0
        percentage = (two_qubit_gates / total_gates) * 100 if total_gates > 0 else 0.0
        self.extracted_features["two_qubit_gate_percentage"] = percentage
        return {"two_qubit_gate_percentage": percentage}
    
    def getPauliGateCount(self):
        """
        Returns the count of Pauli gates (X, Y, Z) in the circuit.
        Returns:
            dict: {"pauli_gate_count": int}
        """
        if "pauli_gate_count" in self.extracted_features:
            return {"pauli_gate_count": self.extracted_features["pauli_gate_count"]}
        if not self.circuit:
            self.extracted_features["pauli_gate_count"] = 0
            return {"pauli_gate_count": 0}
        pauli_gates = [inst for inst in self.circuit.data if inst.operation.name in ['x', 'y', 'z']]
        value = len(pauli_gates)
        self.extracted_features["pauli_gate_count"] = value
        return {"pauli_gate_count": value}

    def extractAllFeatures(self) -> dict[str, Any]:
        """
        Extracts all basic features from the quantum circuit.
        Returns:
            dict: All extracted features.
        """
        features = {
            "num_qubits": self.getNumberOfQubits()["num_qubits"],
            "gate_counts": self.getGateCounts()["gate_counts"],
            "width": self.getWidth()["width"],
            "name": self.getName()["name"],
            "pauli_gate_count": self.getPauliGateCount()["pauli_gate_count"],
            "two_qubit_gate_count": self.getTwoQubitGateCount()["two_qubit_gate_count"],
            "two_qubit_gate_percentage": self.getTwoQubitGatePercentage()["two_qubit_gate_percentage"]
        }
        return features