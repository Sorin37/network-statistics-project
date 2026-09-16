# Louvain Community Detection

## 1. Methodology

The Louvain algorithm was applied to the cleaned largest connected component (LCC) of the political collaboration network. The network contains 355 MPs and 9,588 weighted edges, where the edge weights represent the frequency of collaboration between MPs.

Louvain detects communities by optimizing modularity. The modularity calculation uses the configuration model as the default null model.

To check the sensitivity of the algorithm, different resolution parameters and random seeds were tested. A resolution of 1.0 was used for the final analysis. The different seeds generally resulted in 7 communities with similar modularity values, so seed 100 was selected as a reproducible representative partition.

## 2. Files

- `louvain_analysis_Nikoletta_version.ipynb`: Contains the complete Louvain analysis, including parameter sensitivity, community detection, evaluation, visualizations, and comparison with political parties.
- `louvain_community_mapping.csv`: Maps each MP to their political party and detected Louvain community.

## 3. Results

The final Louvain partition detected **7 communities** with a modularity of approximately **0.323**.

The detected communities were compared with the formal political-party affiliations of the MPs.

- **NMI:** approximately 0.119
- **ARI:** approximately 0.0066
- **Purity:** approximately 0.268

The party-composition analysis also shows that the communities contain MPs from several different political parties. These results indicate limited correspondence between the collaboration communities detected by Louvain and formal political-party membership.

## 4. Additional Analysis

As an additional exploratory analysis, the detected communities were compared with the political-compass coordinates provided in `Party.json`. These coordinates are defined at the party level rather than for individual MPs, so this analysis is treated only as additional interpretation.

## 5. How to Run

Open `louvain_analysis_Nikoletta_version.ipynb` and run all cells.

The notebook uses the cleaned network and party data located in the `data cleaning` folder of the repository.