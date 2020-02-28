from collections import defaultdict
from heapq import *
import src.common as common
import sys
scriptfilepath = common.get_calling_script_directory_path(sys)
logFilePath = scriptfilepath + r'\routing_log.txt'

def dijkstra(edges,f,t):
    # Initialize a defaultdict of list type
    # Usually, a Python dictionary throws a KeyError if you try to get an item with a key that is not currently in the dictionary.
    # The defaultdict in contrast will simply create any items that you try to access (provided of course they do not exist yet).
    # If key does not exist, a new item is created with an empty list
    ddict_edges = defaultdict(list)
    q_count = 0
    # What is an edge or a vertex?
    # Each vertex is a 3-tuple in format as such - ("A", "B", 7) ,
    # Format above reads distance from A (f for first) to B (t for terminus) is 7

    for l,r,c in edges:
        # Loop through list of vertices/edges and make use of defaultdic g to create new items
        # dict items uses first node as key, cost and terminus as values
        # By appending (c,r) tuple to the dict using first node keys, effectively we are grouping all the c,r of
        # neighbours of the first node under the node key
        # Looking up a node key in g, returns a list of (c,r) tuples of the node's neighbours
        ddict_edges[l].append((c,r)) #{left_node: (cost, right_node)

    # Note that order of the tuple is cost c and then the node name r (for right), order is to ensure tuple is processed
    # correctly during the heap operation since cost c is also the dijkstra greedy score

    # Initialize queue list with argument f as initial node, an empty set as seen/explored nodes,
    # and mins as a distance dictionary with argument f as the first dict item, where f is mapped 0
    # ie if first node variable f is "A", A which is the initial node, is mapped to 0 integer according to the algo

    came_from={}
    q = [(0,f)] # a list containing the first initial node tuple (0 distance, "A", path list)
    visited_set = set()
    min_cost_from_initial_to_n = {f: 0}

    # while loop, run till q list of node tuples, is empty
    while q:
        q_count += 1
        # heap pop the tuple in the q list and get its values.
        (current_node_cost,current_node) = heappop(q)
        # Check if node is explored
        if current_node not in visited_set:
            # Add to explored list
            visited_set.add(current_node)

            # common.print_to_log_w_timestamp(logFilePath,'Exploring node:' + str(current_node))

            # distance result as cost and the path taken from initial node to current node
            if current_node == t:
                # Terminal node encountered, return the node path
                return (current_node_cost,came_from)
            else:
                # If current node is not terminus, get all neighbours of current node in form of a list of tuples of (cost,right_node)
                neighbours = ddict_edges.get(current_node, ())
                # common.print_to_log_w_timestamp(logFilePath, 'Neighbours:' + str(neighbours))
                # Loop through all neighbours of current node
                for cost_to_right_node, right_node in neighbours:
                    # if node is in visited_set (ie explored), skip to next iteration
                    # only process unvisited neighbours
                    if right_node in visited_set: continue
                    # get the cumulative minimum cost function to neighbour node, default to None if it's first time being looked at
                    prev_cost = min_cost_from_initial_to_n.get(right_node, None)
                    # Calculate the new cumulative cost function to this neighbour by adding current node cost to this neighbour's vertex cost
                    next_cost = current_node_cost + cost_to_right_node

                    if prev_cost is None or next_cost < prev_cost:
                        # add current node to came from list to track journey e.g. node B is tagged to current node A
                        came_from[right_node] = current_node
                        # Update mins with new minimum cost from current node to neighbour node
                        min_cost_from_initial_to_n[right_node] = next_cost
                        # Push neighbour node into the heap priority queue (prioritized by smallest cost) on pop
                        heappush(q, (next_cost, right_node))

    # Q has exhausted without returning the terminal node, solution for routing is not found
    # Possible reason is the start and end nodes are not connected at all by edges e.g. inland lake location
    # common.print_to_log_w_timestamp(logFilePath, 'Solution not found! came_from list:' + str(came_from))
    # common.print_to_log_w_timestamp(logFilePath, 'Solution not found! last node visited:' + str(current_node))
    # common.print_to_log_w_timestamp(logFilePath, 'Queue processed count:' + str(q_count))
    current_node_cost = None
    return (current_node_cost, came_from)