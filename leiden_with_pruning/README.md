
## 1. Methodology
The Leiden algorithm with the addition of pruning is realised by extending the work done in the `leiden` folder. An experiment is done for multiple thresholds of pruned edges ranging from `0%` to `50%` in increments of `2%`, as stated in the paper (https://arxiv.org/abs/cond-mat/0505245). The weakest edges in the whole graph are pruned first, but the edges that would completely disconnect a node are preserved. The pruning percentages that lead to the highest NMI and highest modularity are selected for their results to be further analyzed. The script automatically selects the `resolution_parameter` such that the number of communities will be as close as possible to the number of parties. This change to the original `leiden` script was a design choice to tackel the fact that the community fractionation has different thresholds for every pruning percentage.

## 2. Python Files and Generated Artifacts
The Python scripts process the raw data, construct the network, run the experiment, calculate evaluation metrics, and output the following artifacts, for each of the graphs selected based on the highest NMI and highest modularity:

*   **resolution_profile.html**: Illustrates the number of detected communities across different resolution parameters to help find an appropriate plateau.
*   **community_purity_matrix.csv**: Displays the dominant party per community, their total member counts, and the community's purity score.
*   **mp_community_mapping.csv**: A master list mapping every MP to their actual political party and their algorithm-assigned Leiden community.
*   **sankey_diagram.html**: Visualizes the flow of MPs from their actual political parties into the newly detected communities.
*   **network_graph_with_edges.html**: An interactive graph of the network where MP nodes are colored by their detected community.

Additionally, a history with the NMI scores and the modularity score along with the number of communities, can be seen for each pruning percentage in the file **edge_pruning_results.html**.
## 3. Results Interpretation
*   **Purity Scores**: Purity measures the percentage of a community comprised by its dominant party. The final values contain wide ranges compared to the original implementation:  from `[11%, 50%]` to `[12.5%, 100%]`. The weighted average purity increased from 28.45% in the original network to 34.93% for the graph selected by NMI and 32.68% for the graph selected by modularity. However, this increase should be interpreted cautiously, as purity is affected by the number and size of communities. Splitting communities into smaller groups can increase purity without necessarily indicating a stronger underlying party-community relationship. The reported average is weighted by community size, such that larger communities contribute proportionally more to the overall score
*   **NMI Score**: NMI measures how perfectly our communities align with actual parties and it was also used in this paper that we found (https://arxiv.org/abs/cond-mat/0505245). As seen in **sankey_diagram_2.html**, parties split broadly across different communities due to "noise" from weak, occasional co-sponsorships.


## 4. How to Run

Install libraries using:
```bash
pip install -r requirements.txt
```
Enter the directory with leiden implementation and results:
```bash
cd leiden_with_pruning
```
Execute the algorithm and get the results:
```bash
python main.py
```


