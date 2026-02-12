import xarray as xr
from matplotlib import animation 
import matplotlib.pyplot as plt 

import imageio.v2 as imageio 

import numpy as np
import os


import cartopy.crs as ccrs
import cartopy.feature as cfeature


class DataSet():
    """
    Helper class for organizing a grib dataset
    
    :Contact: hytang2@illinois.edu
    """
    def __init__(self, array : xr.DataArray, time_steps : int, data_var : str):
        """
        :param array: the grib data set
        :type array: xr.DataArray
        :param time_steps: total time steps
        :type time_steps: int
        :param data_var: the name of the climate variable, e.g. t2m
        :type data_var: str
        """
        self.array = array
        self.time_steps = time_steps
        self.data_var = data_var
    
    def to_lat_index(self, lat) :
        """
        Helper function to get index in latitude array
        :param lat: latitude [-90, 90]
        """
        return  int((90 - lat) * 4)

    def to_lon_index(self, lon):
        return int((lon + 180) * 4)
    
    def get_mask(self, lat, lon, dlat, dlon, coarsen_factor = 1):
        if(lat == None and lon == None and dlat == None and dlon == None) :
            latmask = slice(0, len(self.array["latitude"]), coarsen_factor)
            lonmask = slice(0, len(self.array["longitude"]), coarsen_factor)
        elif(lat != None and lon != None and dlat != None and dlon != None):
            lat_min, lat_max = max(lat - dlat, -90), min(lat + dlat, 90)
            lon_min, lon_max = max(lon - dlon, -180), min(lon + dlon, 180)
            latmask = slice(self.to_lat_index(lat_max), self.to_lat_index(lat_min), coarsen_factor)
            lonmask = slice(self.to_lon_index(lon_min), self.to_lon_index(lon_max), coarsen_factor)
        else: 
            raise RuntimeError("[DataSet-ERROR] region information ambiguous")
        return latmask, lonmask
    
    def getMesh(self, time_step, lat : float = None, lon : float = None, dlat : float = None, dlon : float = None, coarsen_factor : int =1) -> tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
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
        print(f"[DataSet-LOG]Extract mesh for {self.data_var} at lat = {lat}, lon = {lon} with coarsen_factor {coarsen_factor}")
        if time_step >= self.time_steps :
            raise RuntimeError("[DataSet-ERROR] time step out of bound")
        
        latmask, lonmask = self.get_mask(lat, lon, dlat, dlon, coarsen_factor=coarsen_factor)
        latmesh = self.array["latitude"][latmask]
        lonmesh = self.array["longitude"][lonmask]
        latmesh, lonmesh = np.meshgrid(latmesh, lonmesh)
        fieldmesh = self.array[self.data_var][time_step][latmask, lonmask]
        return latmesh, lonmesh, fieldmesh

class Visualize():
    def create_dir(self, dir):
        try : 
            os.mkdir(dir)
            print(f"[Visualize-LOG] Directory '{dir}' created")
        except FileExistsError : 
            print(f"[Visualize-LOG] Directory '{dir}' already exists")
            
    def __init__(self, task_name : str, data_paths : dict[str, str], outputs_dir, mode = 'scalar', projection = ccrs.PlateCarree(), time_steps : int = 1):
        """
        A naive **climate data visualize class** for one-shot animation
    
        *Problems? Please contact*: hytang2@illinois.edu \n
        *Date* 2026-02-11 \n
        *FormatAllowed* currently just grib, in near future can support cdf
        
        :param task_name: name of the task, required e.g. plot_wind_vector_field
        :param data_paths: a dictionary in the form name_of_dataset -> path_to_dataset
        :param projection: type of projection using cartopy.crs
        :param frame_dir: the output directory for frame output used for later animation
        :param animate_dir: the output directory for final animation
        :param time_steps: dict that maps name of climate var to number of time steps
        """
        self.datasets = {}
        self.size = len(data_paths)
        self.task_name = task_name
        self.time_steps = time_steps
        print(f"[Visualize-LOG] Creating a new visualize class for taks {task_name} with {self.size} climate variables")
        self.projection = projection
        #create a directory for this task with the name as task_name
        self.out_dir = os.path.join(outputs_dir, task_name)
        self.create_dir(self.out_dir)
        
        if(mode != 'scalar' and mode != 'vector') : raise RuntimeError("[Visualize-ERROR] Mode not supported !")
        else : self.mode = mode
        
        #creating frame and anim dir respectively
        self.frame_dir : str = os.path.join(self.out_dir, "frame")
        self.anim_dir : str = os.path.join(self.out_dir, "animation")
        self.create_dir(self.frame_dir)
        self.create_dir(self.anim_dir)
        for data_name, data_path in data_paths.items(): 
            print(f"[Visualize-LOG] Preparing dataset for {data_name}")
            ds : xr.DataArray = xr.open_dataset(data_path, engine="cfgrib") #open dataset
            time_steps = self.time_steps
            self.datasets[data_name] = DataSet(ds, time_steps, data_name)
    
    def set_cartopy(self, ax):
        ax.coastlines()
        ax.gridlines()
        ax.add_feature(cfeature.LAKES, linewidth=0.8, edgecolor="black")
        ax.add_feature(cfeature.RIVERS, linewidth=0.8, edgecolor="black")
        
    def plot_scalar_and_save(self, Y, X, Z, time, title):
        """
        Plot a scalar field on the meshgrid X, Y
        """
        print(f"[Visualize LOG] Plotting frame in scalar mode at timestep {time}")
        plt.close()
        fig, ax = plt.subplots(subplot_kw={"projection": self.projection}, figsize=(10, 6))
        pc = ax.pcolormesh(
            X,
            Y,
            Z,
            shading='auto',
            transform=self.projection,
            cmap="Spectral_r",
        )
        fig.colorbar(pc, ax=ax, orientation="horizontal", pad=0.2) #draw colorbar for pcolormesh into ax 
        self.set_cartopy(ax)
        title = title + f"at timestep {time}"
        ax.set_title(title)
        path = os.path.join(self.frame_dir , str(time)) + ".png"
        plt.savefig(path)
        
    def magnitude(self, U, V, ):
        U = U.to_numpy()
        V = V.to_numpy()
        return xr.DataArray(np.sqrt(U ** 2 + V ** 2))
        
    def plot_vector_and_save(self, Y, X, U, V, time, title):
        print(f"[Visualize LOG] Plotting frame in vector mode at timestep {time}")
        plt.close()
        fig, ax = plt.subplots(subplot_kw={"projection": self.projection}, figsize=(20, 12))
        mag = self.magnitude(U,V)
        Q = ax.quiver(X, 
                      Y, 
                      U, 
                      V,
                      mag,
                      width =  1e-3,
                      scale= 2.5, 
                      scale_units='xy', 
                      angles='xy',
                      transform=self.projection,
                      cmap="Spectral_r")
        self.set_cartopy(ax)
        title = title + f"at timestep {time}"
        ax.set_title(title, fontsize=20)
        fig.colorbar(Q, ax=ax, orientation="horizontal", shrink = 0.7, label="magnitude") #draw colorbar for pcolormesh into ax 
        path = os.path.join(self.frame_dir , str(time)) + ".png"
        plt.savefig(path)
        
        
    def populate_frame(self, lat=None, lon=None, dlat=None, dlon=None, title=None):
        if(self.mode == 'scalar'):
            if(len(self.datasets.keys()) != 1) : raise RuntimeError("[Visualizer-ERROR] Incorrect number of datasets for scalar mode")
            data_name = (self.datasets.keys())[0]
            print(f"[Visualize LOG] Populating for the scalar climate variable {data_name}")
            ds = self.datasets[data_name]
            for time in range(ds.time_steps): 
                lat_mesh, lon_mesh, varmesh = ds.getMesh(time, lat, lon, dlat, dlon) #get meshes
                self.plot_scalar_and_save(lat_mesh, lon_mesh, varmesh, time=time, title=title)
        else:
            if(len(self.datasets.keys()) != 2) : raise RuntimeError("[Visualizer-ERROR] Incorrect number of datasets for vector mode")
            u_name = list(self.datasets.keys())[0] 
            v_name = list(self.datasets.keys())[1] 
            print(f"[Visualize LOG] Populating for the vector climate variable ({u_name},{v_name})")
            u, v = self.datasets[u_name], self.datasets[v_name]
            for time in range(self.time_steps): 
                coarsen_factor = 12
                lat_mesh, lon_mesh, U = u.getMesh(time, lat, lon, dlat, dlon, coarsen_factor)
                _, _, V = v.getMesh(time, lat, lon, dlat, dlon, coarsen_factor)
                self.plot_vector_and_save(lat_mesh, lon_mesh, U, V, time, title)
            
        
    def animate_from_frames(self):
        images = []
        for i in range(self.time_steps) :
            ith_path = os.path.join(self.frame_dir, (str(i) + ".png"))
            images.append(imageio.imread(ith_path))

        # Save as an animated GIF
        output_gif_path = os.path.join(self.anim_dir, (self.task_name + ".gif"))
        imageio.mimsave(output_gif_path, images, fps=5)   
        print(f"[Visualize-LOG] Animation saved as {output_gif_path}") 
          
if __name__ == "__main__":
    #usage example : 
    output_path = "/data/keeling/a/hytang2/Climate_System_ATMS507/Main/HWs/HW2/outputs"
    
    data_paths = {
        "u100" : "/data/keeling/a/hytang2/Climate_System_ATMS507/Main/HWs/HW2/data/wind_vector_field/100m_u_component_of_wind.grib",
        "v100" : "/data/keeling/a/hytang2/Climate_System_ATMS507/Main/HWs/HW2/data/wind_vector_field/100m_v_component_of_wind.grib"
    }
    time_steps = 24
    vs = Visualize(task_name="wind_vector_field", mode='vector', data_paths = data_paths, outputs_dir=output_path, time_steps=time_steps)
    vs.populate_frame(title="uv wind field at 100m 2026-2-5")
    vs.animate_from_frames()