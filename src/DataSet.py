import xarray as xr
import numpy as np

import matplotlib.colors as colors

import os

import DateMap




class DataSet():
    """
    Class for organizing a dataset
    
    :Contact: hytang2@illinois.edu
    """
    def __init__(self, 
                 name : str,
                 data_paths : dict[str : str],
                 time_steps : int, 
                 unit : str | None = None, 
                 time_unit : str | None = None, 
                 start_time : str | None = None,
                 data_format : str | None = "cfgrib"):
        """
        DataSet class 
        
        Purpose : After downloading a single-variable dataset(in grib/netcdf etc.), this class 
        opens the dataset and creates a wrapper around it to enable 
         1. Spatial Slicing 
         2. Data analysis like spatial averaging, PCA(EOF) etc.
         3. Proper time annotation
        
        About 'mode':
            If you wish to plot/analyze a vector field, simply put path to data files for both component in param data_paths with u_component preceding 
            Else the default is to plot/analyze a scalar field 
            
            The datasest class automatically detect the number of files and decide the mode
        
        :param name: Name of the data set you want to give
        :type name: str
        :param data_paths: A python dictionary var_name -> path_to_data
        :type data_paths: dict[str: str]
        :param time_steps: The total number of time steps
        :type time_steps: int
        :param unit: The unit of the climate variable
        :type unit: str | None
        :param time_unit: The unit of the time, e.g. days
        :type time_unit: str | None
        :param start_time: The start time, \n
            - if the time_unit is months, the format should be %Y-%m \n
            - if the time_unit is days then the format should be %Y-%m-%d \n
            - if the time_unit is hours, the nthe format should be %Y-%m-%d %H \n
        :type start_time: str | None
        """
        self.name = name #name of data set
        self.mode = 'vector' if len(list(data_paths.keys())) > 1 else 'scalar'
        self.time_steps = time_steps
        self.unit = unit
        self.time_unit = time_unit
        if(start_time != None) : self.date_map = DateMap.DateMap(start_time, time_unit, time_steps)
        
        #coarsen_factor is defualted to 1, but in vector mode it is set to 12 for better visual effect
        self.coarsen_factor = 1
        
        #open datasets 
        if self.mode == 'vector' :
            self.coarsen_factor = 12 #seems to work well
            self.u_name, self.v_name = list(data_paths.keys())[0], list(data_paths.keys())[1]
            u_data_path, v_data_path = data_paths[self.u_name], data_paths[self.v_name]

            self.U = xr.open_dataset(u_data_path, engine=data_format)
            self.V = xr.open_dataset(v_data_path, engine=data_format)
        else : 
            self.s_name = list(data_paths.keys())[0]
            s_data_path = data_paths[self.s_name]
            self.S = xr.open_dataset(s_data_path, engine=data_format)
        
    
    def to_lat_index(self, lat) :
        """
        Helper function to get index in latitude array
        :param lat: latitude [-90, 90]
        """
        if(lat > 90 or lat < -90) :
            raise RuntimeError("[DataSet-Error] lat out of bound")
        return  int((90 - lat) * 4)

    def to_lon_index(self, lon):
        if(lon < 0 or lon > 360) :
            raise RuntimeError("[DataSet-Error] lon out of bound")
        return int(lon * 4)
    
    def get_mask(self, lat, lon, dlat, dlon):
        if(lat == None and lon == None and dlat == None and dlon == None) :
            latmask = slice(0, len(self.array["latitude"]), self.coarsen_factor)
            lonmask = slice(0, len(self.array["longitude"]), self.coarsen_factor)
        elif(lat != None and lon != None and dlat != None and dlon != None):
            lat_min, lat_max = max(lat - dlat, -90), min(lat + dlat, 90)
            lon_min, lon_max = max(lon - dlon, -180), min(lon + dlon, 180)
            latmask = slice(self.to_lat_index(lat_max), self.to_lat_index(lat_min), self.coarsen_factor)
            lonmask = slice(self.to_lon_index(lon_min), self.to_lon_index(lon_max), self.coarsen_factor)
        else: 
            raise RuntimeError("[DataSet-ERROR] region information ambiguous")
        return latmask, lonmask
    
    def getMesh(self, 
                lat : float | None = None, 
                lon : float | None = None, 
                dlat : float | None = None, 
                dlon : float | None = None, 
                time_step : float | None = None,
                ) -> tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
        """
        Getting the meshes for lattitude, lontitude and datafield resp. within the region 
            [lat - dlat, lat + dlat] x [lon - dlon, lon + dlon]
        where x is the cartesian product
        
        :param time_step: time step of interest
        :param lat: latitude
        :type lat: float
        :param lon: longitude
        :type lon: float
        :param dlat: delta latitude
        :type dlat: float
        :param dlon: delta longitude
        :type dlon: float
        :return: Three 1d array
        :rtype: tuple
        """
        if time_step!= None: 
            if time_step >= self.time_steps :
                raise RuntimeError("[DataSet-ERROR] time step out of bound")
        
        latmask, lonmask = self.get_mask(lat, lon, dlat, dlon)
        
        if self.mode == 'vector':
            latarray = self.U["latitude"][latmask]
            lonarray = self.U["longitude"][lonmask]
            latmesh, lonmesh = np.meshgrid(latarray, lonarray)
            if time_step != None:
                Umesh = self.U[self.u_name][time_step][latmask, lonmask]
                Vmesh = self.V[self.v_name][time_step][latmask, lonmask]
            else:
                Umesh = self.U[self.u_name][:][latmask, lonmask]
                Vmesh = self.V[self.v_name][:][latmask, lonmask]
            return latmesh, lonmesh, Umesh, Vmesh
        
        if self.mode == 'scalar':
            latarray = self.S["latitude"][latmask]
            lonarray = self.S["longitude"][lonmask]
            latmesh, lonmesh = np.meshgrid(latarray, lonarray)
            if time_step != None:
                Smesh = self.S[self.s_name][time_step][latmask, lonmask]
            else :
                Smesh = self.S[self.s_name][:][latmask, lonmask]
            return latmesh, lonmesh, Smesh
        
    def getNormalizer(self, X):
        min = np.min(X)
        center = np.mean(X)
        max = np.max(X)
        return colors.TwoSlopeNorm(vmin = min, vcenter=center, vmax=max)
        
    def computeNormalizerForScalar(self, lat, lon, dlat, dlon):
        if self.mode == 'scalar':
            _, _, Smesh = self.getMesh(lat, lon, dlat, dlon)
            Smesh = Smesh.to_numpy()
            self.smin = np.min(Smesh)
            self.scenter = np.mean(Smesh)
            self.smax = np.max(Smesh)
            self.scalar_normalizer = colors.TwoSlopeNorm(vmin = self.smin, vcenter=self.scenter, vmax=self.smax)
    
    def getSpatialAveragedTimeSeries(self, lat : int, lon : int, dlat : int, dlon : int) :
        """Produce a time series(1d array) of spatial average of the data in the given region [lat - dlat, lat + dlat] x [lon - dlon, lon + dlon] 
        
        :param lat: latitude
        :type lat: float
        :param lon: longitude
        :type lon: float
        :param dlat: delta latitude
        :type dlat: float
        :param dlon: delta longitude
        :type dlon: float
        :return: time-series of spatial average
        :rtype: 1d numpy array
        """
        if(self.mode == 'scalar'):
            time_series = []
            for time_step in range(self.time_steps):
                _, _, Smesh = self.getMesh(lat, lon, dlat, dlon, time_step)
                time_series.append(np.mean(Smesh.to_numpy()))
            return np.array(time_series)
        else :
            raise RuntimeError("vector mode can't have spatially averaged time series")
    
    
        
   