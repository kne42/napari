from typing import Dict, Tuple, Union

import numpy as np
from vispy.color.colormap import Colormap


def dataframe_to_properties(dataframe) -> Dict[str, np.ndarray]:
    """Convert a dataframe to Points.properties formatted dictionary.

    Parameters
    ----------
    dataframe : DataFrame
        The dataframe object to be converted to a properties dictionary

    Returns
    -------
    dict[str, np.ndarray]
        A properties dictionary where the key is the property name and the value
        is an ndarray with the property value for each point.
    """

    properties = {col: np.asarray(dataframe[col]) for col in dataframe}
    return properties


def guess_continuous(property: np.ndarray) -> bool:
    """Guess if the property is continuous (return True) or categorical (return False)"""
    # if the property is a floating type, guess continuous
    if issubclass(property.dtype.type, np.floating) and len(property < 16):
        return True
    else:
        return False


def map_property(
    prop: np.ndarray,
    colormap: Colormap,
    contrast_limits: Union[None, Tuple[float, float]] = None,
) -> Tuple[np.ndarray, Tuple[float, float]]:
    """Apply a colormap to a property

    Parameters
    ----------
    prop : np.ndarray
        The property to be colormapped
    colormap : vispy.color.Colormap
        The vispy colormap object to apply to the property
    contrast_limits: Union[None, Tuple[float, float]]
        The contrast limits for applying the colormap to the property.
        If a 2-tuple is provided, it should be provided as (lower_bound, upper_bound).
        If None is provided, the contrast limits will be set to (property.min(), property.max()).
        Default value is None.
    """

    if contrast_limits is None:
        contrast_limits = (prop.min(), prop.max())
    normalized_properties = np.interp(prop, contrast_limits, (0, 1))
    mapped_properties = colormap.map(normalized_properties)

    return mapped_properties, contrast_limits


def create_box(data):
    """Create the axis aligned interaction box of a list of points

    Parameters
    ----------
    data : (N, 2) array
        Points around which the interaction box is created

    Returns
    -------
    box : (4, 2) array
        Vertices of the interaction box
    """
    min_val = data.min(axis=0)
    max_val = data.max(axis=0)
    tl = np.array([min_val[0], min_val[1]])
    tr = np.array([max_val[0], min_val[1]])
    br = np.array([max_val[0], max_val[1]])
    bl = np.array([min_val[0], max_val[1]])
    box = np.array([tl, tr, br, bl])
    return box


def points_to_squares(points, sizes):
    """Expand points to squares defined by their size

    Parameters
    ----------
    points : (N, 2) array
        Points to be turned into squares
    sizes : (N,) array
        Size of each point

    Returns
    -------
    rect : (4N, 2) array
        Vertices of the expanded points
    """
    rect = np.concatenate(
        [
            points + np.sqrt(2) / 2 * np.array([sizes, sizes]).T,
            points + np.sqrt(2) / 2 * np.array([sizes, -sizes]).T,
            points + np.sqrt(2) / 2 * np.array([-sizes, sizes]).T,
            points + np.sqrt(2) / 2 * np.array([-sizes, -sizes]).T,
        ],
        axis=0,
    )
    return rect


def points_in_box(corners, points, sizes):
    """Determine which points are in an axis aligned box defined by the corners

    Parameters
    ----------
    points : (N, 2) array
        Points to be checked
    sizes : (N,) array
        Size of each point

    Returns
    -------
    inside : list
        Indices of points inside the box
    """
    box = create_box(corners)[[0, 2]]
    rect = points_to_squares(points, sizes)
    below_top = np.all(box[1] >= rect, axis=1)
    above_bottom = np.all(rect >= box[0], axis=1)
    inside = np.logical_and(below_top, above_bottom)
    inside = np.unique(np.where(inside)[0] % len(points))
    return list(inside)
