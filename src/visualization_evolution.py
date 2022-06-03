#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 11 14:52:43 2019

@author: gregor
"""

import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import libCore_evolution as lc
import matplotlib.animation as animation
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.patches as mpatches
from PIL import Image
from globalvar import *

#im = Image.open('volcano.png')
#height = im.size[1]
## We need a float array between 0-1, rather than
## a uint8 array between 0-255
#im = np.array(im).astype(np.float) / 255


def plot_donut(rmin,rmax):
    n, radii = 100, [rmin, rmax]
    theta = np.linspace(0, 2*np.pi, n, endpoint=True)
    xs = np.outer(radii, np.cos(theta))
    ys = np.outer(radii, np.sin(theta))
    
    # in order to have a closed area, the circles
    # should be traversed in opposite directions
    xs[1,:] = xs[1,::-1]
    ys[1,:] = ys[1,::-1]
    
    return xs,ys
    
def plot_isnow(ri,r,rh,rm,T,P,chi_li,rho,chi_li_in,moi,cmc,mass,Gyr,img,directory,param):

    font = {'family':'normal','size':16}
    matplotlib.rc('font', **font)

    crust = plt.Circle((0, 0), radius=rm/1E+3, color='black')
    mantle = plt.Circle((0, 0), radius=rh/1E+3, color='sandybrown')
    outer_core = plt.Circle((0, 0), radius=r[-1]/1E+3, color='salmon')
    inner_core = plt.Circle((0, 0), radius=ri/1E+3, color='silver')
    
    # identify snow zones
    zones=[]
    Tms=[]
    for i in range(len(r)):
        Tm = lc.getCoreLiquidus(chi_li[i],chi_Si_icb,P[i],param,0)
        Tms.append(Tm)
        if abs(T[i]-Tm)<1e-8:
            zones.append(i)
    
    fig,ax = plt.subplots(2,3,figsize=(18,12))

    # Temperature profiles
    ax[0,0].plot(r/1000,np.array(Tms),label='Tmelt',lw=3,color='blue')
    ax[0,0].plot(r/1000,np.array(T),label='Tcore',lw=3,color='red')
    ax[0,0].set_xlim((ri/1000-ice,r[-1]/1000))
    ax[0,0].set_ylim((1200,2700))  
    ax[0,0].set_ylabel('Temperature [K]')
    ax[0,0].set_xlabel('Radius [km]')
    ax[0,0].legend()
    ax[0,0].grid()
    
    # T-Tm profile
    ax[1,0].plot(r/1000,T-np.array(Tms),lw=3,color='black')
    ax[1,0].set_xlim((ri/1000-ice,r[-1]/1000))
    ax[1,0].set_ylim((0,150)) 
    ax[1,0].set_xlabel('Radius [km]')
    ax[1,0].set_ylabel('Tcore-Tmelt [K]')
    ax[1,0].grid()

    
    # Density profile
    ax[0,1].plot(r/1000,np.array(rho)/1000,lw=3,color='black')
    ax[0,1].set_xlim((ri/1000-ice,r[-1]/1000))
    ax[0,1].set_ylim((4,9))  
    ax[0,1].set_ylabel('Density [g/cm$^3$]')
    ax[0,1].set_xlabel('Radius [km]')
    ax[0,1].grid()

    # Pressure profile
    ax[1,1].plot(r/1000,np.array(P/1E+9),lw=3,color='black')
    ax[1,1].set_xlim((ri/1000-ice,r[-1]/1000))
    ax[1,1].set_ylim((0,50))  
    ax[1,1].set_ylabel('Pressure [GPa]')
    ax[1,1].set_xlabel('Radius [km]')
    ax[1,1].grid()
    
    # Sulfur Concentration
    ax[0,2].plot(r/1000,chi_li*100,lw=3,color='black')
    ax[0,2].set_xlim((ri/1000-ice,r[-1]/1000))
    ax[0,2].set_ylim((0,25))   
    if param['li_el']=='S': ax[0,2].set_ylabel('Sulfur Concentration [wt.%]')  
    elif param['li_el']=='Si': ax[0,2].set_ylabel('Silicon Concentration [wt.%]')
    elif param['li_el']=='S+Si': ax[0,2].set_ylabel('Sulfur Concentration [wt.%]')
    ax[0,2].set_xlabel('Radius [km]')  
    plt.text(0.02, 0.94, 'Avg. Concentration = '+str(round(chi_li_in*100,1))+' wt.%', transform=ax[0,2].transAxes)
    ax[0,2].grid()  
     
    # plot mercury layouts
    ax[1,2].add_patch(crust)
    ax[1,2].add_patch(mantle)
    ax[1,2].add_patch(outer_core)
    ax[1,2].add_patch(inner_core)
    ax[1,2].grid()
       
    # add snow zones
    for i in range(1,len(zones)):
        if (zones[i]-zones[i-1])<2:
            xs,ys = plot_donut(r[zones[i-1]]/1E+3,r[zones[i]]/1E+3)
            ax[1,2].fill(np.ravel(xs), np.ravel(ys),color='lightyellow')
      
    # annotate plot
    off = rm/1E+3
    ax[1,2].annotate('Crust = '+str(round(rm/1E+3,1))+' km', 
                xy=(off*np.cos(3*np.pi/12),off*np.cos(3*np.pi/12)), xytext=(2, 2),
                textcoords='offset points',
                color='black', size=14)
    ax[1,2].annotate('Mantle = '+str(round(rh/1E+3,1))+' km', 
                xy=(off*np.cos(2*np.pi/12),off*np.sin(2*np.pi/12)), xytext=(2, 2),
                textcoords='offset points',
                color='black', size=14)    
    ax[1,2].annotate('Outer Core = '+str(round(r[-1]/1E+3,1))+' km', 
                xy=(off*np.cos(1*np.pi/12),off*np.sin(1*np.pi/12)), xytext=(2, 2),
                textcoords='offset points',
                color='black', size=14) 
    ax[1,2].annotate('Inner Core = '+str(round(ri/1E+3,1))+' km', 
                xy=(off*np.cos(0),off*np.sin(0)), xytext=(2, 2),
                textcoords='offset points',
                color='black', size=14)             
    ax[1,2].annotate('Mass = '+str(round(mass,3))+' | MoI = '+str(round(moi,3))+ ' | $C_m/C$ = '+str(round(cmc,3)), 
                xy=(-off,1.05*off), xytext=(2, 2),
                textcoords='offset points',
                color='black', size=14)  
    ax[1,2].annotate('MoI = '+str(round(moi,3)), 
                xy=(-1.2*off,off), xytext=(2, 2),
                textcoords='offset points',
                color='black', size=14)  
    ax[1,2].annotate('$C_m/C$ = '+str(round(cmc,3)), 
                xy=(-1.2*off,off), xytext=(2, 2),
                textcoords='offset points',
                color='black', size=14)  
    
    ax[1,2]=plt.gca()
    ax[1,2].axis('scaled')
    ax[1,2].axis('off')

    #if T[-1]>2000: fig.figimage(im, 750, 50)
    
    colors = ["lightyellow", "black", "sandybrown", "salmon", "silver", ]
    texts = ["Iron Snow", "Crust", "Mantle", "Outer Core", "Inner Core"]
    patches = [ mpatches.Patch(color=colors[i], label="{:s}".format(texts[i]) ) for i in range(len(texts)) ]
    ax[1,1].legend(handles=patches, loc='lower right', bbox_to_anchor=(2.7, 0))
    #fig.suptitle("Time: "+str(round(Gyr,2))+' Gyr',fontsize=20)
    #plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    #plt.tight_layout()
    plt.savefig(directory+"/{:03d}".format(img)+'.pdf', bbox_inches="tight")
    plt.show()

import re

def tryint(s):
    try:
        return int(s)
    except:
        return s

def alphanum_key(s):
    """ Turn a string into a list of string and number chunks.
        "z23a" -> ["z", 23, "a"]
    """
    return [ tryint(c) for c in re.split('([0-9]+)', s) ]

def sort_nicely(l):
    """ Sort the given list in the way that humans expect.
    """
    l.sort(key=alphanum_key)
    return l
    
def gif_writer(directory):
    import imageio
    from pdf2image import convert_from_path
    import glob
    filenames = glob.glob(directory+'/*.pdf')
    filenames = sort_nicely(filenames)

    with imageio.get_writer(directory+'/movie.gif', mode='I') as writer:
        for filename in filenames:
            img = convert_from_path(filename)[0]          
            image =  np.array(img.getdata(),np.uint8).reshape(img.size[1], img.size[0], 3)
            #image = imageio.imread(filename)
            writer.append_data(image)
#gif_writer('/Users/gregor/Projects/Evolution of Mercury/models/evolution/margot/440.0/')