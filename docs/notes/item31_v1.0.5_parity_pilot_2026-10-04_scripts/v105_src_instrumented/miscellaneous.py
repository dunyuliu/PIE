# Functions not used and spun off from libCore
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

for lel in ['sulfur','silicon']:
    #font = {'family':'normal','size':16}
    #matplotlib.rc('font', **font)

    data1 = np.load('./results/genova/'+lel+'.npy',allow_pickle=True).item()
    data1a = np.load('./results/genova/'+lel+'-1sigma.npy',allow_pickle=True).item()
    data1b = np.load('./results/genova/'+lel+'+1sigma.npy',allow_pickle=True).item()
    data2 = np.load('./results/margot/'+lel+'.npy',allow_pickle=True).item()
    data2a = np.load('./results/margot/'+lel+'-1sigma.npy',allow_pickle=True).item()
    data2b = np.load('./results/margot/'+lel+'+1sigma.npy',allow_pickle=True).item()
    #data3 = np.load('./results/genova/'+lel+'_margot_cmc.npy',allow_pickle=True).item()
            
    fig,ax = plt.subplots(2,2,figsize=(15,7))
    fig.subplots_adjust(wspace=0.35)

    """
    ax[0,0].plot(np.array(data['rs'])/1000,np.array(data['is']*100,lw=3,color='blue')
    ax[0,0].plot(np.array(data2['rs'])/1000,np.array(data2['is']*100,lw=3,color='red')
    ax[0,0].plot(np.array(data3['rs'])/1000,np.array(data3['is']*100,lw=3,color='black')
    ax[0,0].set_xlabel('ICB Radius [km]')
    ax[0,0].set_ylabel('ICB Si [wt.%]')
    """
    
    ax[0,0].plot(np.array(data1['rs'])/1000,np.array(data1['cr'])/1000,lw=3,color='blue')
    ax[0,0].plot(np.array(data1a['rs'])/1000,np.array(data1a['cr'])/1000,lw=2,ls='--',color='blue')
    ax[0,0].plot(np.array(data1b['rs'])/1000,np.array(data1b['cr'])/1000,lw=2,ls='--',color='blue')
    ax[0,0].plot(np.array(data2['rs'])/1000,np.array(data2['cr'])/1000,lw=3,color='red')
    ax[0,0].plot(np.array(data2a['rs'])/1000,np.array(data2a['cr'])/1000,lw=2,ls='--',color='red')
    ax[0,0].plot(np.array(data2b['rs'])/1000,np.array(data2b['cr'])/1000,lw=2,ls='--',color='red')
    #ax[0,0].plot(np.array(data3['rs'])/1000,np.array(data3['cr'])/1000,lw=3,ls='--',color='goldenrod')
    #ax[0,0].fill_between(np.array(data1a['rs'])[0:121]/1000,np.array(data1a['cr'])[0:121]/1000,np.array(data1b['cr'])[0:121]/1000,color='lightblue')
    #ax[0,0].fill_between(np.array(data2a['rs'])[0:110]/1000,np.array(data2a['cr'])[0:110]/1000,2050,color='lightsalmon')
    
    ax[0,0].set_xlabel('ICB Radius [km]')
    ax[0,0].set_ylabel('CMB Radius [km]')
    ax[0,0].grid()
    ax[0,0].set_xlim(0, 1400)
    ax[0,0].set_ylim(1925, 2050)
    #ax[0,0].set_ylim(1950, 1980)
    
    ax[1,0].plot(np.array(data1['rs'])/1000,np.array(data1['cs'])*100,lw=3,color='blue')
    ax[1,0].plot(np.array(data1a['rs'])/1000,np.array(data1a['cs'])*100,lw=2,ls='--',color='blue')
    ax[1,0].plot(np.array(data1b['rs'])/1000,np.array(data1b['cs'])*100,lw=2,ls='--',color='blue')
    ax[1,0].plot(np.array(data2['rs'])/1000,np.array(data2['cs'])*100,lw=3,color='red')
    ax[1,0].plot(np.array(data2a['rs'])/1000,np.array(data2a['cs'])*100,lw=2,ls='--',color='red')
    ax[1,0].plot(np.array(data2b['rs'])/1000,np.array(data2b['cs'])*100,lw=2,ls='--',color='red')
    #ax[1,0].plot(np.array(data3['rs'])/1000,np.array(data3['cs'])*100,lw=3,ls='--',color='goldenrod')
    #ax[1,0].fill_between(np.array(data1s['rs'])[0:121]/1000,np.array(data1s['cs'])[0:121]*100,np.array(data2s['cs'])[0:121]*100,color='lightgray')
    ax[1,0].set_xlabel('ICB Radius [km]')
    ax[1,0].set_ylabel('Mean Lq. Core '+lel.replace('s','S')+' [wt.%]')
    ax[1,0].grid()
    ax[1,0].set_xlim(0, 1400)
    ax[1,0].set_ylim(0, 15)
    
    ax[0,1].plot(np.array(data1['rs'])/1000,np.array(data1['ct']),lw=3,color='blue')
    ax[0,1].plot(np.array(data2['rs'])/1000,np.array(data2['ct']),lw=3,color='red')
    #ax[0,1].plot(np.array(data3['rs'])/1000,np.array(data3['ct']),lw=2,color='goldenrod')
    ax[0,1].plot(np.array(data1a['rs'])/1000,np.array(data1a['ct']),lw=2,ls='--',color='blue')
    ax[0,1].plot(np.array(data1b['rs'])/1000,np.array(data1b['ct']),lw=2,ls='--',color='blue')
    ax[0,1].plot(np.array(data2a['rs'])/1000,np.array(data2a['ct']),lw=2,ls='--',color='red')
    ax[0,1].plot(np.array(data2b['rs'])/1000,np.array(data2b['ct']),lw=2,ls='--',color='red')
    ax[0,1].set_xlabel('ICB Radius [km]')
    ax[0,1].set_ylabel('CMB Temperature [K]')
    ax[0,1].grid()
    #ax[0,1].fill_between(np.array(data1s['rs'])[0:121]/1000,np.array(data1s['ct'])[0:121],np.array(data2s['ct'])[0:121],color='lightgray')
    ax[0,1].set_xlim(0, 1400)
    if lel == 'silicon': ax[0,1].set_ylim(1900, 2500)
    else: ax[0,1].set_ylim(1200, 2400)
    
    ax[1,1].plot(np.array(data1['rs'])/1000,np.array(data1['md']),lw=3,color='blue')
    ax[1,1].plot(np.array(data2['rs'])/1000,np.array(data2['md']),lw=3,color='red')
    #ax[1,1].plot(np.array(data3['rs'])/1000,np.array(data3['md']),lw=2,color='goldenrod')
    #ax[1,1].fill_between(np.array(data1s['rs'])[0:121]/1000,np.array(data1s['md'])[0:121],np.array(data2s['md'])[0:121],color='lightgray')
    ax[1,1].plot(np.array(data1a['rs'])/1000,np.array(data1a['md']),lw=2,ls='--',color='blue')
    ax[1,1].plot(np.array(data1b['rs'])/1000,np.array(data1b['md']),lw=2,ls='--',color='blue')
    ax[1,1].plot(np.array(data2a['rs'])/1000,np.array(data2a['md']),lw=2,ls='--',color='red')
    ax[1,1].plot(np.array(data2b['rs'])/1000,np.array(data2b['md']),lw=2,ls='--',color='red')
    ax[1,1].set_xlabel('ICB Radius [km]')
    ax[1,1].set_ylabel('Mantle Density [kg/m$^3$]')
    ax[1,1].grid()
    ax[1,1].set_xlim(0, 1400)
    ax[1,1].set_ylim(2800, 3450)

    #font = {'family':'normal','size':12}
    #matplotlib.rc('font', **font)
    colors = ["red", "blue"]
    texts = ["MoI = 0.346 (Margot et al. 2012)", "MoI = 0.333 (Genova et al. 2019)"]

    patches = [ mpatches.Patch(color=colors[i], label="{:s}".format(texts[i]) ) for i in range(len(texts)) ]
    plt.legend(handles=patches, 
              loc='lower center', 
              bbox_to_anchor=(0.5,-0.5),
              ncol=3)
    
    plt.tight_layout()
    plt.savefig('comparison_'+lel+'.pdf',dpi=300)
    plt.show()

    
    #fig,ax = plt.subplots(figsize=(20,4))

#plt.savefig('legend.pdf',dpi=300)
#plt.show()

print('done')


# REASSEMBLE DATA

for param in model_cases:
    root = './results/'+param['name']+'/'
    files = glob.glob(root+'*.h5')
    icb_sulfur = []
    core_sulfur = []
    cmb_radius = []
    cmb_temperature = []
    mantle_density = []
    rs = []
    if not files == []:
        files = sorted(files, key=lambda i: np.int(os.path.basename(i).replace('.0_data.h5','')))
    
    for f in files:
        df = pd.read_hdf(f,'misc') 
    
        icb_sulfur.append(df['chi_li_icb'].values[0])  
        core_sulfur.append(df['chi_liin'].values[0])
        cmb_radius.append(df['rcmb'].values[0])
        cmb_temperature.append(df['Tcmb'].values[0])
        mantle_density.append(df['rhom'].values[0])    
        rs.append(df['ricb'].values[0])
    
    
    data = {'is':icb_sulfur, 'cs':core_sulfur, 'cr':cmb_radius,
            'ct':cmb_temperature, 'md':mantle_density, 'rs':rs}

    np.save('./results/'+param['name']+'.npy',data)

    
    
    