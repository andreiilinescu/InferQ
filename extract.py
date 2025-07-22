from feature_extractors.graphs import IGGraphExtractor
from generators.state_prep_circuits import ghz, wstate
from generators.state_prep_circuits.ghz import BaseParams
from feature_extractors.graph_features import *
from feature_extractors.static_features import *
from feature_extractors.extractors import extract_features
from generators.circuit_merger import CircuitMerger
from matplotlib import pyplot as plt
from rustworkx.visualization import mpl_draw
# Generate a circuit
# n = 2
# circuit = wstate.WState(BaseParams(max_qubits=n, min_qubits=n,max_depth=n**2,min_depth=0)).generate(n)
# print(circuit)

# print("IG graph created")

# # Generate Graph
# iggraph = IGGraph(circuit=circuit)


base_params=BaseParams(max_qubits=20, min_qubits=2, max_depth=100,min_depth=2)
circuitMerger=CircuitMerger(base_params=base_params)
circuit=circuitMerger.generate_hierarchical_circuit()

# print(circuit)
# # Draw the graph
# plt.figure()
# mpl_draw(convertToPyGraphGDG(circuit), with_labels=True)
# plt.savefig("my_graph.png")
# # Saved


# Let us use the fetaure extractors and get the metrics
print("IG graph Metrics for Circuit\n\n\n\n\n")
features = extract_features(circuit=circuit)
print(features)