import ase
from ase.io import read, write
import numpy as np
from orb_models.forcefield import pretrained
from orb_models.forcefield.calculator import ORBCalculator
from ase.optimize import BFGS
from ase import Atoms
import re
import sys
import argparse
from datetime import datetime
import os

def calculate_molecule_surface_distance(atoms):
    """Calculate the average distance between the molecule and the surface."""
    molecule_positions = atoms.positions[atoms.get_tags() == 0]
    surface_positions = atoms.positions[atoms.get_tags() == 1]
    
    distances = []
    for mol_pos in molecule_positions:
        min_dist = min(np.linalg.norm(mol_pos - surf_pos) for surf_pos in surface_positions)
        distances.append(min_dist)
    
    return np.mean(distances)

def analyze_structure(atoms, energy):
    """Analyze key structural parameters."""
    avg_distance = calculate_molecule_surface_distance(atoms)
    
    forces = atoms.get_forces()
    max_force = np.max(np.linalg.norm(forces, axis=1))
    avg_force = np.mean(np.linalg.norm(forces, axis=1))
    
    # Calculate max displacement from initial positions for molecule atoms
    mol_indices = np.where(atoms.get_tags() == 0)[0]
    if hasattr(atoms, 'initial_positions'):
        max_displacement = np.max(np.linalg.norm(
            atoms.positions[mol_indices] - atoms.initial_positions[mol_indices], 
            axis=1
        ))
    else:
        max_displacement = 0.0
    
    return {
        'energy': energy,
        'avg_mol_surf_distance': avg_distance,
        'max_force': max_force,
        'avg_force': avg_force,
        'max_displacement': max_displacement
    }

def main():
    parser = argparse.ArgumentParser(description='Optimize structure using ORB with enhanced monitoring.')
    parser.add_argument('input_file', help='Path to the input XYZ file')
    parser.add_argument('--device', default='cpu', choices=['cpu', 'cuda'], 
                       help='Device to run calculations on (default: cpu)')
    parser.add_argument('--fmax', type=float, default=0.01,
                       help='Maximum force criterion for optimization (default: 0.01)')
    parser.add_argument('--output', default='optimized_structure.xyz',
                       help='Output file name (default: optimized_structure.xyz)')
    parser.add_argument('--save-interval', type=int, default=5,
                       help='Save intermediate structure every N steps (default: 5)')
    parser.add_argument('--max-steps', type=int, default=200,
                       help='Maximum number of optimization steps (default: 200)')
    
    args = parser.parse_args()

    # Create output directory with timestamp and input file name
    basename = os.path.splitext(os.path.basename(args.input_file))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"orb_opt_{basename}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    # Set up logging
    log_file = os.path.join(output_dir, "optimization.log")
    trajectory_file = os.path.join(output_dir, "optimization.traj")
    analysis_file = os.path.join(output_dir, "analysis.txt")

    def parse_lattice(lattice_str):
        numbers = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", lattice_str)]
        return np.array(numbers).reshape(3, 3)

    # Read structure
    try:
        with open(args.input_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Could not find file '{args.input_file}'")
        sys.exit(1)

    # Parse header
    try:
        header = lines[1]
        lattice_str = re.search(r'Lattice="([^"]+)"', header).group(1)
        pbc_str = re.search(r'pbc="([^"]+)"', header).group(1)
    except (IndexError, AttributeError):
        print("Error: File format incorrect. Expected extended XYZ format with Lattice and pbc information.")
        sys.exit(1)

    cell = parse_lattice(lattice_str)
    pbc = [x.strip().lower() == 't' for x in pbc_str.split()]

    # Parse atoms
    symbols = []
    positions = []
    tags = []

    for line in lines[2:]:
        if line.strip():
            try:
                parts = line.split()
                symbols.append(parts[0])
                positions.append([float(x) for x in parts[1:4]])
                tags.append(int(parts[4]))
            except (IndexError, ValueError) as e:
                print(f"Error parsing line: {line.strip()}")
                print(f"Error details: {e}")
                sys.exit(1)

    atoms = Atoms(
        symbols=symbols,
        positions=positions,
        cell=cell,
        pbc=pbc,
        tags=tags
    )
    
    # Store initial positions for displacement analysis
    atoms.initial_positions = atoms.positions.copy()

    print(f"Successfully loaded structure with {len(atoms)} atoms")
    print(f"Output directory created: {output_dir}")

    # Initialize model
    print(f"Initializing ORB-D3 model on {args.device}...")
    orbff = pretrained.orb_d3_v2(device=args.device)
    calc = ORBCalculator(orbff, device=args.device)
    atoms.calc = calc  # Updated syntax for setting calculator

    # Initial analysis
    initial_energy = atoms.get_potential_energy()
    initial_analysis = analyze_structure(atoms, initial_energy)
    
    with open(analysis_file, 'w') as f:
        f.write("Initial structure analysis:\n")
        for key, value in initial_analysis.items():
            f.write(f"{key}: {value:.6f}\n")
        f.write("\n")

    print(f"Initial energy: {initial_energy:.3f} eV")
    print(f"Initial molecule-surface distance: {initial_analysis['avg_mol_surf_distance']:.3f} Å")

    # Set up optimizer with trajectory saving
    opt = BFGS(atoms, trajectory=trajectory_file, logfile=log_file, maxstep=0.2)  # Added maxstep for safer optimization
    
    # Custom observer function
    def observer():
        current_energy = atoms.get_potential_energy()
        analysis = analyze_structure(atoms, current_energy)
        
        with open(analysis_file, 'a') as f:
            f.write(f"Step {opt.get_number_of_steps()}:\n")
            for key, value in analysis.items():
                f.write(f"{key}: {value:.6f}\n")
            f.write("\n")
        
        if opt.get_number_of_steps() % args.save_interval == 0:
            intermediate_file = os.path.join(output_dir, f"structure_step_{opt.get_number_of_steps()}.xyz")
            write(intermediate_file, atoms, format='extxyz')

    opt.attach(observer)

    # Run optimization
    print("Starting geometry optimization...")
    try:
        opt.run(fmax=args.fmax, steps=args.max_steps)
        optimization_status = "Converged"
    except Exception as e:
        optimization_status = f"Failed: {str(e)}"
        print(f"Optimization failed: {e}")
    
    # Final analysis
    final_energy = atoms.get_potential_energy()
    final_analysis = analyze_structure(atoms, final_energy)
    
    print("\nOptimization complete!")
    print(f"Status: {optimization_status}")
    print(f"Final energy: {final_energy:.3f} eV")
    print(f"Energy change: {final_energy - initial_energy:.3f} eV")
    print(f"Final molecule-surface distance: {final_analysis['avg_mol_surf_distance']:.3f} Å")
    print(f"Maximum atomic displacement: {final_analysis['max_displacement']:.3f} Å")
    
    # Save final structure
    final_structure_path = os.path.join(output_dir, args.output)
    write(final_structure_path, atoms, format='extxyz')
    print(f"Optimized structure saved to {final_structure_path}")
    print(f"Full optimization details available in {output_dir}")

if __name__ == "__main__":
    main()