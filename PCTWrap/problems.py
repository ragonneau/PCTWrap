"""Wrapper for pycutest.CUTEstProblem

It records the objective function evaluations together with a measure of the
constraints evaluations.
.
"""
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, NonlinearConstraint


class PCTProblem:
    """Wrapper for pycutest.CUTEstProblem

    It records the objective function evaluations together with merit
    evaluations.
    """

    def __init__(self, problem):
        """Initialize the problem wrapper.

        :param problem: Instance of pycutest.CUTEstProblem.
        """
        self._problem = problem
        self.name = self._problem.name
        self.n = self._problem.n
        self.x0 = self._problem.x0
        self.objectives = []
        self.residuals = []
        self.bounds, self.constraints = self.get_constraints()

    def clear_memory(self):
        """Clear from the memory of the class the objective function and merit
        evaluations.
        """
        self.objectives = []
        self.residuals = []

    def get_constraints(self):
        """Extract the constraint from the problem.

        In order to extract the linear constraint, it performs an extra
        constraint function evaluation.

        :return: The bounds and the constraints of the problems.
        """
        # Extract the bounds. PyCUTEst set a bound to (+/-)1e20 when the
        # direction should be considered unconstrained.
        if np.less_equal(self._problem.bl, -1e20).all() and \
                np.greater_equal(self._problem.bu, 1e20).all():
            bounds = None
        else:
            bounds = Bounds(self._problem.bl, self._problem.bu)

        # Extract the linear constraints.
        if self._problem.is_linear_cons.any():
            bl, Al = self._problem.cons(np.zeros(self.n), gradient=True)
            lbl = np.full(self._problem.m, -np.inf)
            Al = Al[self._problem.is_linear_cons, ...]
            ubl = -bl[self._problem.is_linear_cons]
            lbl[self._problem.is_eq_cons] = -bl[self._problem.is_eq_cons]
            lbl = lbl[self._problem.is_linear_cons]
        else:
            Al = np.array([[]])
            lbl, ubl = np.array([]), np.array([])

        # Extract the nonlinear constraints.
        ctr = [LinearConstraint(Al, lbl, ubl)]
        if not self._problem.is_linear_cons.all():
            is_nl = np.logical_not(self._problem.is_linear_cons)
            lbn = np.full(self._problem.m, -np.inf)
            lbn[self._problem.is_eq_cons] = 0
            lbn = lbn[is_nl]
            ubn = np.zeros_like(lbn)
            ctr.append(
                NonlinearConstraint(lambda x: self.cons(x)[is_nl], lbn, ubn))

        return bounds, ctr

    def obj(self, x, gradient=False, norm_linear_violation=False):
        """ Evaluate the objective function and record it, together with the
        merit value.

        :param x: Point of evaluation.
        :param gradient: Whether the gradient should be evaluated.
        :param norm_linear_violation: Whether the residuals associated with
            linear constraint should be normalized.
        :return: The objective function value, and possibly the gradient.
        """
        if gradient:
            f, g = self._problem.obj(x, gradient)
            self.objectives.append(f)
            g = np.nan_to_num(g)
        else:
            f = self._problem.obj(x)
            self.objectives.append(f)
        if np.isnan(f):
            f = np.inf

        # Compute the constraint violation. As of now, a new evaluation of the
        # constraint function is performed for each residual calculation, this
        # should be improved.
        if self._problem.m > 0:
            vlt = self.ctr_violations(self.cons(x), norm_linear_violation)
            if vlt > 1e-2:
                self.residuals.append(np.inf)
            else:
                self.residuals.append(f + 1e3 * vlt)
        else:
            self.residuals.append(f)

        if gradient:
            return f, g
        else:
            return f

    def cons(self, x, index=None, gradient=False):
        """Evaluate the constraint function.

        :param x: Point of evaluation.
        :param index: Index of the constraint to evaluate. If set to None, all
            the constraints are evaluated.
        :param gradient: Whether the gradient should be evaluated.
        :return: The constraint value, and possibly the gradient.
        """
        return self._problem.cons(x, index, gradient)

    def ctr_violations(self, cons, norm_linear_violation):
        """Measure the constraint violation of the given constraint evaluation.

        :param cons: Evaluation of the constraint function
        :param norm_linear_violation: Whether the residuals associated with
            linear constraint should be normalized.
        :return: The measure of the constraint violation.
        """
        is_nl = np.logical_not(self._problem.is_linear_cons)
        is_l_eq = np.logical_and(self._problem.is_linear_cons,
                                 self._problem.is_eq_cons)
        is_l_ineq = np.logical_and(np.logical_not(is_l_eq),
                                   self._problem.is_linear_cons)
        is_nl_eq = np.logical_and(is_nl, self._problem.is_eq_cons)
        is_nl_ineq = np.logical_and(np.logical_not(is_nl_eq), is_nl)
        vlt = np.max(np.abs(cons[is_l_eq]), initial=0)
        vlt = np.max((vlt, np.max(cons[is_l_ineq], initial=0)))
        if norm_linear_violation:
            # The residual term associated with the linear constraints is
            # normalized with the right-hand side vector of the linear
            # constraints.
            vlt /= np.max(
                (1, np.max(np.abs(self.constraints[0].ub), initial=0)))
        vlt = np.max((vlt, np.max(np.abs(cons[is_nl_eq]), initial=0)))
        vlt = np.max((vlt, np.max(cons[is_nl_ineq], initial=0)))

        return vlt
