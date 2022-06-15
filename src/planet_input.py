import coreEos as eos
from libCore import *
from scipy.constants import G

def planet(mod_type, mod_name, mod_li_el):
    fccFe=eos.eosAndersonGrueneisen(M0=MFe,p0=1.e-5,T0=298,V0=6.82,
                            alpha0=7.e-5,KT0=163.4,KTP0=5.38,
                            deltaT=5.5,kappa=1.4,GibbsE=eos.GibbsfccFe)        
        
    liquidFe=eos.eosAndersonGrueneisen(M0=MFe,p0=1E-5,T0=298,V0=6.88,
                               alpha0=9E-5,KT0=148,KTP0=5.8,deltaT=5.1,
                               kappa=0.56,GibbsE=eos.GibbsLiquidFe)

    liquidFeS=eos.eosAndersonGrueneisen(M0=MFeS,p0=1E-5,T0=1650,
                                V0=22.956500240757844,alpha0=11.9e-5,
                                KT0=17.01901122392699,
                                KTP0=5.92217679116356,
                                deltaT=5.9221767911635,kappa=1.4,
                                gamma0=1.3,q=0)

    liquidFeSi=eos.eosAndersonGrueneisen(M0=MFeSi,p0=1E-5,T0=1723,
                                 V0=16.5839,alpha0=17.6525e-5,KT0=69.0074,
                                 KTP0=7.76007,deltaT=4.07505,kappa=0.56,
                                 gamma0=1.61986,q=0)

    model_generic = {'rm':2439360.0,
         'GM':22031.86E+9,
         'c22':0.804151E-05,
         'CmC':0,
         'CMR2':0,
         'MFe':MFe,
         'MS':32.065,
         'MSi':28.08,
         'MFeS':MFeS,
         'MFeSi':(55.845+28.08),
         'lFe':liquidFe,
         'lFeS':liquidFeS,
         'lFeSi':liquidFeSi,
         'fccFe':fccFe,
         'liquidus':TmFeSSi,# Added by Tilio. Defined in libCore.py. 20220614.
         'li_el':'None',
         'name':'replace_me',
         'rhomean':'None',
          'rhocr':2974,
          'hcr':26e3,
          'rh':'None',
          'scale':'None',
          'v0':[0.8,1.0,0.8,0.7,0.05]} # initial guesses
          
    M = model_generic['GM']/G
    rm = model_generic['rm']
    hcr = model_generic['hcr']
    
    #Average density
    rhomean = 3*M/(4*np.pi*rm**3)
    model_generic['rhomean'] = rhomean
    model_generic['scale']= {'a':rm,'ga':M*G/rm**2,'P':rhomean*rm*M*G/rm**2,'T':1800}
    model_generic['rh'] = (rm-hcr)/rm # radius of crust-mantle boundary
    
    # Margot Fe-S-Si models
    if mod_type == 'p':
        if mod_name == 'margot' and mod_li_el == 'S+Si':
            h = model_generic.copy()
            h['CMR2'] = 0.346
            h['CmC'] = 0.148/h['CMR2']
            h['li_el'] = 'S+Si'
            h['name'] = 'margot/Fe-S-Si'
        elif mod_name == 'margot' and mod_li_el == 'S':
            h['CMR2'] = 0.346-0.014/20
            h['CmC'] =  0.431# 0.148/margot_fesi['CMR2']
            h['li_el'] = 'S'
            h['name'] = 'margot/Fe-S'
        elif mod_name == 'margot' and mod_li_el == 'Si':
            h['CMR2'] = 0.346-0.014/20
            h['CmC'] =  0.148/h['CMR2']
            h['li_el'] = 'Si'
            h['name'] = 'margot/Fe-Si'
    elif mod_type == 'e':
        h = model_generic.copy()
        h['CMR2'] = 0.346
        h['CmC'] = 0.148/h['CMR2']
        h['li_el'] = mod_li_el
        h['name'] = mod_type + '_' + mod_name + '_' + mod_li_el
     
    # Margot  +1 sigma
    #margot_fessi_p1sigma = margot_fessi.copy()
    #margot_fessi_p1sigma['name'] = 'margot/Fe-S-Si+1sigma'
    #margot_fessi_p1sigma['CMR2'] = 0.346+0.014
    #margot_fessi_p1sigma['CmC'] = 0.148/(0.346+0.014)
    # Margot  -1 sigma
    #margot_fessi_m1sigma = margot_fessi.copy()
    #margot_fessi_m1sigma['name'] = 'margot/Fe-S-Si-1sigma'
    #margot_fessi_m1sigma['CMR2'] = 0.346-0.014
    #margot_fessi_m1sigma['CmC'] = 0.148/(0.346-0.014)

    return h