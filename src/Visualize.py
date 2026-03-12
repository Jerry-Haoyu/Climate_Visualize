import xarray as xr
from matplotlib import animation 
import matplotlib.pyplot as plt 

import imageio.v2 as imageio 

import numpy as np
import numpy.typing as npt
import os

import tqdm


import cartopy.crs as ccrs
import cartopy.feature as cfeature

import DateMap
import DataSet

            
class Visualize():
    def create_dir(self, dir):
        try : 
            os.mkdir(dir)
            print(f"[Visualize-LOG] Directory '{dir}' created")
        except FileExistsError : 
            print(f"[Visualize-LOG] Directory '{dir}' already exists")
            
    def __init__(self, 
                task_name : str, 
                dataset : DataSet,
                outputs_dir, 
                projection = ccrs.PlateCarree()
                ):
        self.dataset = dataset
        self.projection = projection
        #create a directory for this task with the name as task_name
        self.out_dir = os.path.join(outputs_dir, task_name)
        self.create_dir(self.out_dir)
        self.task_name = task_name
        
        #creating frame and anim dir respectively
        self.frame_dir : str = os.path.join(self.out_dir, "frame")
        self.anim_dir : str = os.path.join(self.out_dir, "animation")
        self.create_dir(self.frame_dir)
        self.create_dir(self.anim_dir)

    
    def set_cartopy(self, ax):
        ax.coastlines()
        ax.gridlines()
        ax.add_feature(cfeature.LAKES, linewidth=0.8, edgecolor="black")
        ax.add_feature(cfeature.RIVERS, linewidth=0.8, edgecolor="black")
        
        
    def decorate_and_save(self, object, fig, ax, time, title):
        title = title + " " + self.dataset.date_map.getTime(time_step = time) + f"({self.dataset.unit})"
        ax.set_title(title, fontsize=40)
        if self.dataset.mode == 'vector':
            cbar = fig.colorbar(object, ax=ax, orientation="horizontal", fraction=0.05)
            cbar.set_label("Magnitude", size=30) 
            cbar.ax.tick_params(labelsize=30) 
            cbar.ax.set_xscale('linear') 
        else :
            cbar = fig.colorbar(object, ax=ax, orientation="horizontal", fraction=0.05, ticks=np.linspace(self.dataset.smin, self.dataset.smax, 5))
            cbar.set_label(self.dataset.s_name, size=30) 
            cbar.ax.tick_params(labelsize=30) 
            cbar.ax.set_xscale('linear') 
        path = os.path.join(self.frame_dir , str(time)) + ".png"
        plt.savefig(path)
        
        
    def plot_scalar_and_save(self, time, Y, X, Z, title):
        """
        Plot a scalar field and save in output 
        
        :param Y: latitude
        :param X: longitude
        :param Z: The scalar field
        :param time: The time step
        :param title: Title for the plot
        """
        plt.close()
        ratio = len(Y)/len(X)
        figsize = (20, int(20 * ratio))
        fig, ax = plt.subplots(subplot_kw={"projection": self.projection}, figsize=figsize, layout="constrained")
        pc = ax.pcolormesh(
            X,
            Y,
            Z,
            shading='auto',
            transform=self.projection,
            norm=self.dataset.scalar_normalizer, 
            cmap="Spectral_r",
        )
        self.set_cartopy(ax)
    
        self.decorate_and_save(pc, fig, ax, time, title)
        
    def magnitude(self, U, V, ):
        U = U.to_numpy()
        V = V.to_numpy()
        return xr.DataArray(np.sqrt(U ** 2 + V ** 2))
        
    def plot_vector_and_save(self, time, Y, X, U, V, title):
        plt.close()
        fig, ax = plt.subplots(subplot_kw={"projection": self.projection}, figsize=figsize, layout="constrained")
        
        mag = self.magnitude(U,V)
        Q = ax.quiver(X, 
                      Y, 
                      U, 
                      V,
                      mag,
                      width = 1e-3,
                      scale= 2.5, 
                      scale_units='xy', 
                      angles='xy',
                      transform=self.projection,
                      cmap="Spectral_r")
        self.set_cartopy(ax)
        self.decorate_and_save(Q, fig, ax, time, title)

        
    def populate_frame(self, lat=None, lon=None, dlat=None, dlon=None, title=None):
        print(f"[Visualize LOG] Plotting frame in {self.dataset.mode} mode")
        for t in tqdm.tqdm(range(self.dataset.time_steps)):
            if self.dataset.mode == 'vector':   
                latmesh, lonmesh, Umesh, Vmesh = self.dataset.getMesh(lat, lon, dlat, dlon, t)
                self.plot_vector_and_save(t, latmesh, lonmesh, Umesh, Vmesh, title)
            elif self.dataset.mode == 'scalar':
                latmesh, lonmesh, Smesh = self.dataset.getMesh(lat, lon, dlat, dlon, t)
                self.dataset.computeNormalizerForScalar(lat, lon, dlat, dlon)
                self.plot_scalar_and_save(t, latmesh, lonmesh, Smesh, title)
            else:
                raise RuntimeError("No such mode")
        
    def animate_from_frames(self, fps=5):
        images = []
        for i in range(self.dataset.time_steps) :
            ith_path = os.path.join(self.frame_dir, (str(i) + ".png"))
            images.append(imageio.imread(ith_path))

        # Save as an animated GIF
        output_gif_path = os.path.join(self.anim_dir, (self.task_name + ".gif"))
        imageio.mimsave(output_gif_path, images, fps=fps)   
        print(f"[Visualize-LOG] Animation saved as {output_gif_path}")
    
    def plot_time_series(self, lat=None, lon=None, dlat=None, dlon=None, title : str | None =None):
        if(self.dataset.mode != 'scalar'): 
            raise RuntimeError("[Visualize ERROR] time-series plot only allowed for scalar climate varialbe")
        unit = self.dataset.unit 
        time_unit = self.dataset.time_unit
        time_series = self.dataset.getSpatialAveragedTimeSeries(lat, lon, dlat, dlon)
        fig, ax = plt.subplots(figsize=(20,5)) 
        if(title != None) : ax.set_title(title)
        ax.set_ylabel(rf"{self.dataset.s_name} ({unit})")
        ax.set_xlabel(rf"time steps ({time_unit})")
        T = np.arange(0, self.dataset.time_steps)
        print("length of T is", len(T))
        print("length of time_seires is", len(time_series))
        ax.plot(T, time_series)
        ax.set_xticks(np.arange(0, self.dataset.time_steps, 12))
        out_path = os.path.join(self.frame_dir, self.task_name)
        plt.savefig(out_path)
        
        
          
