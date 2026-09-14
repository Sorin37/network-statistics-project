# Dutch Political Collaboration Network

This folder contains the cleaned network data used as a common input for the Louvain, Leiden, and WEO community-detection implementations. The cleaning process does not run or tune any community-detection method.

## Cleaned files

- `data_cleaning.ipynb`: Loads the raw GML and JSON files, checks the original statistics, adds MP names and party metadata, labels missing parties as `Unknown`, checks duplicate edges, removes five self-loops, creates the full graph and largest connected component, and exports the cleaned tables.
- `nodes_clean.csv`: Node table with one row per MP. Its 365 rows contain `node_id`, `name`, `party`, and `party_id`, mainly for interpreting detected communities.
- `edges_clean.csv`: Edge table with one row per collaboration pair. Its 9,612 rows contain `source`, `target`, and the original, unmodified collaboration `weight`.
- `political_network_clean_full.gml`: Full cleaned network with 365 MPs, 9,612 edges, no self-loops, and three connected components of sizes 355, 9, and 1.
- `political_network_clean_lcc.gml`: Largest connected component with 355 MPs and 9,588 edges. This graph is connected and can be used when all methods need the same connected input network.

The original files are kept separately in `raw data/` and are not modified by the notebook.
