Data description
------------------------------------------------------------
Political collaboration in the Dutch parlement (Tweede Kamer) over the period 2013-2022. Each node represents an MP that was active in parlement during this period. Each edge indicate that two MPs collaborated on a motion (Motie) and the weight indicates how often such a collaboration took place. 

Data was extracted on December 2022 from the open data portal of the Dutch parlement.

API link: https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/
Information link (Dutch only): https://opendata.tweedekamer.nl/documentatie/odata-api

Files:
----------------------------------------------------------------------
politician_network.gml		Network of the MPs and collaborations in GML format. Node labels are IDs from the open data portal.
MP.json						JSON file that contains the name associated to each MP ID and also the ID of their political party.
Party.json					JSON file that contains information of each political party based on the party ID.