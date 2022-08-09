import numpy as np
import shoote as lc
import glob,os,sys
from globalvar import *
import TEST_visualization_evolution as vis
import pandas as pd
import csv # for adding data to csv -- added 6/28/2022

def drivere(param, model, init, pdicr): # pdicr == present day inner core radius -- added 6/29/2022 for the for loop in main.py for the csv files/figures

    scale = param['scale']
    rhomean_s = param['rhomean']
    rm_s = param['rm']
    hcr0 = param['hcr']
    rhocr = param['rhocr']
    maxit = 15

    init = pd.read_hdf(model, key='misc') # key misc is a big list of scalar quantities.
    chi_li_in_fix = init['chi_li_in'].values[0] #params['chiSin'].values[0] # initial sulfur
    chi_li_icb = init['chi_li_icb'].values[0]  # sulfur at inner core boundary
    ricb0 = init['ricb'].values[0] # inner core boundary radius
    rcmb0 = init['rcmb'].values[0] # core-mantle boundary radius
    rhom = init['rhom'].values[0] # what mantle density?
    core_mass = init['core_mass'].values[0] # the mass of core?
    Tctr0 = pd.read_hdf(model, key='T')[0] # Temperature profile at center? 
    Tmantle_old = pd.read_hdf(model, key='T').values[-1] # temperature at mantle surface?
    Pctr = pd.read_hdf(model, key='P')[0] # pressure profile at center? 
    chi_li0 = pd.read_hdf(model, key='chi_li')[0] #   
    mantle_mass = lc.get_mass_mantle(rcmb0,rm_s-hcr0,rhom) # get mantle mass

    # create folder for output data. If not exist, create one and run the models.
    directory = evolution_figure_path + str(round(ricb0/1000,1))
    print(directory, os.path.exists(directory))
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Initial Guess
    # 1) P(r=0) 2) ricb 3) rcmb 4) rm 5) chi_li_icb
    v0=[Pctr/scale['P'],1,rcmb0/rm_s,1,chi_li_icb,1]
    
    Gyr = 0
    k = 0

    for ricb_evo in range(0,int(ricb0/1000)+50000,20):
        ricb = (ricb0-ricb_evo*1E+3)/rm_s
        if ricb>0:
            print('ricb>0 : running model WITH inner core')
            v = lc.mynewtonSys('J_mercmodel',v0,
                        [ricb,rhocr,rhom,chi_li_in_fix,core_mass,mantle_mass,param,scale],
                        xtol=xtol, ftol=ftol, maxit=maxit, verbose=True)
        
            v0=v.tolist() # % initial guess for next is taken as previous solution.
        
            # final solution
            [f,r,yy,fout,ricb,rhomean,rm,hcr] = lc.shoot_mercmodel(v,ricb,rhocr,rhom,
                chi_li_in_fix,core_mass,mantle_mass,
                param,scale)
        
        else:
            print('ricb<=0 : running model WITHOUT inner core')
            Tsrpls = abs(ricb0-ricb_evo*1E+3)/1000
            v = lc.mynewtonSys('J_mercmodel_nosic',v0,
                    [Tsrpls,rhocr,rhom,chi_li_in_fix,core_mass,mantle_mass,param,scale],
                    xtol=xtol, ftol=ftol, maxit=maxit, verbose=True)
            
            [f,r,yy,fout,ricb,rhomean,rm,hcr] = lc.shoot_mercmodel_nosic(v,Tsrpls,rhocr,rhom,chi_li_in_fix,core_mass,mantle_mass,param,scale)
            v0=np.insert(v,1,0).tolist()

        nr=len(r) # r is all the radius points array for this specific ricb[k]. yy is a 6-element array.
        
        # re-scale
        r=scale['a']*r
        P1=scale['P']*yy[0]
        g1=scale['ga']*yy[1]
        T1=scale['T']*yy[2]
        Tctr=T1[0]
        Tad=scale['T']*yy[3]
        rho1=rhomean*yy[4]
        chi_li=yy[5] # the light element wt profile inverted

        #rhom[k]=v[3]*rhomean # different from PresentDay model, this is inverted now.
        chi_li_icb=v[4]
        chi_li_cmb=chi_li[-1]
        rcmb=r[-1]
        
        rhd=(rm-hcr)
        r_2=np.append(r,[rhd,rm])    
        rho1_2=np.append(rho1,[rhom,rhocr])
        moi = lc.get_moi(r_2,rho1_2,rhomean)
        ccc = lc.get_ccc(r_2,rho1_2,rhomean)
        cmc = 1-ccc/moi
        #mass = lc.get_mass_norm(r_2,rho1_2,rhomean)
        #print(mass,moi,ccc,cmc)
        #plt.plot(r/1000,rho1)
        #plt.show()
        
        Picb=fout[0]
        Tcmb=fout[1]
        isnow=fout[2]
        isnowcmb=fout[3]
        chi_li_in=fout[4]
        
        Tmantle = T1[-1]
        Tdiff = Tmantle-Tmantle_old
        Tmantle_old = Tmantle
        Gyr = Gyr-Tdiff/60
        
        #print('rhom:',rhom[k])
        vis.plot_isnow(ricb,r,rhd,rm,T1,P1,chi_li,rho1,
                chi_li_in,moi,cmc,1,Gyr,k,directory,param)

        # write in row of csv file that includes radii on snow zones and cmb temperature to plot -- added 6/27/2022
        row = [chi_Si_icb, ricb/1E+3, Tcmb]
        print("chi_Si_icb", chi_Si_icb)
        print("ricb", ricb/1E+3)
        print("Tcmb", Tcmb)
        for radius in vis.radii_list:
            row.append(radius)
        print("row", row)
        csv_radii_cmbtemp = open(radii_vs_cmbtemp_path + csv_radii_vs_cmbtemp_filename + '_' + str(pdicr) + '.csv', 'a')
        if row[3] != 0.0:
            writer = csv.writer(csv_radii_cmbtemp)
            writer.writerow(row)
        csv_radii_cmbtemp.close()
        
        #print('rs:',rs[k]/1000)
        #print('isnow:',fout[2])
        #print('isnow cmb:',fout[3])
        #print('DeltaS:',chiS[-1],v[4])    
        Pcmb=P1[-1]
        Pctr=P1[0]
        chi_li_euticb=0.11 +0.187*np.exp(-0.065*Picb*1e-9)
        chi_li_eutcmb=0.11 +0.187*np.exp(-0.065*Pcmb*1e-9)
        k+=1
        
        print('FINAL MANTLE TEMPERATURE:',Tmantle)
        print()
        if Gyr<-4.5: break
        
        zones=np.zeros(len(P1))
        Tms=[]
        for i in range(len(r)):
        #Tm = lc.getmelt_anzellini(chiS[i],P1[i],param,0)
            Tm = lc.getCoreLiquidus(chi_li[i],chi_Si_icb,P1[i],param,0)
            Tms.append(Tm)
        if abs(T1[i]-Tm)<1e-8:
            zones[i]=1  
            
        if os.path.isdir(evolution_data_path):
            print(evolution_data_path)
        else:
            os.mkdir(evolution_data_path)
            
        name = evolution_data_path + str(round(ricb0/1000,1))+'_{:03d}'.format(k)+'.txt'
        output = np.dstack((r/1e3,rho1,P1/1e9,T1,chi_li,zones))[0]
        np.savetxt(name,output,fmt='%.3f %.3f %.3f %.3f %.3f %i',
            header = 'Time: '+str(round(Gyr,2))+' Gyr \n Radius [km] # Density [kg/m3] # Pressure [GPa] # Temperature [K] # Light Element Content [wt.%] # Snow Zone')        
        vis.gif_writer(directory+'/')
