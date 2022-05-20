def CvC(theta_T):
    # heat capacity at constant volume, T and theta in K
    f=3*RGas*(4*debye3(theta_T)-theta_T*3/(np.exp(theta_T)-1))
    return f


def debye3(x, maxdeg=7): # truncated to save computation time
    """
    %DEBYE3 ThirdF order Debye function.
    %   Y = DEBYE3(X) returns the third order Debye function, evaluated at X.
    %   X is a scalar.  For positive X, this is defined as
    %
    %      (3/x^3) * integral from 0 to x of (t^3/(exp(t)-1)) dt
    
    %   Based on the FORTRAN implementation of this function available in the
    %   MISCFUN Package written by Alan MacLead, available as TOMS Algorithm 757
    %   in ACM Transactions of Mathematical Software (1996), 22(3):288-301.
    """

    adeb3=[2.70773706832744094526,
           0.34006813521109175100,
           -0.1294515018444086863e-1,
           0.79637553801738164e-3,
           -0.5463600095908238e-4,
           0.392430195988049e-5,
           -0.28940328235386e-6,
           0.2173176139625e-7,
           -0.165420999498e-8,
           0.12727961892e-9,
           -0.987963459e-11,
           0.77250740e-12,
           -0.6077972e-13,
           0.480759e-14,
           -0.38204e-15,
           0.3048e-16,
           -0.244e-17,
           0.20e-18,
           -0.2e-19]

    if x < 0: 
        print('error in debye3: negative input value')
        return 0
    elif (x < 3.e-8): 
        print('low input value in debye3: check input value')
        D3 = ((x - 7.5 ) * x + 20.0)/20.0
    elif x <= 4:
        # routine only accurate within these limits
        # but should be OK for typical x values in our
        # models

        t = ((x**2/8)-0.5)-0.5
        D3 = cheval(adeb3[0:maxdeg],t)-0.375*x
    else:
        print('error in debye3: input value should be smaller than 4');
        return 0

    return D3

def cheval(a, t):
    """
    CHEVAL evaluates a Chebyshev series.
    modified by MD for Matlab 
    
      Discussion:
    
        This function evaluates a Chebyshev series, using the
        Clenshaw method with Reinsch modification, as analysed
        in the paper by Oliver.
    
      Author:
    
        Allan McLeod,
        Department of Mathematics and Statistics,
        Paisley University, High Street, Paisley, Scotland, PA12BE
        macl_ms0@paisley.ac.uk
    
      Reference:
    
        Allan McLeod,
        Algorithm 757, MISCFUN: A software package to compute uncommon
          special functions,
        ACM Transactions on Mathematical Software,
        Volume 22, Number 3, September 1996, pages 288-301.
    
        J Oliver,
        An error analysis of the modified Clenshaw method for
        evaluating Chebyshev and Fourier series,
        Journal of the IMA,
        Volume 20, 1977, pages 379-391.
    
      Parameters:
    
        Input, A(1:N), the coefficients of the Chebyshev series.
    
        Input,  T, the value at which the series is
        to be evaluated.
    
        Output, CHEV, the value of the Chebyshev series at T.
    
    """
    n=len(a)-1
    u1 = 0.0
    #  T <= -0.6, Reinsch modification.
    # -0.6 < T < 0.6, Standard Clenshaw method.
    #  T > 0.6 Reinsch
    if t <= -0.6 or t>=0.6:
        d1 = 0.0
        tt = (t+0.5) + 0.5
        tt = tt+tt
        for i in range(n,-1,-1):
            d2 = d1
            u2 = u1
            d1 = tt * u2 + a[i] - d2
            u1 = d1 - u2
        chev = 0.5*( d1-d2 )


    else:
        u0 = 0.0
        tt = t + t
        for i in range(n,-1,-1):
            u2 = u1
            u1 = u0
            u0 = tt * u1 + a[i] - u2

        chev = 0.5*( u0 - u2 ) 

    return chev

def Eth(T,theta):
    #internal thermal energy (without not relevant term linear in theta),
    # T and theta in K
    RGas=8.3144621
    f=3.*RGas*(3*theta/8 + T*debye3(theta/T))
    
    return f

def gammaC(eta,gamma0,q0):
    # Grueneisen parameter
    # eta=V0/V
    return gamma0*eta**(-q0)

def thetaC(eta,theta0,gamma0,q0):
    # Debye temperature, eta=V0/V
    return theta0*np.exp((gamma0-gammaC(eta,gamma0,q0))/q0)

