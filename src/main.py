import src.class_vessel_coordinator as vc
import src.class_draggable_rectangle as drect
import src.common as common
import shapely.geometry as sgeom
import pickle
import matplotlib.pyplot as plt, cartopy
import src.class_time_keeper as tk
import sys
cartopy.config['pre_existing_data_dir ']='\\cache'

# test plot
# fig2,ax2= plt.subplots(subplot_kw={'projection': cartopy.crs.PlateCarree()}, figsize=(30, 30))

# region Initial parameters
my_time_keeper = tk.timekeeper()
grid_block_size_degrees = 30
scriptfilepath = common.get_calling_script_directory_path(sys)
logFilePath = scriptfilepath + r'\geometric_operation_log.txt'
vc_pickle_file = scriptfilepath + r'\\cache\\vc_'+ str(grid_block_size_degrees) + '_degree.pickle'

# Configure cache parameters
recreate_cache = True
save_vc = True
load_vc_from_file = False


#endregion

#region Events
def onclick(event):
    print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
          ('double' if event.dblclick else 'single', event.button,
           event.x, event.y, event.xdata, event.ydata))

#endregion
if __name__ == '__main__':

    # region Initialize all class objects
    my_time_keeper.start_timing_event(event_name='main')

    if recreate_cache == True:
        # Initialize vessel coordinator - a complex class that initializes the earth and map artist
        my_vc = vc.Vessel_Coordinator(grid_block_size_degrees=grid_block_size_degrees,recreate_cache_boolean=True)
    # else:
    # my_vc = vc.Vessel_Coordinator(grid_block_size_degrees=grid_block_size_degrees,recreate_cache_boolean=False)


    if save_vc:
        # region Save to pickle operation
        my_time_keeper.start_timing_event(event_name='Save vc to pickle file')
        with open(vc_pickle_file, 'wb') as handle:
            pickle.dump(my_vc, handle, protocol=pickle.HIGHEST_PROTOCOL)
        my_time_keeper.stop_timing_event(event_name='Save vc to pickle file')
        # endregion

    if load_vc_from_file:
        my_time_keeper.start_timing_event(event_name='Loading vc from pickle file')
        with open(vc_pickle_file, 'rb') as handle:
            my_vc = pickle.load(handle)
        my_time_keeper.stop_timing_event(event_name='Loading vc from pickle file')
    #endregion

    #region Connect all event functions to figure canvas
    gl = my_vc.my_map_artist.ax.gridlines(crs=cartopy.crs.PlateCarree(), linewidth=0.5, color='gray', alpha=0.8,
                                          linestyle='-', draw_labels=True)
    drect.fig = my_vc.my_map_artist.fig
    cid = my_vc.my_map_artist.fig.canvas.mpl_connect('button_press_event', onclick)

    my_time_keeper.stop_timing_event(event_name='main')

    vessel_optimized_track = my_vc.get_optimal_route((30,-70),(0,85))
    my_vc.my_map_artist.plot_vessel_track(vessel_optimized_track,'C Valentine')
    vessel_optimized_track = my_vc.get_optimal_route((20, 140), (-20, -90))
    my_vc.my_map_artist.plot_vessel_track(vessel_optimized_track, 'Minerva Pisces')
    vessel_optimized_track = my_vc.get_optimal_route((0, 85), (44, 156))
    my_vc.my_map_artist.plot_vessel_track(vessel_optimized_track, 'Long Island')
    my_vc.my_map_artist.save_plot(scriptfilepath + r'/vessel-route.png')
    my_vc.my_map_artist.display()

