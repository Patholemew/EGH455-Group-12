import math


def calculate_angle(gauge_centre, needle):
    """
    Calculate needle angle from gauge centre and needle.

    Angle convention:
        0 deg   = bottom
        90 deg  = left
        180 deg = top
        270 deg = right

    Parameters
    ----------
    gauge_centre : tuple
        (x, y) pixel coordinates of the gauge centre.

    needle : tuple
        (x, y) pixel coordinates of the needle.

    Returns
    -------
    float
        Needle angle in degrees from 0 to <360.
    """

    if gauge_centre is None or needle is None:
        return None

    centre_x, centre_y = gauge_centre
    needle_x, needle_y = needle

    dx = needle_x - centre_x
    dy = needle_y - centre_y

    # Image coordinates have +y pointing downwards.
    #
    # Desired convention:
    # bottom = 0
    # left   = 90
    # top    = 180
    # right  = 270
    angle = math.degrees(
        math.atan2(-dx, dy)
    )

    return angle % 360


def angle_to_measurement(angle, gauge_type):
    """
    Convert needle angle to the gauge measurement.

    Replace the contents of this function once the calibration
    equations for each gauge type have been determined.

    Parameters
    ----------
    angle : float
        Needle angle in degrees.

    gauge_type : str
        "Blue Gauge" or "Plain Gauge".

    Returns
    -------
    float or None
        Gauge measurement. Currently None until calibration
        equations are added.
    """

    if angle is None:
        return None


    if gauge_type == "Blue Gauge":
        measurement = 0.0356 * angle - 1.4226
    
    elif gauge_type == "Plain Gauge":
        measurement = 0.0368 * angle - 1.5254
    
    else:
        return None
    
    return measurement


def read_gauge(gauge):
    """
    Calculate the angle and measurement for one gauge returned
    by OakDetector.

    Parameters
    ----------
    gauge : dict
        Gauge dictionary returned from OakDetector.

    Returns
    -------
    dict
        Gauge type, centre, needle, angle and measurement.
    """

    gauge_type = gauge["type"]
    centre = gauge["centre"]
    needle = gauge["needle"]

    # Cannot calculate angle unless both points were detected
    # and associated with the gauge.
    if centre is None or needle is None:

        return {
            "type": gauge_type,
            "centre": centre,
            "needle": needle,
            "angle": None,
            "measurement": None,
            "valid": False,
        }

    angle = calculate_angle(
        centre,
        needle,
    )

    measurement = angle_to_measurement(
        angle,
        gauge_type,
    )

    return {
        "type": gauge_type,
        "centre": centre,
        "needle": needle,
        "angle": angle,
        "measurement": measurement,
        "valid": True,
    }


def process_gauge(gauges):
    """Read the first detected gauge.

    Returns
    -------
    dict | None
        Gauge reading dictionary, or None if no gauge is detected.
    """
    if not gauges:
        return None

    return read_gauge(gauges[0])
