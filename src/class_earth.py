from geographiclib.geodesic import Geodesic
from shapely.prepared import prep
from shapely.ops import unary_union
import src.class_map_artist as mapart
import sqlite3
import numpy as np
import shapely.geometry as sgeom
import cartopy.io.shapereader as shpreader
import src.katana_geom_split as katana_geom_split
import matplotlib.pyplot as plt, cartopy
import src.class_time_keeper as tk
import sys
import src.common as common
import geopandas as gpd
import pandas as pd
import cartopy.crs as crs
from geopandas import GeoDataFrame, GeoSeries, read_file
from geopandas.tools import sjoin
from shapely.ops import cascaded_union

import pickle

scriptfilepath = common.get_calling_script_directory_path(sys)
logFilePath = scriptfilepath + r'\geometric_operation_log.txt'
# import katana_geom_split as katana

class Earth():
    def __init__(self, grid_block_size_degrees):

        # Initialize file names and variables
        self.block_size = grid_block_size_degrees
        self.marine_polys_filename = scriptfilepath + r'\shapefiles\ne_10m_geography_marine_polys.shp'
        self.rivers_lake_centerlines_filename = scriptfilepath + r'\shapefiles\ne_50m_rivers_lake_centerlines.shp'
        self.land_polys = scriptfilepath + r'\shapefiles\ne_110m_land.shp'


        # Create earth grid generator
        earth_grid_generator = self.create_earth_grid_generator(grid_block_size_degrees)
        self.tiled_edges_list = list(earth_grid_generator)
        self.global_right_vertical_nodes =[]
        self.global_bottom_horizontal_nodes = []
        self.global_left_vertical_nodes =[]
        self.global_top_horizontal_nodes = []
        self.part_composite_hor_bottom_edges = []
        self.part_composite_ver_right_edges = []
        self.part_composite_hor_bottom_reversed_edges = []
        self.part_composite_ver_right_reversed_edges = []

        # Create boundary geographical nodes ie the perimeter of the world map
        self.create_boundary_nodes()

        # Create bottom and right boundary
        self.create_bottom_and_right_boundary_edges()
        self.all_geo_edges_before_stitching = self.tiled_edges_list + self.part_composite_hor_bottom_edges \
                                              + self.part_composite_ver_right_edges + \
                                              self.part_composite_hor_bottom_reversed_edges + \
                                              self.part_composite_ver_right_reversed_edges

        self.all_geo_edges_after_stitching = []
        self.list_of_imaginary_stitch_edges = []

        # Stitch all geographic nodes together
        self.stitch_geo_boundaries()
        self.global_distinct_nodes_list = []
        self.create_global_nodes_set()
        self.list_of_all_sea_mesh_edges = []
        self.list_of_all_sea_mesh_geometries =[]
        self.union_all_water_features = None
        self.union_all_non_water_features = None
        self.global_distinct_sea_mesh_nodes_list = []
        self.canal_edges_list = []


    @staticmethod
    def apply_linear_transform_to_from_node(x, y, from_node):
        # apply y transform to lat, and x transform to lon
        to_node = (round(from_node[0] + y, 2), round(from_node[1] + x, 2))
        # Validate new lat and lons, set node to none if lat or lons are invalid
        if to_node[0] < -90 or to_node[0] > 90 or to_node[1] < -180 or to_node[1] > 180:
            to_node = None
        return to_node

    @staticmethod
    def calc_geo_dist_km(PointALat, PointALon, PointBLat, PointBLon):
        geod = Geodesic.WGS84
        geod_result_dict = geod.Inverse(PointALat, PointALon, PointBLat, PointBLon)
        distance_in_km = (geod_result_dict['s12'] / 1000)
        return distance_in_km

    def quantized_coord_using_grid(self,input_latitude,input_longitude):
        # Function takes in a an input coord, and finds the nearest point in grid relative to the input coord
        # Convert node list to np array
        npa_all_nodes = np.asarray(self.global_distinct_sea_mesh_nodes_list, dtype=np.float32)
        # Use np to find min abs distance and hence the nearest lat in terms of degrees
        nearest_lat_index = (np.abs(npa_all_nodes[:,0]-input_latitude)).argmin()
        # Get the actual latitude using the returned index
        nearest_lat = npa_all_nodes[nearest_lat_index][0]

        # Get a list of all the coords with the above lat
        filtered_coords_by_lat  = [(lat, lon) for (lat, lon) in self.global_distinct_sea_mesh_nodes_list if round(lat-nearest_lat,0) == 0]
        # Convert the list with above lat, into np array for same purpose
        filtered_coords_by_lat_ndarray = np.asarray(filtered_coords_by_lat, dtype=np.float32)
        # Use np function to find nearest longitude (from min abs difference), : means all rows, 1 means 2nd column of ndarray
        nearest_lat_lon_index = (np.abs(filtered_coords_by_lat_ndarray[:,1]-input_longitude)).argmin()
        actual_nearest_lat_lon = filtered_coords_by_lat_ndarray[nearest_lat_lon_index]

        # Assign result to tuple and return it
        quantized_coord_tuple = actual_nearest_lat_lon[0],actual_nearest_lat_lon[1]

        return quantized_coord_tuple

    def create_earth_grid_generator(self,block_size):
        geo_nodes_db_path=''
        addition_counter = 0
        # conn = sqlite3.connect(geo_nodes_db_path)
        # cursor = conn.cursor()
        # Set the first lat and lon for the grid
        temp_lat = -90
        temp_lon = -180

        # Overwrite object block size if already set and prompt a warning
        self.block_size = block_size
        if self.block_size != None:
            print('Caution: Earth object already has a block size set. Method block size argument will supersede and '
                  'overwrite Earth object block size.')
        else:
            self.block_size = block_size

        lon_count = int(360 / block_size)
        lat_count = int(180 / block_size)

        # Use BEGIN to allow sqlite cursor to start accepting insert statement executions
        # cursor.execute('BEGIN')
        # cursor.execute('Delete FROM geo_nodes_table')
        # cursor.execute('COMMIT')

        # print('state' + str(temp_lat) + str(temp_lon))

        # Vector projection, loop to create set of vectors repetitively shaped like square root of x
        # Shape is used to tile the grid, this way of writing reduces code and improves readability
        # Close the earth grid right vertical and bottom horizontal boundaries separately after tiling

        for i in range(1, lat_count + 1):
            # x , y is normal 2d cartesian plane axis
            projection_A = (temp_lat, temp_lon)
            projection_B = Earth.apply_linear_transform_to_from_node(block_size, 0, projection_A)
            projection_C = Earth.apply_linear_transform_to_from_node(0, block_size, projection_A)
            projection_D = Earth.apply_linear_transform_to_from_node(block_size, block_size, projection_A)

            # Pre-calculate the constant actual distance in km to be used as weights for all of the edges in this row of tile
            top_horizontal_edge_dist = Earth.calc_geo_dist_km(projection_A[0], projection_A[1], projection_B[0],
                                                        projection_B[1])
            left_vertical_edge_dist = Earth.calc_geo_dist_km(projection_A[0], projection_A[1], projection_C[0],
                                                       projection_C[1])
            diagonal_edge_dist = Earth.calc_geo_dist_km(projection_A[0], projection_A[1], projection_D[0], projection_D[1])

            # Nested loop through all longitudes and tile in x axis direction
            for j in range(1, lon_count + 1):
                # Create normal "left-to-right" edges
                top_horizontal_edge = (projection_A, projection_B, top_horizontal_edge_dist)
                left_vertical_edge = (projection_A, projection_C, left_vertical_edge_dist)
                negative_diagonal_edge = (projection_A, projection_D, diagonal_edge_dist)
                positive_diagonal_edge = (projection_C, projection_B, diagonal_edge_dist)

                # Create reverse direction edges
                reverse_top_horizontal_edge = (projection_B, projection_A, top_horizontal_edge_dist)
                reverse_left_vertical_edge = (projection_C, projection_A, left_vertical_edge_dist)
                reverse_negative_diagonal_edge = (projection_D, projection_A, diagonal_edge_dist)
                reverse_positive_diagonal_edge = (projection_B, projection_C, diagonal_edge_dist)

                # create individual yield statements so that the generator object returns one object at a time
                # not advisable to yield all edges at once because they would return a list of objects every time
                # the generator next() is called, this would resulting in the generator returning list of objects
                # which have to be further chained and combined together using itertools later (waste of time)
                # To check the number of edges, find the number of squares given block size, then multiply that by
                # four, and take the result and multiply by two (both directions)
                yield top_horizontal_edge
                yield left_vertical_edge
                yield negative_diagonal_edge
                yield positive_diagonal_edge
                yield reverse_top_horizontal_edge
                yield reverse_left_vertical_edge
                yield reverse_negative_diagonal_edge
                yield reverse_positive_diagonal_edge

                # Increment longitude of Projection A
                temp_lon = round(temp_lon + block_size, 2)
                projection_A = (temp_lat, temp_lon)

                # Basis new projection A (new longitude), apply linear transformation to get new Point B,C and D
                projection_B = Earth.apply_linear_transform_to_from_node(block_size, 0, projection_A)
                projection_C = Earth.apply_linear_transform_to_from_node(0, block_size, projection_A)
                projection_D = Earth.apply_linear_transform_to_from_node(block_size, block_size, projection_A)

            # Reset temp longitude (Projection A) after loop through all discrete longitudes for given latitude
            temp_lon = -180

            # Increment latitude (Projection A) after loop through all discrete longitudes for given latitude
            temp_lat = round(temp_lat + block_size, 2)

    def create_boundary_nodes(self):
        #This function is used to create the vertical right and horizontal bottom edge, and then
        # also stitches the top-bottom horizontal and left-right boundaries together using zero cost edges

        lon_count = int(360 / self.block_size)
        lat_count = int(180 / self.block_size)

        temp_lat = -90
        temp_lon = -180


        # Most bottom left A point, project southwards by block size
        # bottom_left_most_point =

        global_right_vertical_nodes =[]
        global_bottom_horizontal_nodes = []
        global_left_vertical_nodes =[]
        global_top_horizontal_nodes = []


        # Create list of bottom boundary points
        for i in range(1, lat_count + 1):
            temp_lat = round(temp_lat + self.block_size, 2)
            if i == lat_count:
                for j in range(1, lon_count + 2):
                    global_bottom_horizontal_nodes.append((temp_lat,temp_lon))
                    temp_lon = round(temp_lon + self.block_size, 2)

        # Reset temporary variables
        temp_lat = -90
        temp_lon = -180

        # Create list of right boundary points
        for i in range(1, lon_count + 1):
            temp_lon = round(temp_lon + self.block_size, 2)
            if i == lon_count:
                for j in range(1, lat_count + 2):
                    global_right_vertical_nodes.append((temp_lat,temp_lon))
                    temp_lat = round(temp_lat + self.block_size, 2)


        # Derive left and top boundary points
        global_left_vertical_nodes = [(lat,-lon) for (lat,lon) in global_right_vertical_nodes]
        global_top_horizontal_nodes = [(-lat, lon) for (lat,lon) in global_bottom_horizontal_nodes]

        # Assign reference to object variables
        self.global_right_vertical_nodes  = global_right_vertical_nodes
        self.global_bottom_horizontal_nodes  = global_bottom_horizontal_nodes
        self.global_left_vertical_nodes = global_left_vertical_nodes
        self.global_top_horizontal_nodes = global_top_horizontal_nodes

    def create_bottom_and_right_boundary_edges(self):

        bottom_lon_distance_interval = self.calc_geo_dist_km(self.global_bottom_horizontal_nodes[0][0],
                                       self.global_bottom_horizontal_nodes[0][1],
                                       self.global_bottom_horizontal_nodes[1][0],
                                       self.global_bottom_horizontal_nodes[1][1])
        right_lat_distance_interval = self.calc_geo_dist_km(self.global_right_vertical_nodes[0][0],
                                       self.global_right_vertical_nodes[0][1],
                                       self.global_right_vertical_nodes[1][0],
                                       self.global_right_vertical_nodes[1][1])

        # Create global bottom edges in both directions
        previous_node = None
        for node in self.global_bottom_horizontal_nodes:
            if previous_node != None:
                self.part_composite_hor_bottom_edges.append((previous_node, node, bottom_lon_distance_interval))
                self.part_composite_hor_bottom_reversed_edges.append((node, previous_node, bottom_lon_distance_interval))
                previous_node = node
            else:
                previous_node = node

        # Create global right edges in both directions
        previous_node = None
        for node in self.global_right_vertical_nodes:
            if previous_node != None:
                self.part_composite_ver_right_edges.append((previous_node, node, right_lat_distance_interval))
                self.part_composite_ver_right_reversed_edges.append((node, previous_node, right_lat_distance_interval))
                previous_node = node
            else:
                previous_node = node

        a=0

    def stitch_geo_boundaries(self):
        # Stitching involves creating edges to make the boundaries of the earth seamless
        # from a graph point of view
        # Stitched edges have zero cost as technically e.g. -90,180  and -90,-180 is the one and same location


        # Top-bottom stitch (deprecated due to incorrect geographic logic)
        # Zip top and bottom tuples horizontally into a single list of tuples
        # combined_top_bottom_stitchedge_tuples_list = list(
        #     zip(self.global_top_horizontal_nodes, self.global_bottom_horizontal_nodes))
        # # create stitch edges
        # stitch_top_bottom_edges_list = [(top_boundary_node, bottom_boundary_node, 0) for
        #                                 (top_boundary_node, bottom_boundary_node) in
        #                                 combined_top_bottom_stitchedge_tuples_list]
        #
        # stitch_top_bottom_edges_reversed_list = [(bottom_boundary_node, top_boundary_node, 0) for
        #                                 (top_boundary_node, bottom_boundary_node) in
        #                                 combined_top_bottom_stitchedge_tuples_list]

        # Zip left and right tuples horizontally into a single list of tuples
        combined_left_right_stitchedge_tuples_list = list(
            zip(self.global_left_vertical_nodes, self.global_right_vertical_nodes))
        # create stitch edges (removed)
        stitch_left_right_edges_list = [(left_boundary_node, right_boundary_node, 0) for
                                        (left_boundary_node, right_boundary_node) in
                                        combined_left_right_stitchedge_tuples_list]
        stitch_left_right_edges_reversed_list = [(right_boundary_node,left_boundary_node , 0) for
                                        (left_boundary_node, right_boundary_node) in
                                                 combined_left_right_stitchedge_tuples_list]

        # Keep and expose the imaginary stitches for use in geometric intersection comparison later
        # These automatically qualify to be valid sea mesh edges
        self.list_of_imaginary_stitch_edges += stitch_left_right_edges_list
        self.list_of_imaginary_stitch_edges += stitch_left_right_edges_reversed_list


        if len(self.global_left_vertical_nodes)!= len(self.global_right_vertical_nodes):
            print('Fatal Error: Left and right stitches do not have the same number of nodes!')

        self.all_geo_edges_after_stitching = self.all_geo_edges_before_stitching + \
                                             stitch_left_right_edges_list + stitch_left_right_edges_reversed_list

        num_of_lat_blocks = 180/self.block_size
        num_of_lon_blocks = 360 / self.block_size
        print('Block size used for earth object:' + str(self.block_size))
        print('Number of blocks in length:' + str(360/self.block_size))
        print('Number of blocks in height:' + str(180/self.block_size))

        theoretical_edges_required = ((num_of_lat_blocks*num_of_lon_blocks)*4)*2+(num_of_lat_blocks*2)+ \
                                     (num_of_lon_blocks*2) + (num_of_lat_blocks+1)*2

        total_edge_created_count = len(self.all_geo_edges_after_stitching)
        print('Total number of theoretical edges required is :' + str(theoretical_edges_required))
        print('Actual number of edges created: ' + str(total_edge_created_count))
        if theoretical_edges_required - total_edge_created_count == 0:
            print('Grid check passed!')
        else:
            print('Grid check failed!')

        a=0

    def create_global_nodes_set(self):
        from_node_list,to_node_list,distance = zip(*self.all_geo_edges_after_stitching)
        self.global_distinct_nodes_list = list(set(from_node_list + to_node_list))
        self.global_distinct_nodes_list = sorted(self.global_distinct_nodes_list)

    def create_sea_mesh_nodes_set(self):
        from_node_list,to_node_list,distance = zip(*self.list_of_all_sea_mesh_edges)
        self.global_distinct_sea_mesh_nodes_list = list(set(from_node_list + to_node_list))
        self.global_distinct_sea_mesh_nodes_list = sorted(self.global_distinct_sea_mesh_nodes_list)

    @staticmethod
    def point_is_on_water_feature(water_feature,x, y):
        return water_feature.contains(sgeom.Point(x, y))

    def get_all_poststitch_geo_edges_linestring_generator(self):
        # Generator to return line string geom objects of all geo edges after stitching
        for edge in self.all_geo_edges_after_stitching:
            # x is lon, y is lat, edge is lat lon format therefore switch places when passing edge tuple
            edge_linestring = sgeom.LineString([(edge[0][1],edge[0][0]), (edge[1][1],edge[1][0])])
            yield edge_linestring,edge

    def save_all_poststitch_geo_edges_linestring_to_pickle(self,**kwargs):
        pickle_objects_boolean = kwargs.get('pickle_objects_boolean',False)
        pickled_edgelist_filepath = kwargs.get('pickled_edgelist_filepath',None)

        # If vessel coordinator is initialized with true flag in pickle_grid_switch indicator
        if pickle_objects_boolean is True:
            linestring_list =[]
            # Get generator that returns row by row, all geo edges post stitch and their corresponding line strings
            all_geo_edges_after_stitching_linestrings_generator = self.get_all_poststitch_geo_edges_linestring_generator()
            # Loop through all edges and corresponding edge linestrings
            for edge_linestring,edge in all_geo_edges_after_stitching_linestrings_generator:
                linestring_list.append(edge_linestring)

            # region Save to pickle operation
            with open(pickled_edgelist_filepath, 'wb') as handle:
                pickle.dump(linestring_list, handle, protocol=pickle.HIGHEST_PROTOCOL)
            # endregion
            print('All geo edges saved to ' + pickled_edgelist_filepath)


    def perturb_top_and_right_edges(self,edge):
        # Optimized perturbation code
        # Only perturb edges with lat=90 or lon=180 , ie top and right edges
        if 90 in [int(edge[0][0]),int(edge[1][0])] or 180 in [int(edge[0][1]),int(edge[1][1])]:
            # Strip the two pairs of lat,lon from edge
            edge_point_a_lat = edge[0][0]
            edge_point_a_lon = edge[0][1]
            edge_point_b_lat = edge[1][0]
            edge_point_b_lon = edge[1][1]
            distance = edge[2]

            # Perturb edge data
            if edge_point_a_lat == 90:
                edge_point_a_lat = round(edge_point_a_lat - round(self.block_size/10,3),2)

            if edge_point_a_lon == 180:
                edge_point_a_lon = round(edge_point_a_lon - round(self.block_size/10,3),2)

            if edge_point_b_lat == 90:
                edge_point_b_lat = round(edge_point_b_lat - round(self.block_size/10,3),2)

            if edge_point_b_lon == 180:
                edge_point_b_lon = round(edge_point_b_lon - round(self.block_size/10,3),2)

            # Return perturbed edge and True flag for modified boolean (for top and right edges only)
            return ((edge_point_a_lat,edge_point_a_lon),(edge_point_b_lat,edge_point_b_lon),distance),True
        else:
            # Else return original edge and False flag for modified boolean (majority of the points)
            return edge, False

    def create_sea_mesh_edges_and_geoms(self,list_of_edgelinestrings):
        # Create new time keeper and debug map artist, debug map artist has to be commented out else you will see two charts
        my_time_keeper = tk.timekeeper()
        # my_debug_map_artist = mapart.map_artist()

        # Get shape file names using natural earth cartopy
        # marine_polys_filename = shpreader.natural_earth(resolution='ne_10m',
        #                                                 category='physical', name='geography_marine_polys')
        # rivers_lake_centerlines_filename = shpreader.natural_earth(category='physical', resolution='ne_10m',

        #Create empty lists to hold the water geoms                                                            name='rivers_lake_centerlines')
        list_of_river_buffered_lines_polys = []
        list_of_marine_polys_positive_buffered = []

        # region Use cartopy shapereader to read all geometries into a list
        list_of_marine_polygons = list(
            shpreader.Reader(self.marine_polys_filename).geometries())  # returns all polys representing oceans and seas
        list_of_river_geometries = list(shpreader.Reader(
            self.rivers_lake_centerlines_filename).geometries())  # returns multilinestring representing rivers
        list_of_land_polygons = list(shpreader.Reader(
            self.land_polys).geometries())  # returns multilinestring representing rivers

        #endregion

        #region Buffer rivers, lakes and centrelines, to create polygons for testing intersection
        # One degree grid points can only be tested against polygons. This requirement is satisfied by marine polygons but
        # rivers_lakes_centerlines features are multilinestrings (container for single linestrings) and thus grid points cannot be
        # tested against rivers
        # Rivers geometric representation must now be converted from multi linestring basis to polygon basis
        # This is done via creation of new polygons via the use of linestring.buffer method(width integer). Buffer method creates
        # rivers by using the river linestrings as centroids and creating a polgyon that buffers the actual line by the number of
        # non-distance units specified the the integer
        # Loop through multilinestrings in list_of_river_geometries and create line "tracks" list list_of_river_buffered_lines_polys
        # apply negative buffer to speed up unary union
        for river_line in list_of_river_geometries:
            if isinstance(river_line, sgeom.multilinestring.MultiLineString):
                list_of_river_buffered_lines_polys.append(river_line.buffer(0.5))

        # apply negative buffer to speed up unary union
        for marine_polygon in list_of_marine_polygons:
            if isinstance(marine_polygon, sgeom.multipolygon.MultiPolygon):
                list_of_marine_polys_positive_buffered.append(marine_polygon.buffer(0))

        # Previously tried to apply negative buffer to marine polygons to buffer coastlines against vessel
        # It did not work as marine polygons are many distinct polygons and the negative buffering
        # shrunk the marine polygons, creating gaps in between water bodies which posed a problem
        # when performing sea mesh intersection with the grid

        #endregion

        # Consolidate water geoms into one single list
        final_water_features_geom_list = list_of_marine_polygons + list_of_river_buffered_lines_polys

        # region Union all marine polygons and rivers lakes centrelines (final water features)
        print('Commencing union of water geometries...')
        my_time_keeper.start_timing_event(event_name='Union water geometries operation')
        # Union all water features into a single geometry object
        union_all_water_features_geom = unary_union(final_water_features_geom_list)
        my_time_keeper.stop_timing_event(event_name='Union water geometries operation')
        print('Union of water geometries complete.')
        #endregion


        # region Union all land polygons
        print('Commencing union of land geometries...')
        my_time_keeper.start_timing_event(event_name='Union land geometries operation')
        # Union all water features into a single geometry object
        union_all_land_features_geom = unary_union(list_of_land_polygons)
        my_time_keeper.stop_timing_event(event_name='Union land geometries operation')
        print('Union of land features geometries complete.')
        #endregion


        # region Derive non-water polygons from final water features

        # Derive non-water polygons by taking world map difference union all water features
        # Use non-water polygons to test against geo nodes post stitch for sea mesh.
        # DO NOT use water polygons to test for sea mesh, valid edges at the perimeter of world map wil be lost


        a = 180
        b = 90
        gap = 0
        exterior_ring = [(-a - gap, -b - gap), (-a - gap, b + gap), (a + gap, b + gap), (a + gap, -b - gap),
                         (-a - gap, -b - gap)]
        world_map_polygon = sgeom.Polygon(exterior_ring)

        my_time_keeper.start_timing_event(event_name='Differencing out non-water polygons')
        union_non_water_polygons = world_map_polygon.difference(union_all_water_features_geom)
        my_time_keeper.stop_timing_event(event_name='Differencing out non-water polygons')
        print('Union_non_water_polygons geometry object created')
        #endregion

        self.union_all_water_features = union_all_water_features_geom
        self.union_all_non_water_features = union_non_water_polygons

        # region Prep union water features for intersection comparison
        my_time_keeper.start_timing_event(event_name='Prep operation on non-water polygons')
        prepped_union_all_non_water_features = prep(union_non_water_polygons)
        prepped_all_non_water_union = prepped_union_all_non_water_features
        my_time_keeper.stop_timing_event(event_name='Prep operation on non-water polygons')
        print('Prepping of of non water union geometries complete, ready to perform intersection test with edges')
        #endregion

        # Split union polygons using katana methodology to prepare for spatial intersection using R-tree

        split_union_non_water_features = katana_geom_split.katana(union_non_water_polygons,30)
        split_union_water_features = katana_geom_split.katana(union_all_water_features_geom, 30)


        # Debug charts for viewing the world map outside of map artist manager (which is only available in main.py)
        # my_debug_map_artist.show_polygon_geometries_on_map(union_non_water_polygons, 'green')
        # my_debug_map_artist.show_polygon_geometries_on_map(union_all_water_features_geom,'cyan')
        # my_debug_map_artist.show_polygon_geometries_on_map(union_non_water_polygons, 'red')


        #region begin debug

        # INTERSECTION CODE SEGMENT BEGINS

        #region Traditional shapely intersection comparison method to populate list_of_all_sea_mesh_edges
        #Shapely geometry filtering operation completed in 00 HOURS :06 MINUTES :55.72 SECONDS
        print('Shapely node filtering/intersection test for sea mesh commencing...')
        my_time_keeper.start_timing_event(event_name='Shapely geometry filtering operation')
        comparison_counter = 0
        # Get generator that returns row by row, all geo edges post stitch and their corresponding line strings
        all_geo_edges_after_stitching_linestrings_generator = self.get_all_poststitch_geo_edges_linestring_generator()
        # Loop through all edges and corresponding edge linestrings
        for edge_linestring,edge in all_geo_edges_after_stitching_linestrings_generator:
            # For debugging purpose
            # if int(edge[0][0])==90 and int(edge[0][1])==180 and int(edge[1][0])== 85 and int(edge[1][1])==180:
                # a=0

            # Perform data perturbation for purposes of finding intersection with land for top and left boundaries
            # However, ORIGINAL edges are still used for route optimization in sea meshes edges list
            # Check to see if edge is a top edge or a left edge, perturb if it is
            # Check edge if it falls on the top or the right side, if so perturb the coordinates slightly
            if 90 in [int(edge[0][0]), int(edge[1][0])] or 180 in [int(edge[0][1]), int(edge[1][1])]:
                perturbed_edge,edge_perturbed_bool = self.perturb_top_and_right_edges(edge)

                # If it is perturbed, change the edge_linestring reference to use the perturbed edge linestring instead of
                # the original generator's linestring for intersection detection
                # if edge_perturbed_bool == True:
                edge_linestring = sgeom.LineString([(perturbed_edge[0][1],perturbed_edge[0][0]),(perturbed_edge[1][1],perturbed_edge[1][0])])

            # A valid sea mesh edge has two AND/OR criteria:
            # 1) If the edge falls entirely, on water body, it is a valid sea mesh edge
            # 2) If edge has zero cost (ie a imaginary edge created for stitching left/right globe boundaries)
            # it is a valid edge even if it crosses a land body
            if prepped_union_all_non_water_features.intersects(edge_linestring) == False or edge in self.list_of_imaginary_stitch_edges:
                self.list_of_all_sea_mesh_edges.append(edge)
                comparison_counter +=1
                if comparison_counter%100000 == 0:
                    print('Comparison complete for edge ' + str(edge) + ' #' + str(comparison_counter))
                # common.print_to_log_w_timestamp(logFilePath, 'Comparison complete for edge ' + str(edge) + ' #' + str(comparison_counter))
        my_time_keeper.stop_timing_event(event_name='Shapely geometry filtering operation')
        print('Node filtering done by eliminating nodes with edges that intersect with non-water polygons for sea mesh complete')


        # my_debug_map_artist.show_edges_on_map(self.list_of_all_sea_mesh_edges,'White')

        #endregion

        # region Create Geopandas geodataframes

        my_time_keeper.start_timing_event(event_name='Create linestrings geodataframe')
        all_lines_gdf = gpd.GeoDataFrame(geometry=list_of_edgelinestrings)
        my_time_keeper.stop_timing_event(event_name='Create linestrings geodataframe')

        my_time_keeper.start_timing_event(event_name='Create union water polygons geodataframe')
        union_water_poly_gdf = gpd.GeoDataFrame(geometry=[union_all_water_features_geom])
        my_time_keeper.stop_timing_event(event_name='Create union water polygons geodataframe')

        my_time_keeper.start_timing_event(event_name='Create land polygons geodataframe')
        land_poly_gdf = gpd.GeoDataFrame(geometry=list_of_land_polygons)
        my_time_keeper.stop_timing_event(event_name='Create land polygons geodataframe')

        my_time_keeper.start_timing_event(event_name='Create union land polygons geodataframe')
        union_land_poly_gdf = gpd.GeoDataFrame(geometry=[union_all_land_features_geom])
        my_time_keeper.stop_timing_event(event_name='Create union land polygons geodataframe')

        #endregion
        #
        # # region SJOIN operation, find linestring within union all water polys
        # # # Perform geopandas sjoin operations completed in 00 HOURS :25 MINUTES :27.34 SECONDS
        # # my_time_keeper.start_timing_event(event_name='Perform geopandas sjoin operations')
        # # # perform spatial join using the two geodataframes, note tha order of the gdf in arguments matter
        # # list_of_linestrings_within_unioned_all_water_features = gpd.sjoin(all_lines_gdf, union_water_poly_gdf, how='inner',
        # #                                                                   op='within')
        # # my_time_keeper.stop_timing_event(event_name='Perform geopandas sjoin operations')
        # # my_debug_map_artist.show_linepoint_geometries_on_map(
        # #     list(list_of_linestrings_within_unioned_all_water_features['geometry']), 'k')
        # # a=0
        # # endregion
        #
        # # region Geopandas Rtree implementation #1
        #
        # my_time_keeper.start_timing_event(event_name='Rtree filter operation - line intersect union all water')
        #
        # # line_spatial_index = lines_gdf.sindex
        # # print('Total number of lines: ' + str(len(all_lines_gdf)))
        # # possible_matches_index = list(line_spatial_index.intersection(union_all_water_features_geom.bounds))
        # # print('Total number of possible matches after rtree pass: ' + str(len(possible_matches_index)))
        # # possible_matches = all_lines_gdf.iloc[possible_matches_index]
        # # precise_matches = possible_matches[possible_matches.intersects(union_all_water_features_geom)]
        # # print('Total number of matches without false positives: ' + str(len(precise_matches)))
        #
        #
        # my_time_keeper.stop_timing_event(event_name='Rtree filter operation - line intersect union all water')
        #
        # a = 0
        # # endregion
        #
        # # region Geopandas Rtree implementation #2
        #
        my_time_keeper.start_timing_event(event_name='Rtree filter operation - line intersect land polygon list')
        my_time_keeper.start_timing_event(event_name='Spatial index of line strings')
        all_lines_spatial_index = all_lines_gdf.sindex
        my_time_keeper.stop_timing_event(event_name='Spatial index of line strings')
        precise_matches_index_list =[]
        precise_matches_index_tuple =()
        precise_matches_index_list = []
        print('Linestring geodataframe shape: ' + str(all_lines_gdf.shape))
        my_time_keeper.start_timing_event(event_name='Loop through split land polygons and compare to spatial index')
        # # Loop polygon list
        for split_piece_land_polygon in split_union_non_water_features:
            possible_matches_index = list(all_lines_spatial_index.intersection(split_piece_land_polygon.bounds))
            # print('Total number of possible matches after rtree pass: ' + str(len(possible_matches_index)))
            possible_matches = all_lines_gdf.iloc[possible_matches_index]
            precise_matches = possible_matches[possible_matches.intersects(split_piece_land_polygon)]
            # print('Total number of precise matches shapely pass: ' + str(len(precise_matches)))
            precise_matches_index_tuple += tuple(precise_matches.index)
            precise_matches_index_list.extend(list(precise_matches.index))

        my_time_keeper.stop_timing_event(event_name='Loop through split land polygons and compare to spatial index')

        my_time_keeper.start_timing_event(event_name='Perform set operations on resulting indices')
        # remove duplicates that are caused by lines that stretch across 2 or more split land polygons
        precise_matches_removed_duplicate_line_index = list(set(precise_matches_index_list))
        all_linestring_index = set([i for i in range(0, all_lines_gdf.shape[0]-1)])
        all_unique_precise_match_index = set(precise_matches_removed_duplicate_line_index)
        inverse_of_unique_precise_match = all_linestring_index - all_unique_precise_match_index
        my_time_keeper.stop_timing_event(event_name='Perform set operations on resulting indices')
        #
        # # The above rtree spatial operation REMOVED IMAGINARY LINES incorrectly as this implementation removes ALL
        # # lines that cross land polygons. Although the imaginary lines cross land polygons (edge to edge on world map)
        # # , the imaginary lines should be considered a valid part of the edges in computation of vessel route
        # cosmetic_linestrings_outside_land = all_lines_gdf.iloc[list(inverse_of_unique_precise_match)]
        # cosmetic_linestrings_intersect_land = all_lines_gdf.iloc[list(all_unique_precise_match_index)]
        #
        #
        # # my_debug_map_artist.show_linepoint_geometries_on_map(cosmetic_linestrings_outside_land['geometry'], 'k')
        # # my_debug_map_artist.show_linepoint_geometries_on_map(cosmetic_linestrings_outside_land['geometry'], 'k')
        # # my_debug_map_artist.show_linepoint_geometries_on_map(cosmetic_linestrings_outside_land['geometry'], 'k')
        #
        # pointpair_list = [[(edge[0][1],edge[0][0]), (edge[1][1],edge[1][0])] for edge in self.list_of_imaginary_stitch_edges]
        # # linestring_list = [sgeom.LineString[[edge[0], edge[1]]] for edge in self.list_of_imaginary_stitch_edges]
        # imaginary_line_df = pd.DataFrame({'pointpairtuple': pointpair_list})
        # imaginary_line_df['geometry'] = imaginary_line_df['pointpairtuple'].apply(sgeom.LineString)
        #
        # # imaginary_line_gdf = GeoDataFrame(imaginary_line_df, geometry='geometry')     #
        #
        #
        #
        # # Create geodataframe of imaginary lines
        # for edge in self.list_of_imaginary_stitch_edges:
        #     a=0
        #
        #
        #
        # # my_debug_map_artist.show_linepoint_geometries_on_map(cosmetic_linestrings_outside_land['geometry'].tolist(), 'k')
        # # lines_that_nonintersects_land = lines_gdf[~lines_gdf.isin(lines_that_intersects_land)]
        #
        # # print('Total number of lines that intersect land matches without false positives: ' + str(len(lines_that_intersects_land)))
        # # print('Total number of lines that non-intersect land matches without false positives: ' + str(len(lines_that_nonintersects_land)))
        # my_time_keeper.stop_timing_event(event_name='Rtree filter operation - line intersect land polygon list')
        #
        #
        # # endregion

        #endregion end debug
    def add_canal_edge_after_mesh_and_qnodes_created(self,canal_name,line_coord_list):
        # This step adds a canal represented by a line with point pairs tuples
        # The ends of the canal are connected to the existing nearest sea mesh nodes by quantization which naturally
        # means that base sea mesh nodes must be created before calling this function
        # Canals stored in the self.canal_edges_list

        new_canal_adjacency_list = []
        first_node = line_coord_list[0]
        last_node = line_coord_list[len(line_coord_list)-1]
        # quantized_first_node = self.quantized_coord_using_grid(first_node[0],first_node[1])
        # quantized_last_node = self.quantized_coord_using_grid(first_node[0], first_node[1])

        # quantized nodes are existing nodes, connect existing nodes to the new canal line nodes
        # line_coord_list.insert(0, first_node)
        # line_coord_list.append(last_node)

        # create edges to link all the nodes in the order below:
        # quantized first node<->first node, second node, ... last node <-> quantized last node
        previous_node = None
        for current_node in line_coord_list:
            #create bidirectional edges for links between two adjacent nodes
            if previous_node != None:
                edge = (previous_node, current_node,
                        self.calc_geo_dist_km(previous_node[0], previous_node[1], current_node[0], current_node[1]))
                reversed_edge = (current_node, previous_node,
                        self.calc_geo_dist_km(current_node[0], current_node[1], previous_node[0], previous_node[1]))

                new_canal_adjacency_list.append(edge)
                new_canal_adjacency_list.append(reversed_edge)

            previous_node = current_node
        # This is just a reference variable to see what canals are added
        self.canal_edges_list.append((canal_name,new_canal_adjacency_list))

        # Add the canal edges into the sea mesh
        self.list_of_all_sea_mesh_edges.extend(new_canal_adjacency_list)

        a=0

    def export_geometries_as_geojson(self):
        df = pd.DataFrame(columns=['geometries'])
        gdf = gpd.GeoDataFrame(df,geometry=[self.union_all_water_features])
        a=1

