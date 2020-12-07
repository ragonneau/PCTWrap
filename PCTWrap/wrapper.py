import logging
import os
import platform
import re
import subprocess
from pathlib import Path

import numpy as np

from .problems import PCTProblem


class PCTWrapper:
    """Wrapper for the PyCUTEst package"""

    def __init__(self, cutest_root_path=None, cache_path=None):
        """Initialize the PyCUTEst wrapper, including the environment variables
        required by CUTEst. It is assumed that CUTEst has been installed using
        Homebrew if you are using MacOS.

        :param cutest_root_path: Path to the root folder of the CUTEst library.
            By default, it is set to '/opt/cutest' for Linux and
            '/usr/local/opt' for MacOS.
        :param cache_path: Path to the root folder of the PyCUTEst cache. By
            default, it is set to the working directory.
        """
        if platform.system() == 'Linux':
            os.environ['MYARCH'] = 'pc64.lnx.gfo'
        elif platform.system() == 'Darwin':
            os.environ['MYARCH'] = 'mac64.osx.gfo'
        else:
            # The current OS is likely Windows...
            raise OSError('Supported only on Linux and MacOS only.')

        if cutest_root_path is None:
            if platform.system() == 'Linux':
                cutest_root_path = '/opt/cutest'
            else:
                cutest_root_path = '/usr/local/opt'
        self.cutest_root_path = Path(cutest_root_path).resolve(strict=True)
        self.cutest_path = self.cutest_root_path / 'cutest'
        self.archdefs_path = self.cutest_root_path / 'archdefs'
        self.sifdecode_path = self.cutest_root_path / 'sifdecode'
        self.mastsif_path = self.cutest_root_path / 'mastsif'
        if platform.system() == 'Darwin':
            self.cutest_path = self.cutest_path / 'libexec'
            self.archdefs_path = self.archdefs_path / 'libexec'
            self.sifdecode_path = self.sifdecode_path / 'libexec'
            self.mastsif_path = self.mastsif_path / 'share' / 'mastsif'

        if cache_path is None:
            self.cache_path = Path.cwd()
        else:
            self.cache_path = Path(cache_path).resolve(strict=True)

        os.environ['CUTEST'] = str(self.cutest_path)
        os.environ['ARCHDEFS'] = str(self.archdefs_path)
        os.environ['SIFDECODE'] = str(self.sifdecode_path)
        os.environ['MASTSIF'] = str(self.mastsif_path)
        os.environ['PYCUTEST_CACHE'] = str(self.cache_path)

        self.problems = []
        self.base_dir = Path('.').resolve(strict=True)

        # The package PyCUTEst is loaded locally because the environment
        # variables must be set beforehand, but it should be reachable globally.
        global pycutest
        import pycutest

    @staticmethod
    def clear_all_cache():
        """Clear all the PyCUTEst cache."""
        problems = pycutest.all_cached_problems()
        for problem in problems:
            pycutest.clear_cache(problem)

    @staticmethod
    def get_sif_params(problem, parameter='N'):
        """List available values for the given SIF parameter of the given
        problem. If [] is returned, then no settable value has been found.

        :param problem: PyCUTEst problem.
        :param parameter: SIF parameter to investigate.
        :return: Ordered array (increasingly) of the possible value.
        """
        # Execute the `sifdecode` command shell to get all the parameters in a
        # txt format, which will be next processed.
        sp = subprocess.Popen(
            [pycutest.get_sifdecoder_path(), '-show', problem],
            universal_newlines=True, stdout=subprocess.PIPE)
        sif_stdout = sp.stdout.read()

        # We need to wait for the subprocess to finish before continuing,
        # otherwise, it might get garbage-collected before its actual end,
        # resulting in a crash of the interpreter.
        sp.wait()

        # The standard output contains comments and actual information, which
        # should be decoded. The parameters are given as a `key=value` tuple.
        sif_pattern = re.compile('^(?P<param>[A-Z]+)=(?P<value>\d+)')
        sif_values = []  # returned values for the given parameter
        for l_stdout in sif_stdout.split('\n'):
            sif_match = sif_pattern.match(l_stdout)
            if sif_match and sif_match.group('param') == parameter:
                # The current line of the standard output match the provided SIF
                # parameter. The conversion to integer cannot fail since the
                # line match the pattern described in `sif_pattern`.
                sif_values.append(int(sif_match.group('value')))

        return np.sort(sif_values)

    def import_problems(self, n_max, objective='CLQSO', constraints='U',
                        cutest=None, path='.', some_linear_equality=False):
        """Load the CUTEst problems matching the requirements. Not that some
        requirements ask for the problem to be load before being rejected, such
        as `some_equality=True`.

        :param n_max: Upper bound on the dimension of the problems.
        :param objective: String (substring of 'NCLQSO') specifying the type of
            the objective function. The possible values for the objective
            function are
            - 'N' not to be defined,
            - 'C' to be constant,
            - 'L' to be linear,
            - 'Q' to be quadratic,
            - 'S' to be a sum of squares, and
            - 'O' to be none of the above.
        :param constraints: String (substring of 'UXBNLQO') specifying the type
            of the constraints. The possible values for the constraints are
            - 'U' not to be defined (unconstrained),
            - 'X' to be fixed variables,
            - 'B' to be bounds on the variables,
            - 'N' to represent the adjacency matrix of a (linear) network,
            - 'L' to be linear,
            - 'Q' to be quadratic, and
            - 'O' to be more general than any of the above alone.
        :param cutest: List of problems to load or name of the file where the
            problems are listed. If it is set, the parameters objective` and
            `constraints` are not considered.
        :param path: Path to the file where the problems are listed. It is used
            only if `cutest` is set to a string.
        :param some_linear_equality: Whether the problem should admits at least
            one linear equality constraint.
        """
        if cutest is None:
            logging.info('CUTEST problem list provided.')
            cutest = pycutest.find_problems(
                objective, constraints, n=[1, n_max])
        elif isinstance(cutest, str):
            path = Path(path).resolve(strict=True)
            logging.info('Attempt to read %s' % str(path / cutest))
            with open(path / cutest, 'r') as fo:
                cutest = [c.strip(os.linesep) for c in fo.readlines()]
        n_cutest = len(cutest)

        # Attempt to load the selected CUTEst problems.
        problems = []
        for i_prob, prob in enumerate(sorted(cutest)):
            logging.info('Import %d/%d: %s' % (i_prob + 1, n_cutest, prob))
            try:
                if pycutest.problem_properties(prob)['n'] is None:
                    # The dimensions of the problem are not fixed, and can be
                    # higher than n_max.
                    dimensions = self.get_sif_params(prob)

                    if dimensions.size > 0 and dimensions[0] <= n_max:
                        # The problem admits at least one possible value for the
                        # SIF parameter 'N' below n_max. We select the biggest
                        # one below n_max.
                        py_prob = pycutest.import_problem(prob, sifParams={
                            'N': np.max(dimensions[dimensions <= n_max]),
                        })

                        if py_prob.n > n_max:
                            # It seems that PyCUTEst sometimes return problems
                            # with incorrect dimension. We believe that it comes
                            # from the requirements of the CUTEst problems for
                            # the other SIF parameters. The exception will be
                            # caught in the `except` statement below.
                            raise RuntimeError()
                    else:
                        # None of the available SIF parameters for the given
                        # problem match the requirements. The exception will be
                        # caught in the `except` statement below.
                        raise RuntimeError()
                else:
                    # The problem has a fixed dimension below n_max.
                    py_prob = pycutest.import_problem(prob)

                # The problem is now loaded, and we can check the final
                # requirements on its structure.
                if some_linear_equality and \
                        not np.logical_and(py_prob.is_linear_cons,
                                           py_prob.is_eq_cons).any():
                    logging.info('Failed: %s contains no linear equality '
                                 'constraints.' % prob)
                else:
                    problems.append(PCTProblem(py_prob))
                    logging.info('Success: %s (n=%d, m=%d) has been loaded' %
                                 (prob, py_prob.n, py_prob.m))
            except RuntimeError:
                logging.info('Failed: Invalid dimensions of %s' % prob)
            except (AttributeError, ModuleNotFoundError):
                logging.info('Failed: PyCUTEst failed to load %s' % prob)

        self.problems = problems

    def get_problem_names(self):
        """Get a list of the loaded problem names.

        :return: A list of the loaded problem names.
        """
        return [p.name for p in self.problems]

    def save_problems(self, filename, path='.'):
        """Dump the list of the loaded problem into a file.

        :param filename: Name of the file to record the problem names.
        :param path: Path to the file.
        """
        if path == '.':
            path = self.base_dir
        path = Path(path).resolve(strict=True)
        logging.info('Saving problems into %s' % str(path / filename))
        with open(path / filename, 'w') as fo:
            fo.write(os.linesep.join(self.get_problem_names()))

    def __str__(self):
        """Print an instance of PCTWrapper.

        :return: The string associated with the list of all problems.
        """
        return str(self.get_problem_names())
