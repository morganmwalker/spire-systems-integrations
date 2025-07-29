# spire-systems-integrations
Spire Systems integrations to work with Spire's API

## populate_po.py
This integration exists because Spire does not allow existing PO's to be updated through the import function. PO numbers are often provided to suppliers before the order is finalized, especially for big orders, in which case the import function would be especially useful. This integration provides a way to import csv files into existing PO's, and attempts to make the process even easier by automatically detecting headings and providing the option to add new items to inventory upon import. 
