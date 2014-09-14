def extend_bbox(boundingbox):
    """Extends the bounding box by x3 for its width, and x3 of its height."""
    s, n, w, e = [float(coord) for coord in bouindingbox]
    delta_lat, delta_lng = n - s, e - w
    return [s - delta_lat, n + delta_lat, w - delta_lng, e + delta_lng]
