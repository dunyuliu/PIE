#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 11 14:52:43 2019

@author: gregor
"""

import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from . import shoote as lc
import matplotlib.animation as animation
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.patches as mpatches
from PIL import Image
from .globalvar import *

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
    
    fig,ax = plt.subplots(3,3,figsize=(27,27)) # CHANGE BACK TO (2,3,figsize=(18,12)) WHEN DONE TESTING

    # Temperature profiles
    ax[0,0].plot(r/1000,np.array(Tms),label='Tmelt',lw=3,color='blue')
    ax[0,0].plot(r/1000,np.array(T),label='Tcore',lw=3,color='red')
    ax[0,0].set_xlim((0,2700))
    ax[0,0].set_ylim((1200,2700))  
    ax[0,0].set_ylabel('Temperature [K]')
    ax[0,0].set_xlabel('Radius [km]')
    ax[0,0].legend()
    ax[0,0].grid()
    
    # T-Tm profile
    ax[1,0].plot(r/1000,T-np.array(Tms),lw=3,color='black')
    ax[1,0].set_xlim((0,2700))
    ax[1,0].set_ylim((0,150)) 
    ax[1,0].set_xlabel('Radius [km]')
    ax[1,0].set_ylabel('Tcore-Tmelt [K]')
    ax[1,0].grid()

    
    # Density profile
    ax[0,1].plot(r/1000,np.array(rho)/1000,lw=3,color='black')
    ax[0,1].set_xlim((0,2700))
    ax[0,1].set_ylim((4,9))  
    ax[0,1].set_ylabel('Density [g/cm$^3$]')
    ax[0,1].set_xlabel('Radius [km]')
    ax[0,1].grid()

    # Pressure profile
    ax[1,1].plot(r/1000,np.array(P/1E+9),lw=3,color='black')
    ax[1,1].set_xlim((0,2700))
    ax[1,1].set_ylim((0,50))  
    ax[1,1].set_ylabel('Pressure [GPa]')
    ax[1,1].set_xlabel('Radius [km]')
    ax[1,1].grid()
    
    # Sulfur Concentration
    ax[0,2].plot(r/1000,chi_li*100,lw=3,color='black')
    ax[0,2].set_xlim((0,2700))
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
    #ax[1,2].grid() #commented out 6/20/2022
       
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
    
#    ax[1,2]=plt.gca()
#    ax[1,2].axis('scaled')
#    ax[1,2].axis('off')

    #if T[-1]>2000: fig.figimage(im, 750, 50)
    
    colors = ["lightyellow", "black", "sandybrown", "salmon", "silver", ]
    texts = ["Iron Snow", "Crust", "Mantle", "Outer Core", "Inner Core"]
    patches = [ mpatches.Patch(color=colors[i], label="{:s}".format(texts[i]) ) for i in range(len(texts)) ]
    ax[1,1].legend(handles=patches, loc='lower right', bbox_to_anchor=(2.7, 0))
    #fig.suptitle("Time: "+str(round(Gyr,2))+' Gyr',fontsize=20)
    #plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    #plt.tight_layout()

    # NEXT LINES OF CODE USED FOR TESTING -- DELETE WHEN DONE

    """
    # REMOVED WHEN PLOTTING SNOW ZONES
    # make figure that plots bar chart of radii of crust, mantle, outer core, and inner core through time
    xlabels = ['ic','oc','mantle','crust']
    yvals = [ri/1E+3, r[-1]/1E+3, rh/1E+3, rm/1E+3]
    colors = ['silver', 'salmon', 'sandybrown', 'black']
    ax[2,0].bar(xlabels, yvals, color=colors, width=0.6)
    ax[2,0].set_ylabel('Radius [km]')
    ax[2,0].set_ylim((0,2500))
    ax[2,0].grid()
    """
    # SUBPLOT [2,0]
    # make figure that plots the differences between the layers
    # so (crust - mantle), (mantle - outer core), (outer core - inner core)
    # subplot position changed from [2,1] to [2,0] to make room for snow zone plots
    xlabels = ['ocr - icr', 'mr - ocr', 'cr - mr']
    yvals = [(r[-1]/1E+3)-(ri/1E+3), (rh/1E+3)-(r[-1]/1E+3), (rm/1E+3)-(rh/1E+3)]
    colors = ['silver', 'salmon', 'sandybrown']
    edgecolors = ['salmon', 'sandybrown', 'black']
    ax[2,0].bar(xlabels, yvals, color=colors, edgecolor=edgecolors, width=0.6)
    ax[2,0].set_ylabel('Radius Difference [km]')
    ax[2,0].set_ylim((0,2500))
    ax[2,0].grid()

    # SUBPLOT [2,1]
    # make figure that plots the radii of the snow zones with the inner core radius as it changes
    lb_snow = [] # array of lower boundary for snow zone(s)
    ub_snow = [] # array of upper boundary for snow zone(s)
    new_zone = True # bool to see whether we are looking at a new snow zone or not
    for i in range(1,len(zones)):
        if (zones[i]-zones[i-1])<2:
            if new_zone == True:
                lb_snow.append(zones[i-1])
            new_zone = False
            if i == (len(zones) - 1):
               ub_snow.append(zones[i])
        else:
            if new_zone == False:
                ub_snow.append(zones[i-1])
            new_zone = True
    print("zones", zones)
    print("lb_snow", lb_snow)
    print("ub_snow", ub_snow)

    xlabels = ['i. core', 'sz1', 'sz2', 'sz3'] # make x labels for inner core and each snow zone (can overestimate the total number of snow zones)
    ystart = [0.0] # make starting points of each bar (representing a layer) for horizontal bar chart
    ystop = [ri/1E+3] # make end points for each bar (representing a layer) for horizontal bar chart
    colors = ['silver']
    lb_radius = [] # keep in case lb_radius isn't assigned below
    ub_radius = [] # keep in case ub_radius isn't assigned below
    for i in range(0,len(lb_snow)):
        lb_radius = r[lb_snow[i]]/1E+3
        ystart.append(lb_radius)
        ub_radius = r[ub_snow[i]]/1E+3
        ystop.append(ub_radius - lb_radius) # the bar function takes in ystop as the height of the bars -- does not plot as y value
        colors.append('lightyellow')
    if len(ystart) != len(xlabels):
        sz_diff = len(xlabels) - len(ystart)
        for blank_sz in range(0,sz_diff): # if there are less snow zones than what are indicated in xlabels, add on zeros to ystart and ystop
            ystart.append(0.0)
            ystop.append(0.0)

    ax[2,1].bar(xlabels, ystop, bottom=ystart, color=colors, edgecolor='black', width=0.8)
    ax[2,1].set_ylabel("Radius [km]")
    ax[2,1].set_ylim((0,2500))
    ax[2,1].grid()

    print("all radii", r/1E+3)
    print("lb_radius", lb_radius)
    print("ub_radius", ub_radius)
    print("ystart", ystart)
    print("ystop", ystop)

    # Make list to go into csv row that inclides inner core radius, lb sz1, ub sz1, lb sz2, ub sz2, lb sz3, ub sz3 -- added 6/27/2022
    radii_list.clear()
    radii_list.append(ri/1E+3)
    for i in range(0, len(lb_snow)):
        lb_radius = r[lb_snow[i]]/1E+3
        ub_radius = r[ub_snow[i]]/1E+3
        radii_list.append(lb_radius)
        radii_list.append(ub_radius)
    print("radii_list", radii_list)
    if len(radii_list) != 7:
        diff = 7 - len(radii_list)
        for i in range(0,diff):
            radii_list.append(0.0)
    print("radii_list", radii_list)
    # also append cmb radius (essentially outer core radius) to radii_list
    radii_list.append(r[-1]/1E+3)
    print("radii_list", radii_list)

    # SUBPLOT [2,2]
    # Plot the difference between the lower bound of each snow zone and the radius of the inner core
    xlabels = ["lb sz1 - icr", "ub sz1 - icr",  "lb sz2 - icr", "ub sz2 - icr", "ub sz3 - icr", "lb sz3 - icr"]
    r_diffs = [] # differences between the lower boundary of each snow zone and the radius of the inner core
    hatches = [] # visually differentiates between (lower bound - inner core radius) and (upper bound - inner core radius)
    for i in range(0, len(lb_snow)):
        r_diffs.append((r[lb_snow[i]]/1E+3) - ri/1E+3)
        r_diffs.append((r[ub_snow[i]]/1E+3) - ri/1E+3)
        hatches.append("/")
        hatches.append("x")
    if len(xlabels) != len(r_diffs):
        diff_diff = len(xlabels) - len(r_diffs)
        for blank_diff in range(0,diff_diff): # if there are less snow zones than what are indicated in xlabels, add on zeros to r_diffs
            r_diffs.append(0.0)
            hatches.append("o")

    print("r_diffs", r_diffs)
    
    ax[2,2].bar(xlabels, r_diffs, color = "lightyellow", edgecolor="black", width=0.8, hatch=hatches)
    ax[2,2].tick_params(axis='x', labelsize=11)
    ax[2,2].set_ylabel("Radial Difference [km]")
    ax[2,2].set_ylim((0,2500))
    ax[2,2].grid()


    
    # END OF TESTING

    plt.savefig(directory+"/{:03d}".format(img)+'.pdf', bbox_inches="tight")
    #plt.show()

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
    l.sort(key=alphanum_key,reverse=True)
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
