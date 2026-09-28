"""Unit tests for the Newton solver (shootp.mynewtonSys) and the RK4/
Simpson integrators in src/solver.py, isolated from the Mercury physics.

mynewtonSys looks up its Jacobian function by NAME via
`eval(Jfun)(x,varargin)`, evaluated in shootp.py's own module
namespace -- so a toy Jfun must be injected as an attribute of the
imported shootp module (setattr), not passed as a Python callable, to
exercise the solver's iteration/convergence logic without running the
real (slow) Mercury shooting function.
"""
import numpy as np
import pytest

pytestmark = pytest.mark.unit

from conftest import import_src


@pytest.fixture
def shootp(sys_argv_p):
    return import_src("shootp")


@pytest.fixture
def solver(sys_argv_p):
    return import_src("solver")


def test_newton_solves_toy_quadratic_root(shootp):
    # f(x) = x^2 - a, root at x = sqrt(a). J = 2x (scalar "matrix").
    a = 9.0

    def toy_jac(x, varargin):
        J = np.array([[2.0 * x[0]]])
        f = np.array([x[0] ** 2 - a])
        return J, f

    shootp.toy_jac = toy_jac
    x0 = [5.0]
    root = shootp.mynewtonSys("toy_jac", x0, [], xtol=1e-10, ftol=1e-10, maxit=50)
    assert root[0] == pytest.approx(3.0, abs=1e-6)


def test_newton_solves_toy_linear_system(shootp):
    # 2x2 linear system with a known solution: A x = b.
    A = np.array([[2.0, 1.0], [1.0, 3.0]])
    b = np.array([5.0, 10.0])
    x_true = np.linalg.solve(A, b)

    def toy_linear(x, varargin):
        f = A.dot(np.array(x)) - b
        return A, f

    shootp.toy_linear = toy_linear
    root = shootp.mynewtonSys("toy_linear", [0.0, 0.0], [], xtol=1e-10, ftol=1e-10, maxit=5)
    # A linear system is solved in exactly ONE Newton step from any x0
    # (the Jacobian is constant and exact) -- assert convergence to the
    # analytic solution.
    assert np.allclose(root, x_true, atol=1e-8)


def test_newton_raises_systemexit_on_singular_jacobian(shootp):
    # A Jacobian with zero determinant must stop the solve loudly
    # (sys.exit), never silently return a bogus root.
    def toy_singular(x, varargin):
        J = np.array([[1.0, 1.0], [1.0, 1.0]])  # singular
        f = np.array([1.0, 1.0])
        return J, f

    shootp.toy_singular = toy_singular
    with pytest.raises(SystemExit):
        shootp.mynewtonSys("toy_singular", [0.0, 0.0], [], xtol=1e-10, ftol=1e-10, maxit=5)


# ---------------------------------------------------------------------
# simpsonDat: Composite Simpson's rule -- exact for cubics, and a known
# hand-computable case (integral of x^2 from 0 to 1 is 1/3).
# ---------------------------------------------------------------------
def test_simpson_integrates_x_squared(solver):
    x = np.linspace(0.0, 1.0, 101)  # odd number of points required
    f = x ** 2
    assert solver.simpsonDat(x, f) == pytest.approx(1.0 / 3.0, rel=1e-6)


def test_simpson_integrates_constant_exactly(solver):
    x = np.linspace(0.0, 5.0, 51)
    f = np.full_like(x, 3.0)
    assert solver.simpsonDat(x, f) == pytest.approx(15.0, rel=1e-12)
