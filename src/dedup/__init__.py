"""Near-duplicate detection using MinHash LSH.

This package identifies and removes near-duplicate text chunks before
indexing, reducing storage waste and preventing retrieval of redundant
passages.  Similarity is measured via Jaccard distance on token shingles.
"""
