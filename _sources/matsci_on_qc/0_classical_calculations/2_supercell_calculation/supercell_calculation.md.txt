---
title: Supercell Calculations
summary: CP2K calculations for periodic Al(111)-triazole system
---

# Supercell Calculations

This directory contains the CP2K calculations for the periodic Al(111) surface with triazole system. The calculations use periodic boundary conditions with a 4x4 surface unit cell and include the complete system (surface + adsorbate) for total energy calculations.

## System Details

The cell parameters from cp2k.log (reference lines 3-9):

```
Vector a [angstrom]:    11.455     0.000     0.000   |a| =    11.455130
Vector b [angstrom]:     5.728     9.920     0.000   |b| =    11.455130
Vector c [angstrom]:     0.000     0.000    40.000   |c| =    40.000000
Angle (b,c), alpha [degree]: 90.000000
Angle (a,c), beta [degree]: 90.000000
Angle (a,b), gamma [degree]: 60.000000
```

## Calculation Setup

The calculation uses:
- DFT with PBE functional
- DZVP-MOLOPT basis set
- GTH pseudopotentials
- Periodic boundary conditions (XYZ)
- Gamma-point sampling
- OT (Orbital Transformation) method for SCF

## Input Files

1. Structure file (`al_slab_with_triazole_4x4x6_v10.0.xyz`):
- 4×4 Al(111) surface supercell
- 6 layers of Al atoms
- Triazole molecule at optimized geometry
- Vacuum spacing of 10 Å

2. CP2K input file (`Al111_active_space.inp`):
- Complete DFT setup
- Cell parameters and periodicity
- Electronic structure calculation parameters

## Output Files

- `Al111_4x4_active_space_adsorbate-RESTART.wfn`: Wavefunction file
- `cp2k.log`: Main output file containing:
  - Energy convergence
  - Forces
  - Electronic structure information
- `run.log`: Runtime information

## CP2K Input File

The complete CP2K input file (`Al111_active_space.inp`):

```
&GLOBAL
  PROJECT Al111_4x4_active_space_adsorbate
  PRINT_LEVEL MEDIUM
  RUN_TYPE ENERGY
&END GLOBAL

&FORCE_EVAL
  METHOD QUICKSTEP
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME POTENTIAL
    &QS
      METHOD GPW
      EPS_DEFAULT 1.0E-10
      EXTRAPOLATION ASPC
      EXTRAPOLATION_ORDER 3
    &END QS
    &POISSON
      PERIODIC XYZ
    &END POISSON
    &MGRID
      CUTOFF 500
      REL_CUTOFF 60
      NGRIDS 5
    &END MGRID
    &SCF
      SCF_GUESS MOPAC
      EPS_SCF 1.0E-6
      MAX_SCF 500
      ADDED_MOS 100
      &DIAGONALIZATION
        ALGORITHM STANDARD
        EPS_ADAPT 0.01
      &END DIAGONALIZATION
      &MIXING
        METHOD BROYDEN_MIXING
        ALPHA 0.1
        BETA 1.5
        NBROYDEN 8
      &END MIXING
      &SMEAR
        METHOD FERMI_DIRAC
        ELECTRONIC_TEMPERATURE [K] 1000
      &END SMEAR
      &OUTER_SCF
        MAX_SCF 50
        EPS_SCF 1.0E-6
      &END OUTER_SCF
      &PRINT
        &RESTART ON
        &END
      &END PRINT
      IGNORE_CONVERGENCE_FAILURE
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
      &VDW_POTENTIAL
        DISPERSION_FUNCTIONAL PAIR_POTENTIAL
        &PAIR_POTENTIAL
          TYPE DFTD3
          PARAMETER_FILE_NAME dftd3.dat
          REFERENCE_FUNCTIONAL PBE
        &END PAIR_POTENTIAL
      &END VDW_POTENTIAL
    &END XC
    &PRINT
      &MO
        ENERGIES TRUE
        OCCUPATION_NUMBERS TRUE
        &EACH
          QS_SCF 0
        &END
      &END
    &END PRINT
  &END DFT
  &SUBSYS
    &CELL
      A 11.45512985522207 0.00000000000000 0.0000000000
      B 5.727564927611035 9.92043345827187 0.0000000000
      C 0.000000000000000 0.00000000000000 40.000000000
      PERIODIC XYZ
    &END CELL
    &TOPOLOGY
      COORD_FILE_NAME al_slab_with_triazole_4x4x6_v10.0.xyz
      COORD_FILE_FORMAT xyz
    &END TOPOLOGY
    &KIND Al
      BASIS_SET DZVP-MOLOPT-SR-GTH
      POTENTIAL GTH-PBE-q3
    &END KIND
    &KIND C
      BASIS_SET DZVP-MOLOPT-GTH
      POTENTIAL GTH-PBE-q4
    &END KIND
    &KIND N
      BASIS_SET DZVP-MOLOPT-GTH
      POTENTIAL GTH-PBE-q5
    &END KIND
    &KIND H
      BASIS_SET DZVP-MOLOPT-GTH
      POTENTIAL GTH-PBE-q1
    &END KIND            
  &END SUBSYS
&END FORCE_EVAL
```

## Run Script

The calculation can be executed using the following bash script (`run.sh`):

```bash
#!/bin/bash

# Set the current directory as the working directory
WORK_DIR=$(pwd)

# Function to check if a command was successful
check_success() {
    if [ $? -ne 0 ]; then
        echo "Error: $1 failed" >> $WORK_DIR/run.log
        exit 1
    fi
}

# Run CP2K in Docker
echo "Starting CP2K calculation..." >> $WORK_DIR/run.log
docker run --volume-driver local -v $WORK_DIR:/mnt --shm-size=1g --rm --user root cp2k/cp2k sh -c "umask 0000 && mpiexec -genv OMP_NUM_THREADS=1 -np 48 cp2k Al111_active_space.inp" > $WORK_DIR/cp2k.log 2>&1 &

# Store the Docker process ID
DOCKER_PID=$!

# Wait for the socket file to be created
while [ ! -S $WORK_DIR/embedding_socket ]; do
   sleep 1
done

# Run the Python script
echo "Starting Python VQE calculation..." >> $WORK_DIR/run.log
python -u client-vqe-ucc.py --nalpha 1 --nbeta 1 --norbs 5 --adapt > $WORK_DIR/python_output.log 2>&1 &

#PYTHON_PID=$!

# Wait for both processes to finish
wait $DOCKER_PID
check_success "CP2K calculation"

#wait $PYTHON_PID
#check_success "Python VQE calculation"

# Ensure all files are readable and writable
chmod -R a+rw $WORK_DIR

echo "Calculations completed. Check cp2k.log and python_output.log for results." >> $WORK_DIR/run.log
```

where you run the script in the directory containing the input file and structure file. as:
```bash
bash run.sh
```