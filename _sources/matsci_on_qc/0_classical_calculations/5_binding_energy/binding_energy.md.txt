---
title: Binding Energy Calculations
summary: Analysis of inhibitor binding energy on Al(111) surface
---

# Binding Energy Calculations

This analysis calculates the binding energy of the triazole inhibitor on the Al(111) surface using the results from our DFT calculations. The binding energy indicates the strength of the interaction between the inhibitor and the surface.

## Calculation Method

The binding energy is calculated using the following formula:
```
E_binding = E_supercell - (E_substrate + E_inhibitor)
```

where:
- `E_supercell`: Total energy of the complete system (surface + inhibitor)
- `E_substrate`: Energy of the isolated Al(111) surface
- `E_inhibitor`: Energy of the isolated triazole molecule

## System Components

1. Complete System (Supercell):
   - 4×4 Al(111) surface with triazole
   - Total Energy: -241.400214 Hartree

2. Substrate:
   - Clean Al(111) surface
   - Total Energy: -198.415357 Hartree

3. Inhibitor:
   - Isolated triazole molecule
   - Total Energy: -42.970690 Hartree

## Results

The binding energy calculation yields:
- **Binding Energy: -8.890122 kcal/mol**

This negative value indicates:
- Favorable binding between inhibitor and surface
- Spontaneous adsorption process
- Stable surface-inhibitor complex

## Analysis Details

The calculation process involves:
1. DFT calculations for each component (see [`2_supercell_calculation`](../2_supercell_calculation/supercell_calculation.md))
2. Energy extraction from CP2K output files
3. Binding energy calculation using Python
4. Unit conversion from Hartree to kcal/mol

## Additional Analysis

For more detailed analysis, including:
- Geometric changes upon binding
- Electronic structure analysis
- Charge transfer investigation
- Orbital interactions

Please refer to the complete analysis notebook: [`classical_analysis.ipynb`](classical_analysis.ipynb)

