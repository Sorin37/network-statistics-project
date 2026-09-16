# WEO Community Detection

This folder contains the WEO implementations used for community detection on the cleaned Dutch political collaboration network.

## Files

- `WEO_community.py`  
  Standard WEO. The number of communities is determined automatically.

- `fixed30.py`  
  Earlier Target-K implementation with `K = 30`.

- `target30.py`  
  Current clean Target-K implementation with `K = 30`.

## Results

- `results/`  
  Results from standard WEO.

- `results/fixed_k_30/`  
  Results from the earlier Target-K implementation.

- `results/target_k30_clean/`  
  Results from the current clean Target-K implementation.

## Output files

- `weo_communities.csv`  
  Community assignment for each MP.

- `weo_community_summary.csv`  
  Community size and total weighted strength.

- `weo_run_summary.csv`  
  Summary of WEO runs and modularity scores.

- `political_network_weo.gml`  
  Network with detected WEO community labels added.