# Classical Calculations

The classical calculations are organized in several steps:

## a. Supercell generation
- Setting up the supercell that contains the periodic system ready for the CP2K calculations. Example can be a supercell of Al(111) surface and inhibitor on top of the Al(111) substrate
- The script for generating the supercell is [`here`](0_classical_calculations/0_supercell_generation/supercell_generator) (download [`here`](0_classical_calculations/0_supercell_generation/supercell_generator.py)).

## b. Geometry Optimization
- We need to optimize the geometry of the system to get the best possible structure to feed to the DFT calculation. Here we use ASE to optimize the structure with machine learning potential to accelerate the calculation with near DFT quality.
- More details regarding the geometry optimization steps are [`detailed here`](0_classical_calculations/1_geometry_optimization/gemetry_optimize.md) and the related script can be downloaded from [`here`](0_classical_calculations/1_geometry_optimization/geo_opt.py)

## c. Supercell Calculations
- Now, we can perform the DFT calculations for the periodic system. Please follow the details [`here`](0_classical_calculations/2_supercell_calculation/supercell_calculation.md) regarding the system setup and calculational details where the supercell DFT calculations is performed using CP2K code.

## d. Binding Energy Calculation
- Now, we can calculate the binding energy of the inhibitor on the Al(111) surface. The script for calculating the binding energy and more details are [`in this page`](0_classical_calculations/5_binding_energy/binding_energy.md) 