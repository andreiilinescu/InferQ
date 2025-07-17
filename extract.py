from feature_extractors.graphs import IGGraph
from generators.state_prep_circuits import ghz, wstate
from generators.state_prep_circuits.ghz import BaseParams
from feature_extractors.graph_features import *


# Generate a circuit
n = 1000
circuit = wstate.WState(BaseParams(max_qubits=n, min_qubits=n,max_depth=n**2,min_depth=0)).generate(n)
# print(circuit)

# print("IG graph created")

# # Generate Graph
# iggraph = IGGraph(circuit=circuit)

# # Draw the graph
# plt.figure()
# mpl_draw(iggraph.rustxgraph, with_labels=True, edge_labels=int)
# plt.savefig("my_graph.png")
# # Saved


print("IG graph Metrics for Circuit")
# Let us use the fetaure extractors and get the metrics
graph_feature_extractor = GraphFeatureExtracter(circuit=circuit)
features = graph_feature_extractor.extractAllFeatures()
print(features)