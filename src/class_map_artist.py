import cartopy.io.shapereader as shpreader
import cartopy.crs as ccrs
import cartopy.feature as cf
import shapely.geometry as sgeom
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.geometry import LineString
import matplotlib.pyplot as plt
from matplotlib import collections  as mc

class map_artist():
    def __init__(self):
        # Constructor does not do anything, call initialize default map to show a map
        # Call other methods to create and display and therefore create the required maps
        # Map artist needs a map to work on, and receives input and draws them on said map accordingly
        self.created = True
        self.list_of_plotted_objects = []
        self.fig, self.ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(30, 30))

        # This is a static color list 
        # self.color_palette_reference_list = \
        # [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 240, 240),
        #  (240, 50, 230), (210, 245, 60), (250, 190, 190), (0, 128, 128), (230, 190, 255), (170, 110, 40),
        #  (255, 250, 200), (128, 0, 0), (170, 255, 195), (128, 128, 0), (255, 215, 180), (0, 0, 128), (128, 128, 128),
        #  (255, 255, 255), (0, 0, 0)]

        self.color_palette_reference_list = [(65, 104, 190), (123, 60, 195), (181, 59, 196), (200, 76, 55),
                                             (57, 198, 69), (191, 64, 105), (65, 190, 188), (203, 150, 52),
                                             (65, 149, 190), (56, 51, 204), (109, 203, 52), (60, 195, 135),
                                             (172, 201, 54)]

        self.python_rgb_tuple_reference_list = [(rgb_tuple[0]/255,rgb_tuple[1]/255,rgb_tuple[2]/255) for rgb_tuple in self.color_palette_reference_list]

        # This is a recyclable list to track usage
        self.color_palette_available = self.python_rgb_tuple_reference_list.copy()

    def pop_color_tuple(self):
        if len(self.color_palette_available) == 0:
            self.color_palette_available = self.python_rgb_tuple_reference_list.copy()

        top_rgb_tuple = self.color_palette_available.pop(0)
        return top_rgb_tuple

    def show_base_map(self):

        # Use cartopy shapereader to read all geometries into a list
        list_of_marine_polygons = list(
            shpreader.Reader(self.marine_polys_filename).geometries())  # returns all polys representing oceans and seas
        list_of_river_geometries = list(shpreader.Reader(
            self.rivers_lake_centerlines_filename).geometries())  # returns multilinestring representing rivers


        # Get cartopy features for plotting
        rivers_lake_centerlines = cf.NaturalEarthFeature(category = 'physical', name = 'rivers_lake_centerlines',
        scale = 'ne_10m', facecolor = 'none', edgecolor = 'blue')

        marine_polys = cf.NaturalEarthFeature(category='physical', name='geography_marine_polys', scale='ne_10m',
                                              facecolor='blue')
        self.fig, self.ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(30, 30))

        # ax.set_title('Natural Earth Geometries: geography_marine_polys,rivers_lake_centerlines,graticules_1')

        # Add marine polygons, rivers lakes centerlines and graticules in ax
        self.ax.add_feature(marine_polys, zorder=1)
        self.ax.add_feature(rivers_lake_centerlines, zorder=1)

        pass
        # self.ax.add_feature(graticules_1, zorder=2)

    def show_nodes_on_map(self,node_list,int_marker_size,strColor):
        self.ax.set_global()
        # self.fig.show()
        for node in node_list:
            self.ax.plot(node[1], node[0], '>', markersize=int_marker_size, color=strColor,
                transform=ccrs.PlateCarree())

    def show_edges_on_map(self,list_of_edges,str_edge_color):

        # Edges should be in the format ( ( -90,180), (-50,90) ,4000 ) which is l,r, and c
        # input edge data is in lat,lon
        # edge must be converted to lon,lat to plot correctly on an xy axis

        # First way of plotting lines using a line collection. First way is better as it is faster than plotting all
        # lines as a geometry. Rendering should also improve.
        list_of_line_xy = []
        self.edgecolor = str_edge_color
        self.edgealpha = 0.15
        # Convert edges to list of lines e.g. lines = [[(0, 1), (1, 1)], [(2, 3), (3, 3)], [(...
        # c = np.array([(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1)]) ---> color array use as argument for linecollection
        # Consolidate all line string objects into a list
        for edge in list_of_edges:
            # coords must be in lon, lat format , not lat lon format
            linestring_tuple_from = (edge[0][1],edge[0][0])
            linestring_tuple_to= (edge[1][1],edge[1][0])
            list_of_line_xy.append([linestring_tuple_from,linestring_tuple_to])

        lc = mc.LineCollection(list_of_line_xy, colors=str_edge_color, linewidths=1,alpha=self.edgealpha)
        self.ax.set_global()
        self.ax.add_collection(lc)

        # # 2nd way of showing edges on world map; Create all edges in form of linestring and add geometries
        # list_of_line_geom = []
        #
        # # Consolidate all line string objects into a list
        # for edge in list_of_edges:
        #     # coords must be in lon, lat format , not lat lon format
        #     linestring_tuple_from = (edge[0][1],edge[0][0])
        #     linestring_tuple_to= (edge[1][1],edge[1][0])
        #     # Create linestring shapely geom
        #     edge_linestring = sgeom.LineString([linestring_tuple_from, linestring_tuple_to])
        #     list_of_line_geom.append(edge_linestring)
        #
        # # Add the list of linestrings
        # self.ax.add_geometries(list_of_line_geom, ccrs.PlateCarree(), facecolor='none',edgecolor=str_edge_color,alpha=0.2)

    def display(self):
        self.ax.set_global()
        self.fig.set_size_inches(15.5, 7.5)
        plt.show()

    def plot_node(self,node_latlon_tuple,**kwargs):

        # There are two types of nodes, hollow or solid nodes
        # There are two types of edges, dashed or solid edges

        # Unpack tuple coordinates
        lat= node_latlon_tuple[0]
        lon = node_latlon_tuple[1]

        # Set default values

        if kwargs.get('circle_size',None) == None:
            circle_size=3
        else:
            circle_size = kwargs.get('circle_size',3)

        if kwargs.get('color_tuple',None) == None:
            color_tuple='k'
        else:
            color_tuple = kwargs.get('color_tuple','k')

        if kwargs.get('hollow',None) == None:
            hollow=False
        else:
            hollow = kwargs.get('hollow',False)

        if kwargs.get('linestyle',None) == None:
            linestyle='-'
        else:
            linestyle = kwargs.get('linestyle','-')

        if kwargs.get('linewidth', None) == None:
            linewidth = 3
        else:
            linewidth = kwargs.get('linewidth', 3)

        if kwargs.get('edgecolor_tuple', None) == None:
            edgecolor_tuple = '"k"'
        else:
            edgecolor_tuple = kwargs.get('edgecolor_tuple', '"k"')

        # handle is a mandatory argument
        str_point_handle_name = kwargs.get('str_point_handle_name',None)
        if str_point_handle_name == None:
            exit('Custom Error: Handle of point is not defined, please ensure function call has str_point_handle_name for node')

        # Plot ellipse representing the vessel
        # Define ellipse, arg 1 = centre, arg 2 = radius of semi major and semi minor axis, arg 3 = rotation in degrees
        start_ellipse = ((lon, lat), (circle_size, circle_size), 0)
        start_circle = sgeom.Point(start_ellipse[0]).buffer(circle_size)

        if hollow == False:
            facecolor = str(color_tuple)
        elif hollow == True:
            facecolor = '"none"'

        exec_string = str_point_handle_name + r'= self.ax.add_geometries([start_circle], crs=ccrs.PlateCarree(), facecolor=' + facecolor + ', edgecolor=' + str(edgecolor_tuple) + ',linestyle="' + linestyle + '",linewidth='+ str(linewidth) + ')'
        exec(exec_string)

        # Add node object to list of plotted nodes in map artist
        eval_string = 'self.list_of_plotted_objects.append(' + str_point_handle_name + ')'
        eval(eval_string)

    def show_polygon_geometries_on_map(self,list_of_geoms,strColor):
        # fig2, ax2 = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(30, 30))
        self.ax.add_geometries(list_of_geoms, ccrs.PlateCarree(), facecolor=strColor)
        # self.fig.show()
    def show_linepoint_geometries_on_map(self,list_of_geoms,strColor):
        # fig2, ax2 = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(30, 30))
        self.ax.add_geometries(list_of_geoms, ccrs.PlateCarree(), edgecolor=strColor)
        # self.fig.show()
    def plot_vessel_track(self,input_journey_track,vessel_name_str):
        # Pop a color for use, only 20 colors available, will be recycled if used up for all nodes
        rgb_tuple = self.pop_color_tuple()

        # Find start node on track
        start_node = input_journey_track[0]

        # Find end node on track
        end_node = input_journey_track[len(input_journey_track)-1]

        # Create handles for the nodes
        vessel_name_start_node_handle = 'START_NODE_' + vessel_name_str.replace(' ','_')
        vessel_name_end_node_handle = 'END_NODE_' + vessel_name_str.replace(' ','_')

        self.plot_node(start_node, str_point_handle_name=vessel_name_start_node_handle, hollow=False,
                       color_tuple=rgb_tuple,linewidth=0.5,linestyle='-')
        self.plot_node(end_node, str_point_handle_name=vessel_name_start_node_handle, hollow=True,
                       color_tuple=rgb_tuple,edgecolor_tuple=rgb_tuple,linewidth=0.5,linestyle='--')



        # self.fig.show()
        imaginary_edge_flag = False
        # region Output track visually

        # Loop through the journey track and plot arrows showing the vessel route
        previous_journey_track_node = None
        for journey_track_node in input_journey_track:
            if previous_journey_track_node != None:
                # Form coordinates for line
                linestring_tuple_from = (previous_journey_track_node[1], previous_journey_track_node[0])
                linestring_tuple_to = (journey_track_node[1], journey_track_node[0])
                # if journey_track_node[0] == 10 and journey_track_node[1] == 180:
                #     a=0
                # Create arrow tracks using annotations
                # Annotate track with arrows, only annotate if the arrow doesn't cross the imaginary nodes ie from (lat,180) to (lat,-180)
                # The above effectively splits transpac routes into two parts of the hemisphere

                # Skip loop if it current and previous nodes are nodes from an imaginary edge e.g. (25,180)->(25,-180)
                #region Check if edge is imaginary
                if journey_track_node[1] == 180 and previous_journey_track_node[1] == -180:
                    imaginary_edge_flag = True
                else:
                    imaginary_edge_flag = False

                if journey_track_node[1] == -180 and previous_journey_track_node[1] == 180:
                    imaginary_edge_flag = True
                else:
                    imaginary_edge_flag = False
                #endregion

                # Annotate only non-imaginary edges
                if imaginary_edge_flag == False:
                    self.ax.annotate('', xy=linestring_tuple_to, xytext=linestring_tuple_from,
                                              arrowprops=dict(arrowstyle="simple", facecolor=rgb_tuple,
                                                              edgecolor=rgb_tuple,linestyle='--'),transform=ccrs.Geodetic())


            # Running within for loop to keep a T-1 node
            previous_journey_track_node = journey_track_node

        text_location_longitude_modifier = 0
        if start_node[1] > 0:
            #Western hemisphere
            text_location_longitude_modifier = -5
        elif start_node[1] <= 0:
            text_location_longitude_modifier = 5


        # Show vessel name after track is plotted
        self.ax.text(start_node[1]+text_location_longitude_modifier, start_node[0], vessel_name_str,
                transform=ccrs.PlateCarree(), color='white', fontsize=8)

        # self.fig.show()

    def show_geometries_on_map(self, list_of_geometric_shapes, strColor):
        self.ax.add_geometries(list_of_geometric_shapes, ccrs.PlateCarree(), edgecolor=strColor)
        # self.fig.show()

    def save_plot(self,savefilepath):
        plt.savefig(savefilepath,bbox_inches='tight')

    pass




