Purpose

Offer selection determines which GPU instance will be used.

The goal is to choose the cheapest valid instance satisfying all constraints.

Selection Input

The following constraints are applied:

Constraint	Source
minimum VRAM	sizing engine
max price per hour	config
network bandwidth	config
reliability	config
interruptible allowed	config
Selection Algorithm

Retrieve offers

Filter invalid offers

Sort remaining offers

Select best candidate

Filtering Rules

An offer must satisfy:

offer.vram_gb >= required_vram_gb
offer.dph <= max_dph
offer.inet_down >= min_inet_down_mbps
offer.inet_up >= min_inet_up_mbps
offer.reliability >= reliability_min
Sorting Priority

Offers are sorted by:

1. price (ascending)
2. reliability (descending)
Determinism

Sorting is stable.

This guarantees the same selection given identical inputs.