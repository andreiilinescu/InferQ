

from generators.state_prep_circuits import wstate
from feature_extractors.graph_features import *

from rustworkx.visualization import mpl_draw
import matplotlib.pyplot as plt


# Generate a circuit
n = 5
circuit = wstate.generate(n)
print(circuit)

print("IG graph created")

# Generate Graph
graph = convertToPyGraphIG(circuit)

# Draw the graph
plt.figure()
mpl_draw(graph, with_labels=True, edge_labels=int)
plt.savefig("my_graph.png")
# Saved

print("IG graph Metrics for Circuit")
print(getMinCutDegree(graph, circuit))
print(getDiameter(graph, circuit))