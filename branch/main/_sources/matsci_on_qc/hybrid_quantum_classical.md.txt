# Hybrid Quantum Classical Calculations

This document details the implementation of hybrid quantum-classical calculations, combining classical DFT with quantum computing methods through active space embedding.

## Implementation Overview

### Classical Component (CP2K)
- PBE exchange-correlation functional with GGA
- GPW method (500 Ry plane-wave cutoff, 60 Ry relative cutoff)
- DZVP-MOLOPT-GTH basis sets
- DFT-D3 dispersion correction
- Periodic boundary conditions with 25 Å vacuum gap
- 4×4 supercell of Al(111)
- Fermi-Dirac distribution (1000 K electronic temperature)

### Quantum Component (Qiskit)
- Active space: 2 electrons in 5 orbitals
- ADAPT-VQE algorithm implementation
- UCCSD ansatz
- SPSA optimizer configuration:
  ```python
  optimizer = SPSA(
      maxiter=1000,
      learning_rate=0.005,
      perturbation=0.05,
      last_avg=1
  )
  ```

## Workflow Structure

1. **Classical DFT Calculation (CP2K)**
   ```shell
   # Run CP2K calculation with active space embedding
   cp2k -i Al111_active_space.inp
   ```

2. **Quantum Computation (ADAPT-VQE)**
   ```shell
   # Execute quantum calculation with specified parameters
   python client-vqe-ucc.py --nalpha 1 --nbeta 1 --norbs 5 --adapt
   ```

3. **Integration and Execution**
   ```shell
   # Combined workflow execution
   ./run.sh
   ```

## Active Space Configuration

The active space calculation is configured in CP2K with the following key parameters:

```
&ACTIVE_SPACE
  ACTIVE_ELECTRONS 2        # Number of active electrons
  ACTIVE_ORBITALS 5        # Number of active orbitals
  SCF_EMBEDDING TRUE       # Enable SCF embedding
  EPS_ITER 1E-6           # Convergence criterion for embedding iterations
  MAX_ITER 100            # Maximum number of embedding iterations
  AS_SOLVER QISKIT        # Using Qiskit as the active space solver
  ORBITAL_SELECTION CANONICAL  # Method for selecting active orbitals
```

### Key Components
- **Active Space Size**: 2 electrons in 5 orbitals around the Fermi level
- **Embedding Method**: Self-consistent field (SCF) embedding with convergence threshold of 1E-6
- **Orbital Selection**: Using canonical orbitals (energy-ordered) for active space selection

### ERI Configuration
```
&ERI
  METHOD FULL_GPW        # Full Gaussian and Plane Waves method
  PERIODICITY 1 1 1      # Periodic boundary conditions in all directions
  OPERATOR <1/r>         # Coulomb operator for electron repulsion
&END ERI

&ERI_GPW
  CUTOFF 500            # Plane wave cutoff for ERI calculation
  REL_CUTOFF 60         # Relative cutoff for GPW method
&END ERI_GPW
```

The active space solver (Qiskit) receives the one- and two-electron integrals through FCIDUMP format, enabling seamless integration between the classical DFT calculation in CP2K and the quantum computation of the active space using VQE.

## Key Features

- Socket-based communication between CP2K and Qiskit
- Active space transformation for periodic systems
- Multiple VQE implementations:
  - Standard VQE with UCCSD
  - AdaptVQE with dynamic ansatz
  - StatefulVQE with warm-starting
  - StatefulAdaptVQE 

## Implementation Files

The complete implementation details can be found in the following documentation:

- [VQE Client Implementation Documentation](1_hybrid_quantum_classical_calculations/supercell_calculation/client-vqe-ucc.md)
- [CP2K Input Configuration Documentation](1_hybrid_quantum_classical_calculations/supercell_calculation/Al111_active_space.md)
- [Execution Script Documentation](1_hybrid_quantum_classical_calculations/supercell_calculation/run.md)
- [Structure File Documentation](1_hybrid_quantum_classical_calculations/supercell_calculation/al_slab_with_triazole_4x4x6_v10.0.md)

Source files:
- [client-vqe-ucc.py](1_hybrid_quantum_classical_calculations/supercell_calculation/client-vqe-ucc.py)
- [Al111_active_space.inp](1_hybrid_quantum_classical_calculations/supercell_calculation/Al111_active_space.inp)
- [run.sh](1_hybrid_quantum_classical_calculations/supercell_calculation/run.sh)
- [al_slab_with_triazole_4x4x6_v10.0.xyz](1_hybrid_quantum_classical_calculations/supercell_calculation/al_slab_with_triazole_4x4x6_v10.0.xyz)
