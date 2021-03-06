# -*- coding: utf-8 -*-
"""
Spyder Editor.
"""
####################################    Spatial Analyses: SYRACUSE   #######################################
#######################################  Analyse data from Census #######################################
#This script performs basic analyses for the Exercise 1 of the workshop using Census data.
# The overall goal is to explore spatial autocorrelation and aggregation of units of analyses.     
#
#AUTHORS: Benoit Parmentier                                             
#DATE CREATED: 12/29/2018 
#DATE MODIFIED: 03/14/2019
#Version: 1
#PROJECT: AAG 2019 workshop preparation
#TO DO:
#
#COMMIT: added Moran'I and spatial regression, AAG workshop
#Useful links:
#sudo mount -t vboxsf C_DRIVE ~/c_drive

##################################################################################################

###### Library used in this script

import gdal
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import rasterio
import subprocess
import pandas as pd
import os, glob
from rasterio import plot
import geopandas as gpd
import descartes
import libpysal as lp #new pysal interface
from cartopy import crs as ccrs
from pyproj import Proj
from osgeo import osr
from shapely.geometry import Point
import pysal as ps

################ NOW FUNCTIONS  ###################

##------------------
# Functions used in the script 
##------------------

def create_dir_and_check_existence(path):
    #Create a new directory
    try:
        os.makedirs(path)
    except:
        print ("directory already exists")

############################################################################
#####  Parameters and argument set up ########### 

#ARGS 1
in_dir = "/home/bparmentier/c_drive/Users/bparmentier/Data/python/Exercise_1/data"
#ARGS 2
out_dir = "/home/bparmentier/c_drive/Users/bparmentier/Data/python/Exercise_1/outputs"
#ARGS 3:
create_out_dir=True #create a new ouput dir if TRUE
#ARGS 7
out_suffix = "exercise1_03042019" #output suffix for the files and ouptut folder
#ARGS 8
NA_value = -9999 # number of cores
file_format = ".tif"

ct_2000_fname = "ct_00.shp" # CT_00: Cencus Tracts 2000
bg_2000_fname = "bg_00.shp" # BG_00: Census Blockgroups 2000
bk_2000_fname = "bk_00.shp" # BK_00: Census Blocks 2000

census_table_fname = "census.csv" #contains data from census to be linked
soil_PB_table_fname = "Soil_PB.csv" #same as census table
tgr_shp_fname = "tgr36067lkA.shp" #contains data from census to be linked

metals_table_fname = "SYR_metals.xlsx" #contains metals data to be linked

################# START SCRIPT ###############################

######### PART 0: Set up the output dir ################

#set up the working directory
#Create output directory

if create_out_dir==True:
    #out_path<-"/data/project/layers/commons/data_workflow/output_data"
    out_dir_new = "output_data_"+out_suffix
    out_dir = os.path.join(out_dir,out_dir_new)
    create_dir_and_check_existence(out_dir)
    os.chdir(out_dir)        #set working directory
else:
    os.chdir(create_out_dir) #use working dir defined earlier
    
    
#######################################
### PART 1: Read in datasets #######

## Census tracks for Syracuse in 2000
ct_2000_filename = os.path.join(in_dir,ct_2000_fname)
## block groups for Syracuse in 2000
bg_2000_filename = os.path.join(in_dir,bg_2000_fname)
## block for Syracuse in 200
bk_2000_filename = os.path.join(in_dir,bk_2000_fname)

#Read spatial data 
ct_2000_gpd = gpd.read_file(ct_2000_filename)
bg_2000_gpd = gpd.read_file(bg_2000_filename)
bk_2000_gpd = gpd.read_file(bk_2000_filename)

#Explore datasets:
ct_2000_gpd.describe()
ct_2000_gpd.plot(column="CNTY_FIPS")
ct_2000_gpd.head()

#Read tabular data
metals_df = pd.read_excel(os.path.join(in_dir,metals_table_fname))
census_syr_df = pd.read_csv(os.path.join(in_dir,census_table_fname),sep=",",header=0) #census information
#This soil lead in UTM 18 coordinate system
soil_PB_df = pd.read_csv(os.path.join(in_dir,soil_PB_table_fname),sep=",",header=None) #point locations

#Check size
ct_2000_gpd.shape #57 spatial entities (census)
bg_2000_gpd.shape #147 spatial entities (block groups)
bk_2000_gpd.shape #2025 spatial entities (blocks)
census_syr_df.shape #147 spatial entities
metals_df.shape #57 entities

#########################################################
####### PART 2: Visualizing population in 2000 at Census track level with geopandas layers 
#### We explore  also two ways of joining and aggregating data at census track level #########
#### Step 1: First join census information data to blockgroups
#### Step 2: Summarize/aggregate poppulation at census track level ###
#### Step 3: Plot population 2000 by tracks

### Step 1: First join census data to blockgroups

bg_2000_gpd.columns # missing census information:check columns' name for the data frame
census_syr_df.columns #contains census variables to join
#Key is "TRACT" but with a different format/data type
#First fix the format
bg_2000_gpd.head()
bg_2000_gpd.shape
census_syr_df.BKG_KEY.head()
#ct_2000_gpd.TRACT.dtype
census_syr_df.dtypes #check all the data types for all the columns
bg_2000_gpd.BKG_KEY.dtypes #check data type for the "BKG_KEY"" note dtype is "O"
census_syr_df.BKG_KEY.dtypes # check data type, note that it is "int64"

#Change data type for BKG_KEY column from object 'O" to int64
bg_2000_gpd['BKG_KEY'] = bg_2000_gpd['BKG_KEY'].astype('int64')

# Join data based on common ID after matching data types
bg_2000_gpd = bg_2000_gpd.merge(census_syr_df, on='BKG_KEY')
# Check if data has been joined 
bg_2000_gpd.head()

#Quick visualization of population 
bg_2000_gpd.plot(column='POP2000',cmap="OrRd")
plt.title('POPULATION 2000')

#############
#### Step 2: Summarize/aggregate poppulation at census track level

### Method 1: Summarize by census track using DISSOLVE geospatial operation

#To keep geometry, we must use dissolve method from geopanda
census_2000_gpd = bg_2000_gpd.dissolve(by='TRACT',
                                       aggfunc='sum')
type(census_2000_gpd)
census_2000_gpd.index
#Note that the TRACT field has become the index
census_2000_gpd=census_2000_gpd.reset_index() # reset before comparing data
census_2000_gpd.shape #Dissolved results shows aggregation from 147 to 57.

### Method 2: Summarize using groupby aggregation and joining

##Note losing TRACT field
census_2000_df = bg_2000_gpd.groupby('TRACT',as_index=False).sum()
type(census_2000_df) #This is a panda object, we lost the geometry after the groupby operation.
census_2000_df.shape #Groupby results shows aggregation from 147 to 57.

### Let's join the dataFrame to the geopanda object to the census track layer 
census_2000_df['TRACT'].dtype == ct_2000_gpd['TRACT'].dtype #Note that the data type for the common Key does not mach.  
census_2000_df['TRACT'].dtype # check data type field from table
ct_2000_gpd['TRACT'].dtype # check data type field from census geopanda layer
ct_2000_gpd['TRACT'] = ct_2000_gpd.TRACT.astype('int64') #Change data type to int64
ct_2000_gpd.shape #57 rows and 8 columns

ct_2000_gpd = ct_2000_gpd.merge(census_2000_df, on='TRACT')
ct_2000_gpd.shape #57 rows and 50 columns

#### Step 3: Plot population 2000 by tracks in Syracuse

### Check if the new geometry of entities is the same as census
fig, ax = plt.subplots(figsize=(12,8))
ax.set_aspect('equal') # set aspect to equal, done automatically in *geopandas* plot but not in pyplot
census_2000_gpd.plot(ax=ax,column='POP2000',cmap='OrRd')
ct_2000_gpd.plot(ax=ax,color='white',edgecolor="red",alpha=0.7) # Check if outputs from two methods match
ax.set_title("Population", fontsize= 20)

#### Generate population maps with two different class intervals

title_str = "Population by census tract in 2000"
census_2000_gpd.plot(column='POP2000',cmap="OrRd",
                 scheme='quantiles')
plt.title(title_str)

### Let's use more option with matplotlib

fig, ax = plt.subplots(figsize=(14,6))
census_2000_gpd.plot(column='POP2000',cmap="OrRd",
                 scheme='equal_interval',k=7,
                 ax=ax,
                 legend=False)

fig, ax = plt.subplots(figsize=(14,6))
census_2000_gpd.plot(column='POP2000',cmap="OrRd",
                 scheme='quantiles',k=7,
                 ax=ax,
                 legend=True)
ax.set_title('POP2000')

#Problem with legend
#ax.legend(loc=3,
#          fontsize=25,
#          frameon=False)
#plt.show()
#https://nbviewer.jupyter.org/github/pysal/mapclassify/blob/master/notebooks/south.ipynb
#q10 = ps.Quantiles(tx.HR90,k=10)
#q10.bins

#f, ax = plt.subplots(1, figsize=(9, 9))
#tx.assign(cl=q10.yb).plot(column='cl', categorical=True, \
#        k=10, cmap='OrRd', linewidth=0.1, ax=ax, \
#        edgecolor='white', legend=True)
#ax.set_axis_off()
#plt.show()

##############################################
##### PART 3: SPATIAL QUERY #############
### We generate a dataset with metals and lead information by census tracks.
### To do so we use the following steps:
##Step 1: Join metals to census tracks 
##Step 2: Generate geopanda from PB sample measurements 
##Step 3: Join lead (pb) measurements to census tracks
##Step 4: Find average lead by census track

##### Step 1: Join metals to census tracks ###### 

metals_df.head()
metals_df.describe() # 57 rows  
##Number of rows suggests matching to the following spatial entities
metals_df.shape[0]== ct_2000_gpd.shape[0]
#Check data types before joining tables with "merge"
metals_df.dtypes
ct_2000_gpd.dtypes
ct_2000_gpd.shape
census_metals_gpd = ct_2000_gpd.merge(metals_df,left_on='TRACT',right_on='ID')
census_metals_gpd.shape #census information has been joined

##### Step 2: Generate geopanda from PB sample measurements ##### 
# Processing lead data to generate a geopanda object using shapely points

soil_PB_df.columns #Missing names for columns
soil_PB_df.columns = ["x","y","ID","ppm"]
soil_PB_df.head()

soil_PB_gpd = soil_PB_df.copy() # generate a new panda DataFrame object
type(soil_PB_gpd)
soil_PB_gpd['Coordinates']=list(zip(soil_PB_gpd.x,soil_PB_gpd.y)) #create a new column with tuples of coordinates
type(soil_PB_gpd)
soil_PB_gpd['Coordinates']= soil_PB_gpd.Coordinates.apply(Point) #create a point for each tupple row
type(soil_PB_gpd.Coordinates[0]) #This shows that we created a shapely geometry point
type(soil_PB_gpd) #This is still an panda DataFrame
soil_PB_gpd = gpd.GeoDataFrame(soil_PB_gpd,geometry='Coordinates') #Create a gpd by setting the geometry column
type(soil_PB_gpd) # This is now a GeoDataFrame

## Checking and setting the coordinates reference system
soil_PB_gpd.crs #No coordinate reference system (CRS) is set
census_metals_gpd.crs # Let's use the metal geopanda object to set the CRS

## Find out more about the CRS using the epsg code
epsg_code = census_metals_gpd.crs.get('init').split(':')[1]
inproj = osr.SpatialReference()
inproj.ImportFromEPSG(int(epsg_code))
inproj.ExportToProj4() # UTM 18: this is the coordinate system in Proj4 format
## Assign projection system
soil_PB_gpd.crs= census_metals_gpd.crs #No coordinate system is set
soil_PB_gpd.head()

## Now plot the points
fig, ax = plt.subplots()
census_metals_gpd.plot(ax=ax,color='white',edgecolor='red')
soil_PB_gpd.plot(ax=ax,marker='*',
                 color='black',
                 markersize=0.8)

##### Step 3: Join lead (pb) measurements to census tracks #####
# Spatial query: associate points of pb measurements to each census tract

soil_PB_joined_gpd =gpd.tools.sjoin(soil_PB_gpd,census_2000_gpd,
                     how="left")
soil_PB_joined_gpd.columns
soil_PB_joined_gpd.shape #every point is associated with information from the census track it is contained in

len(soil_PB_joined_gpd.BKG_KEY.value_counts()) #associated BKG Key to points: 57 unique identifiers
len(soil_PB_joined_gpd.index_right.value_counts()) #associated BKG Key to points: 57 unique identifiers

#### Step 4: Find average lead by census track #####

grouped_PB_ct_df = soil_PB_joined_gpd[['ppm','TRACT','index_right']].groupby(['index_right']).mean() #compute average by census track
grouped_PB_ct_df = grouped_PB_ct_df.reset_index()
grouped_PB_ct_df.shape
grouped_PB_ct_df.head()

#grouped = grouped.rename(columns={'index_right': 'TRACT',
#                            'ppm': 'pb_ppm' })
grouped_PB_ct_df = grouped_PB_ct_df.rename(columns={'ppm': 'pb_ppm' })
type(grouped_PB_ct_df)

census_metals_gpd = census_metals_gpd.merge(grouped_PB_ct_df,on="TRACT")
census_metals_gpd.shape
census_metals_gpd.columns #check for duplicate columns

from shapely.geometry import shape
import fiona
    
census_metals_df = pd.DataFrame(census_metals_gpd.drop(columns='geometry'))
outfile = "census_metals_pb_"+'_'+out_suffix+'.csv'

census_metals_df.to_csv(outfile)

outfile = "census_metals_pb_"+'_'+out_suffix+'.shp'
census_metals_gpd.to_file(os.path.join(out_dir,outfile))

#################################################
##### PART IV: Spatial regression: Vulnerability to metals #############
#Examine the relationship between metals, Pb and vulnerable populations in Syracuse
## Step 1: Explore Autocorrelation with Moran's I
## Step 2: Spatial regression: examine relationship between lead ppm and % hispanic

#### Step 1: Explore Autocorrelation with Moran's I #######

census_metals_gpd.index
census_metals_gpd = census_metals_gpd.set_index('TRACT')

from libpysal.weights.contiguity import Queen

w = Queen.from_dataframe(census_metals_gpd)
type(w)
w.transform = 'r'
w.n # number of observations (spatial features)
w.neighbors # list of neighbours per census track
w.mean_neighbors

#http://pysal.org/notebooks/viz/splot/esda_morans_viz
import os
import splot

from esda.moran import Moran

#w = Queen.from_dataframe(gdf)
y = census_metals_gpd['pb_ppm'] 
y.shape
moran = Moran(y, w)
moran.I
moran.EI

from splot.esda import plot_moran

plot_moran(moran, zstandard=True, figsize=(10,4))
plt.show()
moran.p_sim #observed moran's I statistically significant
y_lag = ps.lag_spatial(w,y) #this is a numpy array

census_metals_gpd['y'] = census_metals_gpd.pb_ppm
census_metals_gpd['y_lag'] = y_lag

sns.regplot(x=y,y=y_lag,data=census_metals_gpd)

# now plot neighbours links

### Step 2: Spatial regression: examine relationship between lead ppm and % hispanic

y.values.shape #not the right dimension
y = y.values.reshape(len(y),1)
y_lag = y_lag.reshape(len(y_lag),1)

x = census_metals_gpd['perc_hispa']
x = x.values.reshape(len(x),1)

mod_ols = ps.spreg.OLS(y,x)
mod_ols.u 
m_I_residuals = ps.Moran(mod_ols.u,w)
m_I_residuals.p_sim # suggesting there is autocorreation
m_I_residuals.I
#take into account autocorr in spreg
mod_ols.summary

## Use spatial lag model from the pysal package
## Requires pysal weight object
w_queen = ps.weights.queen_from_shapefile(outfile)
w_queen.transform = 'R'
w_queen.neighbors

mod_ols_test = ps.spreg.OLS(y,x,w_queen)#w must be pysal object not libpysal
mod_ols_test.summary

mod_ml_lag = ps.spreg.ML_Lag(y,x,w_queen)
mod_ml_lag.summary
mod_ml_lag.betas #intercept,  %hispanic,spatial lag (rho)
# Add significance values?


################################## END OF SCRIPT ########################################














