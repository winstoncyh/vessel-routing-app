from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.http import HttpResponseRedirect,HttpResponse,JsonResponse
from django.views import generic
from graphviz import Digraph
import os
import pickle
import json
from django.core.serializers.json import DjangoJSONEncoder
from forms import RoutingForm
import src.onload as onload_func
import src.common as common
import sys
scriptfilepath = common.get_calling_script_directory_path(sys)

vc_pickle_file = scriptfilepath + r'\cache\vc_0.5_degree.pickle'
# def home_view(request, *args,**kwargs):
#     template_context_dictionary = {'list_of_crude_streams':['Dubai','Cossack','Enfield','Forties']}
#     return render (request,'home.html',template_context_dictionary)


def home_view(request):

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = RoutingForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            origin_lat = form.cleaned_data['origin_latitude']
            origin_lon = form.cleaned_data['origin_longitude']
            dest_lat = form.cleaned_data['destination_latitude']
            dest_lon = form.cleaned_data['destination_longitude']
            origin_lat_float = float(origin_lat)
            origin_lon_float = float(origin_lon)
            dest_lat_float = float(dest_lat)
            dest_lon_float = float(dest_lon)

            my_vc = onload_func.onload()
            vessel_optimized_track = my_vc.get_optimal_route((origin_lat_float, origin_lon_float), (dest_lat_float, dest_lon_float))
            my_vc.my_map_artist.plot_vessel_track(vessel_optimized_track, 'Vessel')
            my_vc.my_map_artist.save_plot('savedplot.png')

            return render(request, 'home.html', {'routingform': form})

    # if a GET (or any other method) we'll create a blank form
    else:

        form = RoutingForm()
        my_vc = onload_func.onload()
        my_vc.my_map_artist.save_plot('savedplot.png')

    return render(request, 'home.html', {'routingform': form})