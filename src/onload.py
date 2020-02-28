import src.class_vessel_coordinator as vc
import src.common as common
import shapely.geometry as sgeom
import pickle
import matplotlib.pyplot as plt, cartopy
import src.class_time_keeper as tk
import sys
import cartopy.crs as ccrs

my_vc = None
# test plot
# fig2,ax2= plt.subplots(subplot_kw={'projection': cartopy.crs.PlateCarree()}, figsize=(30, 30))

# region Initial parameters
my_time_keeper = tk.timekeeper()
grid_block_size_degrees = 5
scriptfilepath = common.get_calling_script_directory_path(sys)
logFilePath = scriptfilepath + r'\geometric_operation_log.txt'
vc_pickle_file = scriptfilepath + r'\cache\vc_'+ str(grid_block_size_degrees) + '_degree.pickle'

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

def onload():
    # region Initialize all class objects
    my_time_keeper.start_timing_event(event_name='main')
    print('boolean flags' + str(recreate_cache) + str(save_vc) + str(load_vc_from_file))
    my_vc = None
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
    # gl = my_vc.my_map_artist.ax.gridlines(crs=cartopy.crs.PlateCarree(), linewidth=0.5, color='gray', alpha=0.8,
    #                                       linestyle='-', draw_labels=True)

    my_vc.my_map_artist.fig, my_vc.my_map_artist.ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(30, 30))
    my_vc.my_map_artist.show_polygon_geometries_on_map(my_vc.e1.union_all_water_features, '#A6CAE0')
    my_vc.my_map_artist.show_polygon_geometries_on_map(my_vc.e1.union_all_non_water_features, '#8B969A')
    my_vc.my_map_artist.save_plot('pages/savedplot.png')
    # my_vc.my_map_artist.show_edges_on_map(my_vc.e1.list_of_all_sea_mesh_edges, 'white')
    # my_vc.my_map_artist.display()
    return my_vc




