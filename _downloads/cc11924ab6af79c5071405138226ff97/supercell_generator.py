from ase.build import fcc111
from ase.io import write
from ase.visualize.plot import plot_atoms
import matplotlib.pyplot as plt
from rdkit import Chem
from rdkit.Chem import AllChem
from ase import Atoms
import numpy as np

def create_al_slabs_with_triazole(sizes, layers=4, vacuum=10.0, a=4.05, molecule_height=3.0):
    """
    Create aluminum (111) slabs of different sizes with multiple layers, vacuum, and a 1,2,4-Triazole molecule on top.
    
    Parameters:
    sizes (list of tuples): List of (x, y) sizes for the slab, e.g. [(2,2), (3,3), (4,4)]
    layers (int): Number of atomic layers in the slab (default is 4)
    vacuum (float): Vacuum size in Angstroms to add above and below the slab (default is 10.0)
    a (float): Lattice constant for aluminum in Angstroms (default is 4.05)
    molecule_height (float): Height of the molecule above the slab surface in Angstroms (default is 3.0)
    
    Returns:
    None, but saves .xyz files and .png visualizations for each slab with the molecule
    """
    # Generate 1,2,4-Triazole molecule
    smiles = "C1=NC=NN1"
    mol = Chem.MolFromSmiles(smiles)
    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, randomSeed=42)
    AllChem.UFFOptimizeMolecule(mol)
    
    # Convert RDKit molecule to ASE Atoms object
    positions = mol.GetConformer().GetPositions()
    symbols = [atom.GetSymbol() for atom in mol.GetAtoms()]
    triazole = Atoms(symbols=symbols, positions=positions)
    
    for size in sizes:
        # Create the slab with specified number of layers and vacuum
        slab = fcc111('Al', size=(size[0], size[1], layers), a=a, vacuum=vacuum)
        
        # Calculate the center of the slab in xy plane
        center_x = np.mean(slab.positions[:, 0])
        center_y = np.mean(slab.positions[:, 1])
        
        # Calculate the top of the slab
        top_z = np.max(slab.positions[:, 2])
        
        # Position the triazole molecule
        triazole.translate([center_x, center_y, top_z + molecule_height])
        
        # Combine slab and molecule
        combined = slab + triazole
        
        # Generate filenames
        xyz_filename = f"al_slab_with_triazole_{size[0]}x{size[1]}x{layers}_v{vacuum}.xyz"
        png_filename = f"al_slab_with_triazole_{size[0]}x{size[1]}x{layers}_v{vacuum}.png"
        
        # Save the combined structure as an XYZ file
        write(xyz_filename, combined)
        
        # Create visualizations of the combined structure (top and side views)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        
        # Top view
        plot_atoms(combined, ax1, radii=0.5, rotation=('0x,0y,0z'))
        ax1.set_title('Top View')
        ax1.axis('off')
        
        # Side view
        plot_atoms(combined, ax2, radii=0.5, rotation=('90x,0y,0z'))
        ax2.set_title('Side View')
        ax2.axis('off')
        
        plt.tight_layout()
        plt.savefig(png_filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Created {xyz_filename} with {len(combined)} atoms")
        print(f"Saved visualization as {png_filename}")

# Example usage
sizes_to_create = [(4,4)]
create_al_slabs_with_triazole(sizes_to_create, layers=6, vacuum=10.0, molecule_height=3.0)