import src.class_earth
import src.class_map_artist as mapart
import src.class_time_keeper as tk
import src.vessel_route_routing_algorithm as vra
import cartopy.crs as ccrs
import shapely.geometry as sgeom
import src.common as common
import sys
import pickle
import os.path
import matplotlib.pyplot as plt

scriptfilepath = common.get_calling_script_directory_path(sys)
logFilePath = scriptfilepath + r'\geometric_operation_log.txt'
my_tk = tk.timekeeper()
# import katana_geom_split as katana
def onclick(event):
    print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
          ('double' if event.dblclick else 'single', event.button,
           event.x, event.y, event.xdata, event.ydata))



class Vessel_Coordinator():
    def __init__(self,**kwargs):
        # Grab kwargs
        grid_block_size_degrees = kwargs.get('grid_block_size_degrees',1)
        recreate_cache_boolean = kwargs.get('recreate_cache_boolean', True)
        pickled_edgelist_filepath = scriptfilepath + '\cache\lines_' + str(grid_block_size_degrees) + '.pickle'

        # region Instantiate vc objecs from vc class, initialize parameters in constructor
        # Create earth object, which is essentially the geographic map, with a grid interval argument
        e1 = src.class_earth.Earth(grid_block_size_degrees)
        # Create a map artist, which helps to plot objects on the earth object map
        my_map_artist = mapart.map_artist()

        # Create new time keeper
        my_time_keeper = tk.timekeeper()
        # endregion

        # region Create sea mesh by filtering out non-water nodes from the grid
        my_time_keeper.start_timing_event(event_name='Preparation of mesh and geometries')

        # Check if lines file exist
        if os.path.isfile(pickled_edgelist_filepath):
            edgelist_exists = True
        # Depending on whether the flag is true or false, we may/may not recreate cache of list_of_edgelinestrings
        list_of_edgelinestrings = []
        if recreate_cache_boolean or not edgelist_exists:
            my_time_keeper.start_timing_event(event_name='Recreating list of linestrings')
            # Get generator that returns row by row, all geo edges post stitch and their corresponding line strings
            all_geo_edges_after_stitching_linestrings_generator = e1.get_all_poststitch_geo_edges_linestring_generator()
            # Loop through all edges and corresponding edge linestrings
            for edge_linestring, edge in all_geo_edges_after_stitching_linestrings_generator:
                list_of_edgelinestrings.append(edge_linestring)
            # region Save to pickle operation
            with open(pickled_edgelist_filepath, 'wb') as handle:
                pickle.dump(list_of_edgelinestrings, handle, protocol=pickle.HIGHEST_PROTOCOL)
            # endregion
            print('All geo edges saved to ' + pickled_edgelist_filepath)
            my_time_keeper.stop_timing_event(event_name='Recreating list of linestrings')

        else:
            my_time_keeper.start_timing_event(event_name='Loading linestrings list from pickle file')
            with open(pickled_edgelist_filepath, 'rb') as handle:
                list_of_edgelinestrings = pickle.load(handle)
            my_time_keeper.stop_timing_event(event_name='Loading linestrings list from pickle file')


        # Load the pickled edgelist from hard disk, and run a spatial join between marine polygons and all lines to find which ones are within
        e1.create_sea_mesh_edges_and_geoms(list_of_edgelinestrings)  # derived from excluding intersecting geo nodes with non water polys

        # Show the pickled lines on map
        e1.create_sea_mesh_nodes_set()  # used for quantization of input location
        self.add_custom_canal_edges(e1) #add custom canal edges to sea mesh adjacency list ie list_of_all_sea_mesh_edges

        my_map_artist.show_polygon_geometries_on_map(e1.union_all_water_features,'#A6CAE0')

        my_map_artist.show_polygon_geometries_on_map(e1.union_all_non_water_features,'#8B969A')

        # endregion

        # region Remove imaginary sea mesh edges for plotting
        # Operational list of sea mesh edges, contains imaginary edges, that when plotted, does not make any sense
        # Therefore we exclude the imaginary edges from the list before passing it to artist for plotting
        # my_map_artist.show_edges_on_map(e1.list_of_all_sea_mesh_edges, 'white')
        cosmetic_list_of_sea_mesh_edges = [edge for edge in e1.list_of_all_sea_mesh_edges if
                                           edge not in e1.list_of_imaginary_stitch_edges]
        # my_map_artist.show_edges_on_map(cosmetic_list_of_sea_mesh_edges, 'white')


        # endregion

        # region Plot sea mesh edges , temporarily disabled
        # my_map_artist.show_edges_on_map(cosmetic_list_of_sea_mesh_edges, 'yellow')
        my_time_keeper.stop_timing_event(event_name='Preparation of mesh and geometries')

        self.e1 = e1
        self.my_map_artist = my_map_artist
        self.my_time_keeper = my_time_keeper

    def get_optimal_route(self,start_node,end_node):


        # region Begin routing
        # Pass in start and end node and the entire adjacency list of the grid and run the Dijkstra algorithm
        # Algorithm returns 1) Total distance (ie cost) and
        # 2) The shortest path in the form of a list of lists of point pairs
        # Quantization performed on input to ensure input is valid

        # Quantize start and end node and plot them
        start_node = self.e1.quantized_coord_using_grid(start_node[0],start_node[1])
        end_node = self.e1.quantized_coord_using_grid(end_node[0], end_node[1])

        self.my_time_keeper.start_timing_event(event_name='Vessel routing optimization operation')

        cost, came_from_list = vra.dijkstra(self.e1.list_of_all_sea_mesh_edges, start_node, end_node)
        # Exit program if no solution is found ie cost is None
        if cost is None:
            print('Solution not found by routing algorithm, please check log for details of routing error.')
            self.my_time_keeper.stop_timing_event(event_name='Vessel routing optimization operation')
            exit()
        else:
            print('Optimized shortest route distance using Dijkstra Algorithm is :' + "{:,}".format(round(cost, 0)) + ' km')

        # endregion

        # region Output routing results

        # Create journey complete flag
        journey_complete = False

        # Populate the track beginning from the end node, find the previous node, and chain them up
        journey_track = [end_node]

        while journey_complete == False:
            previous_node = came_from_list[end_node]
            journey_track += [previous_node]
            # Once you work backwards and hit the start node, the track is completed
            if previous_node == start_node:
                journey_complete = True
            else:
                end_node = previous_node
        # Reverse the list to show track from start node to end node
        journey_track.reverse()
        print('Optimal Track:' + (str(journey_track)))

        # Returns an ordered list of latlon points
        return journey_track
        # endregion

    def add_custom_canal_edges(self,e1):

        #region Straits of Bosporus
        canal_name = 'strait of bosporus'
        canal_line_coord_list = [(41,29), (41.03,29.02),(41.235,29.1),(41.5, 29.25)]
        e1.add_canal_edge_after_mesh_and_qnodes_created(canal_name,canal_line_coord_list)

        canal_name = 'strait of dardanelles'
        canal_line_coord_list = [(40,26), (40.04,26.2),(40.09,26.33),(40.22,26.47),(40.43,26.75),(27,40.5)]
        e1.add_canal_edge_after_mesh_and_qnodes_created(canal_name,canal_line_coord_list)

        canal_name = 'panama canal'
        canal_line_coord_list = [(9.25,-80), (9,-79.5)]
        e1.add_canal_edge_after_mesh_and_qnodes_created(canal_name,canal_line_coord_list)

        print('Vessel coordinator added '+canal_name+' edges to list of sea mesh edges during its init.')
        #endregion