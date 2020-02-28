from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection
# The polygon is first split into two parts across it's shortest dimension
# (either left to right or top to bottom). If these parts are larger than a given threshold they are split
# again in a similar manner. This is repeated until all of the parts are the desired size. This method
# has two advantages over using a regular grid: the first division of the polygon requires the entire
# geometry to be evaluated, but the second considers each of the two parts independently, and so on,
# thereby reducing the effort required; and additionally, polygons already smaller than the size threshold
# are never split because the "grid" is aligned to each polygon individually, further reducing the effort
# required (and also producing a better result).
# The algorithm is presented below. The function is named katana after the long, single-edged sword used by Japanese samurai.
def katana(geometry, threshold, count=0):
    """Split a Polygon into two parts across it's shortest dimension"""
    bounds = geometry.bounds
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    if max(width, height) <= threshold or count == 250:
        # either the polygon is smaller than the threshold, or the maximum
        # number of recursions has been reached
        return [geometry]
    if height >= width:
        # split left to right
        a = box(bounds[0], bounds[1], bounds[2], bounds[1]+height/2)
        b = box(bounds[0], bounds[1]+height/2, bounds[2], bounds[3])
    else:
        # split top to bottom
        a = box(bounds[0], bounds[1], bounds[0]+width/2, bounds[3])
        b = box(bounds[0]+width/2, bounds[1], bounds[2], bounds[3])
    result = []
    for d in (a, b,):
        c = geometry.intersection(d)
        if not isinstance(c, GeometryCollection):
            c = [c]
        for e in c:
            if isinstance(e, (Polygon, MultiPolygon)):
                result.extend(katana(e, threshold, count+1))
    if count > 0:
        return result
    # convert multipart into singlepart
    final_result = []
    for g in result:
        if isinstance(g, MultiPolygon):
            final_result.extend(g)
        else:
            final_result.append(g)
    return final_result