
## 1. Methodology
The leiden algorithm was implemented using the `leidenalg` Python library for community detection. The algorithm was evaluated against the Configuration Model as our baseline (null model). To select the best resolution parameter, the generated Resolution Profile was analyzed (<code>artifacts/resolution_profile.html</code>) using the native bisection algorithm used by `leidenalg`. The selected value was located on a stable "plateau", a range where the number of communities remained constant, indicating a robust grouping. To select the best value, the number of political parties was also taken into account.

## 2. Python Files and Generated Artifacts
The Python scripts process the raw data, construct the network, run the algorithm, calculate evaluation metrics, and output the following artifacts:

*   **resolution_profile.html**: Illustrates the number of detected communities across different resolution parameters to help find the optimal plateau.
*   **community_purity_matrix_2.csv**: Displays the dominant party per community, their total member counts, and the community's purity score.
*   **mp_community_mapping.csv**: A master list mapping every MP to their actual political party and their algorithm-assigned Leiden community.
*   **sankey_diagram_2.html**: Visualizes the flow of MPs from their actual political parties into the newly detected communities.
*   **network_graph_with_edges_2.html**: An interactive graph of the network where MP nodes are colored by their detected community.

## 3. Results Interpretation
*   **Detected Communities**:  **12** distinct communities were detected. The VVD dominates 7 of them, while the others are led by the PvdA, CDA, FVD, GL, and PVV.
*   **Purity Scores**: Purity measures the percentage of a community comprised by its dominant party. The final values are low (ranging from 11% to 50%), demonstrating that communities are highly diverse and MPs collaborate heavily across party lines (check <code>artifacts/community_purity_matrix.csv</code>).
*   **NMI Score**: The Normalized Mutual Information (NMI) score is a very low **0.172**. NMI measures how perfectly our communities align with actual parties and it was also used in this paper that we found (https://arxiv.org/abs/cond-mat/0505245). As seen in **sankey_diagram_2.html**, parties split broadly across different communities due to "noise" from weak, occasional co-sponsorships.
*   **Remarks**: The VVD receives flow bands from nearly every community on the left, demonstrating their role across multiple varied policy domains. Most communities split their output across 3 or 4 different parties, confirming these are functional working groups. Community 10 (at 50% purity) likely displays a much thicker, more isolated flow to the PVV, reflecting their historical position outside standard coalition dynamics. 

## 4. Future Work
If a node has multiple edges, we can try to prune the weakest edges to remove occasional co-sponsorships. A similar preprocessing step was applied in the following paper that we found: Community Detection and Analysis of Political Alliances in the Brazilian Congress Voting Network (https://sol.sbc.org.br/index.php/sbsi/article/view/34370). The authors claimed that it improved the results. We can then run the Leiden algorithm again on this cleaned network to check if the quality and clarity of the partitions improve before we experiment with any other algorithms.

## 5. How to Run

Install libraries using:
```bash
pip install -r requirements.txt
```
Enter the directory with leiden implementation and results:
```bash
cd Leiden
```
Execute the algorithm and get the results:
```bash
python main.py
```


