# VQE Client Implementation

This file implements the quantum-classical hybrid calculation using Qiskit and CP2K integration.

## Full Implementation

```python
#client-vqe-ucc.py
# pylint: disable=invalid-name
"""CP2K + Qiskit Nature embedding.

Usage:
    python dft-emb-client.py
"""

from __future__ import annotations

import argparse
import json
import logging
import numpy as np
import socket
import time

import numpy as np
from qiskit_algorithms.optimizers import L_BFGS_B, SPSA
from qiskit_algorithms import NumPyMinimumEigensolver
from qiskit.circuit.library import EvolvedOperatorAnsatz
from qiskit.primitives import Estimator
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import Aer
from qiskit_aer.primitives import Estimator as AerEstimator
from qiskit_nature.logging import logging as nature_logging
from qiskit_nature.second_q.algorithms import GroundStateEigensolver
from qiskit_nature.second_q.algorithms.excited_states_solvers import (
    QEOM, EvaluationRule)
from qiskit_nature.second_q.circuit.library import UCC, HartreeFock
from qiskit_nature.second_q.circuit.library.ansatzes.utils import \
    generate_fermionic_excitations
from qiskit_nature.second_q.mappers import ParityMapper
from qiskit_algorithms.minimum_eigensolvers import VQE

from qiskit_nature_cp2k.cp2k_integration import CP2KIntegration
from qiskit_nature_cp2k.stateful_adapt_vqe import StatefulAdaptVQE
from qiskit_nature_cp2k.stateful_vqe import StatefulVQE

from braket.aws import AwsDevice
from braket.devices import Devices
from braket.jobs import hybrid_job, save_job_result
from qiskit.primitives import BackendEstimator

from qiskit_braket_provider import BraketProvider
from qiskit_braket_provider import BraketLocalBackend

from qiskit_ibm_runtime import QiskitRuntimeService

np.set_printoptions(linewidth=500, precision=6, suppress=True)

logger = logging.getLogger(__name__)

level = logging.DEBUG

nature_logging.set_levels_for_names(
    {
        __name__: level,
        "qiskit": level,
        "qiskit_nature": level,
        "qiskit_nature_cp2k": level,
    }
)


if __name__ == "__main__":
    HOST = "embedding_socket"
    PORT = 12345
    UNIX = True #True
    shots = 0
    backend_name = ""

    parser = argparse.ArgumentParser()
    parser.add_argument("--nalpha", type=int, default=None)
    parser.add_argument("--nbeta", type=int, default=None)
    parser.add_argument("--norbs", type=int, default=None)
    parser.add_argument("--two-qubit-reduce", action="store_true")
    parser.add_argument("--adapt", action="store_true") # run statefull adapt
    parser.add_argument("--aer", action="store_true") # run with aer
    parser.add_argument("--sv_estimator", action="store_true")
    parser.add_argument("--braket", action="store_true") # run on braket
    parser.add_argument("--numpy", action="store_true")
    parser.add_argument("--stateless", action="store_true") # run just VQE
    parser.add_argument("--hw", action="store_true") # run on qiskit hw
    parser.add_argument("--local", action="store_true") # run on braket local
    parser.add_argument("--sv1", action="store_true") # run on braket sv1
    parser.add_argument("--aria1", action="store_true") # run on braket aria 1
    args = parser.parse_args()

    if args.nalpha is None or args.nbeta is None or args.norbs is None:
        raise ValueError("Missing argument!")

    num_alpha, num_beta = args.nalpha, args.nbeta
    num_orbs = args.norbs

    if args.two_qubit_reduce:
        mapper = ParityMapper(num_particles=(num_alpha, num_beta))
    else:
        mapper = ParityMapper()

    initial_state = HartreeFock(
        num_orbs,
        (num_alpha, num_beta),
        mapper,
    )
    ansatz = UCC(
        num_orbs,
        (num_alpha, num_beta),
        "sd",
        mapper,
        # generalized=True,
        # preserve_spin=False,
        initial_state=initial_state,
    )

    def _no_fail(*args, **kwargs):
        return True

    ansatz._check_ucc_configuration = _no_fail

    if args.adapt:
        operator_pool = []
        for op in ansatz.operators:
            for pauli, coeff in zip(op.paulis, op.coeffs):
                if sum(pauli.x & pauli.z) % 2 == 0:
                    continue
                operator_pool.append(SparsePauliOp([pauli], coeffs=[coeff]))

        ansatz = EvolvedOperatorAnsatz(
            operators=operator_pool,
            initial_state=initial_state,
        )

    if args.aer:
        # Configure the Aer simulator with the desired number of shots
        logger.info("=== AER backend activated with 100 shots ===")
        estimator = AerEstimator(run_options={"shots":100})
        backend_name = "AER"
        shots = 100
    else:
        if args.sv_estimator:
            logger.info("=== StatevectorEstimator backend activated with 100 shots ===")
            estimator = StatevectorEstimator()
            backend_name = "Qiskit Statevector"
        else:
            logger.info("=== Estimator backend activated with 100 shots ===")
            backend_name = "Qiskit Estimator"
            estimator = Estimator()

    if args.braket:
        if args.local:
            # Configure local backend with desired shots
            logger.info("=== Amazon Braket backend activated ===")
            backend = BraketLocalBackend()
            logger.info("Using Braket Local Simulator backend")
            estimator = BackendEstimator(backend=backend, options={"shots":1000})
            shots = 1000
            backend_name = "Braket Local"
            logger.info(f"Configured estimator with 1000 shots")

        if args.sv1:
            # Configure sv1 backend with desired shots
            logger.info("=== Amazon Braket backend activated ===")
            provider = BraketProvider()

            online_simulators = provider.backends(statuses=["ONLINE"])

            logger.info("Available backends: %s", [backend.name for backend in online_simulators])

            sv1_backends = [b for b in online_simulators if b.name == "SV1"]

            if not sv1_backends:
                logger.error("SV1 backend not found. Available backends: %s",
                            [b.name for b in online_simulators])
                raise ValueError("SV1 backend not available")

            backend = sv1_backends[0]
            logger.info("Using Braket SV1 Simulator backend")
            estimator = BackendEstimator(backend=backend, options={"shots":1000})
            shots = 1000
            backend_name = "Braket SV1"
            logger.info(f"Configured estimator with 1000 shots")
        if args.aria1:
            # Configure aria1 backend with desired shots
            logger.info("=== Amazon Braket backend activated ===")
            provider = BraketProvider()

            online_simulators = provider.backends(statuses=["ONLINE"])

            logger.info("Available backends: %s", [backend.name for backend in online_simulators])

            aria1_backends = [b for b in online_simulators if b.name == "Aria 1"]

            if not aria1_backends:
                logger.error("Aria 1 backend not found. Available backends: %s",
                            [b.name for b in online_simulators])
                raise ValueError("Aria 1 backend not available")

            backend = aria1_backends[0]

            logger.info("Using IONQ aria 1 backend")
            estimator = BackendEstimator(backend=backend, options={"shots":1000})
            shots = 1000
            backend_name = "Braket IONQ Aria 1"
            logger.info(f"Configured estimator with 1000 shots")
            pass


    if args.hw:
        # connect to real hw

        # Save an IBM Quantum account and set it as your default account.
        #QiskitRuntimeService.save_account(
        #    channel="ibm_quantum",
        #    token="",
        #    set_as_default=True,
        #    # Use `overwrite=True` if you're updating your token.
        #    overwrite=True,
        #)

        service = QiskitRuntimeService()
        backend = service.least_busy(operational=True, simulator=False, min_num_qubits=127)
        logger.info(f"Running on IBM hw {backend.name}")
        estimator = BackendEstimator(backend=backend, options={"shots":100})
        shots = 100
        backend_name = "Qiskit HW"


    def callback(nfev, parameters, energy, stepsize):
        logger.info(f"Iteration {nfev}: Energy = {energy:.6f}")
        return False

    # Try using SPSA optimizer
    optimizer = SPSA(
        maxiter=1000,
        learning_rate=0.005,
        perturbation=0.05,
        last_avg=1
    )


    # Use random initial parameters
    initial_point = np.random.rand(ansatz.num_parameters)

    if args.stateless:
        solver = VQE(
            estimator,
            ansatz,
            optimizer,
            callback=callback,
            initial_point=initial_point
        )
    else:
        solver = StatefulVQE(
            estimator,
            ansatz,
            optimizer,
            callback=callback,
            initial_point=initial_point
        )

    if args.adapt:
        class CustomAdaptVQE(StatefulAdaptVQE):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.previous_energies = []
                self.convergence_window = 3
                self.convergence_threshold = 1e-6

            def solve(self, problem):
                result = super().solve(problem)
                
                self.previous_energies.append(result.total_energies[-1])
                if len(self.previous_energies) > self.convergence_window:
                    self.previous_energies.pop(0)
                
                if len(self.previous_energies) == self.convergence_window:
                    energy_range = max(self.previous_energies) - min(self.previous_energies)
                    if energy_range < self.convergence_threshold:
                        logger.info("ADAPT-VQE Convergence achieved!")
                        self._converged = True
                
                return result

        solver = CustomAdaptVQE(
            solver,
            eigenvalue_threshold=1e-6,
            gradient_threshold=1e-4,
            max_iterations=20,
        )

    if args.numpy:
        solver = NumPyMinimumEigensolver()

    algo = GroundStateEigensolver(mapper, solver)

    logger.info(
        "Starting CP2KIntegration"
        )
    integ = CP2KIntegration(algo)
    integ.connect_to_socket(HOST, PORT, UNIX)
    integ.run()
    problem = integ.construct_problem()

    def my_generator(num_spatial_orbitals, num_particles):
        singles = generate_fermionic_excitations(
            1, num_spatial_orbitals, num_particles, preserve_spin=False
        )
        doubles = []
        # doubles = generate_fermionic_excitations(
        #     2, num_spatial_orbitals, num_particles, preserve_spin=False
        # )
        return singles + doubles

    if isinstance(integ.algo.solver, StatefulAdaptVQE):
        algo = GroundStateEigensolver(integ.algo.qubit_mapper, integ.algo.solver.solver)
    logger.info(
        "Creating QEOM"
        )

    qeom = QEOM(
        algo,
        estimator,
        excitations=my_generator,
        aux_eval_rules=EvaluationRule.ALL,
        tol=1e-6
    )

    logger.info(
        "Removing the ElectronicDensity property before starting QEOM"
    )
    problem.properties.electronic_density = None

    excited_state_result = qeom.solve(problem)

    # Print clear separation for results
    summary = f"""
{'='*80}
                         QUANTUM CALCULATION RESULTS
{'='*80}

CONFIGURATION:
-------------
Backend: { backend_name}
Number of alpha electrons: {num_alpha}
Number of beta electrons: {num_beta}
Number of orbitals: {num_orbs}
Number of shots: {shots}

CALCULATION RESULTS:
------------------
Ground State Energy: {excited_state_result.groundstate_energy if hasattr(excited_state_result, 'groundstate_energy') else 'N/A'}

Excitation Energies:
{excited_state_result.raw_result.excitation_energies}

Transition Amplitudes:
"""
    for key, values in excited_state_result.raw_result.transition_amplitudes.items():
        summary += f"\nState {key}:\n"
        for name, val in values.items():
            summary += f"  {name}: {val[0]:.6f}\n"
    summary += f"""
{'='*80}
                         CALCULATION COMPLETED
{'='*80}
Total Iterations: {solver._eval_count if hasattr(solver, '_eval_count') else 'N/A'}
Final Energy: {excited_state_result.groundstate_energy if hasattr(excited_state_result, 'groundstate_energy') else 'N/A'}
Convergence Status: {'Converged' if hasattr(solver, '_converged') and solver._converged else 'Completed'}
{'='*80}
"""

    # Print to both console and log file
    print(summary)
    logger.info(summary)

    # Save results to a JSON file
    results_dict = {
        "configuration": {
            "backend": backend_name,
            "method": "ADAPT-VQE" if args.adapt else "VQE",
            "num_alpha": num_alpha,
            "num_beta": num_beta,
            "num_orbs": num_orbs,
            "num_shots": shots
        },
        "results": {
            "ground_state_energy": float(excited_state_result.groundstate_energy) if hasattr(excited_state_result, 'groundstate_energy') else None,
            "excitation_energies": excited_state_result.raw_result.excitation_energies.tolist(),
            "transition_amplitudes": {
                str(key): {str(name): float(val[0]) for name, val in values.items()}
                for key, values in excited_state_result.raw_result.transition_amplitudes.items()
            }
        }
    }

    with open('quantum_calculation_results.json', 'w') as f:
        json.dump(results_dict, f, indent=4)

    logger.info("Results have been saved to 'quantum_calculation_results.json'")

class CP2KIntegration:
    def __init__(self, algo):
        self.algo = algo
        self.socket = None

    def connect_to_socket(self, host, port, unix):
        try:
            if unix:
                self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.socket.connect(host)
            else:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((host, port))
            logger.info("Connected to socket successfully.")
        except socket.error as e:
            logger.error(f"Socket connection error: {e}")
            self.socket = None

    def run(self):
        if not self.socket:
            logger.error("No socket connection available.")
            return

        try:
            # Ensure the socket is connected before sending data
            self.socket.send(self.Messages.HAVEDATA.value)
        except BrokenPipeError:
            logger.error("Broken pipe error: Unable to send data. The connection may have been closed.")
            self.reconnect()

    def reconnect(self):
        logger.info("Attempting to reconnect to the socket...")
        time.sleep(5)  # Wait before attempting to reconnect
        self.connect_to_socket(HOST, PORT, UNIX)
```

## Key Components

1. **Imports**: The script imports necessary libraries from Qiskit, Braket, and CP2K integration modules.
2. **Configuration**: Sets up logging and numpy print options.
3. **VQE Implementation**: Implements the VQE algorithm with SPSA optimizer.
4. **Integration**: Handles CP2K integration and quantum calculations.