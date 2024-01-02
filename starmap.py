from datetime import datetime

from matplotlib.collections import LineCollection
from matplotlib.pyplot import subplots, close
from numpy import array, rollaxis, clip, amax
from pytz import timezone, utc
from skyfield import api, projections
from skyfield.data import hipparcos, stellarium
from timezonefinder import TimezoneFinder
from ttkbootstrap import (
    BooleanVar,
    Button,
    Checkbutton,
    DateEntry,
    DoubleVar,
    Entry,
    Frame,
    Label,
    Labelframe,
    Scale,
    StringVar,
    Window,
    constants,
    Combobox,
)
from ttkbootstrap.dialogs import Messagebox, colorchooser
from tkinter.filedialog import asksaveasfilename

ADD_CONSTELLATIONS = True
BG_COLOR = "#000000"
ALPHA = 1.0
STAR_COLOR = "#ffffff"
CONSTELLATION_COLOR = "#ffffff"
CONSTELLATION_WIDTH = 0.3
STAR_SCALING = 100
STAR_SIZE_LIMIT = 400
FIGURE_SIZE = 10
FILENAME = "starmap.png"
DPI = 500

MAGNITUDE_LEVELS = [
    "0 - very few stars",
    "1 ",
    "2 ",
    "3 - urban night sky",
    "4 ",
    "5 ",
    "6 - rural night sky",
    "7 ",
    "8 ",
    "9 ",
    "10 - most stars are visible",
    "11",
    "12",
    "13",
    "14",
    "15 - show all the stars",
]


def generate_starmap(
    use_constellations: bool,
    constellation_color: str,
    constellation_width: float,
    bg_color: str,
    bg_alpha: float,
    star_color: str,
    time: str,
    lat: str,
    long: str,
    star_scaling: str,
    max_magnitude: str,
    output: str,
    dpi: str,
    star_limit: str,
):
    try:
        lat = float(lat)
    except ValueError:
        Messagebox.show_error(
            message="The latitude isn't a valid number.\n"
            + "A valid latitude looks like this: 12.3456"
        )
        return

    try:
        long = float(long)
    except ValueError:
        Messagebox.show_error(
            message="The longitude isn't a valid number.\n"
            + "A valid longitude looks like this: 12.3456"
        )
        return

    try:
        star_scaling = int(star_scaling)
    except ValueError:
        Messagebox.show_error(
            message="The maximum star size isn't a valid integer number."
        )
        return

    try:
        max_magnitude = int(max_magnitude)
        if max_magnitude < 0 or max_magnitude > 15:
            raise ValueError
    except ValueError:
        Messagebox.show_error(
            message="The maximum magnitude isn't a valid integer number from 0 to 15."
        )
        return

    try:
        dpi = int(dpi)
    except ValueError:
        Messagebox.show_error(message="The DPI isn't a valid integer number.")
        return

    try:
        star_limit = int(star_limit)
    except ValueError:
        Messagebox.show_error(
            message="The star size limit isn't a valid integer number."
        )
        return

    # de421 shows position of earth and sun in space
    eph = api.load("de421.bsp")

    # hipparcos dataset contains star location data
    with api.load.open(hipparcos.URL) as f:
        stars = hipparcos.load_dataframe(f)

    url = (
        "https://raw.githubusercontent.com/Stellarium/stellarium/master"
        "/skycultures/modern_st/constellationship.fab"
    )

    with api.load.open(url) as f:
        constellations = stellarium.parse_constellations(f)

    # define datetime and convert to utc based on our timezone
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lng=long, lat=lat)
    dt = datetime.strptime(time, "%Y-%m-%d %H:%M")
    local = timezone(timezone_str)

    # get UTC from local timezone and datetime
    local_dt = local.localize(dt, is_dst=None)
    utc_dt = local_dt.astimezone(utc)

    # find location of earth
    earth = eph["earth"]

    # define observation time from our UTC datetime
    ts = api.load.timescale()
    t = ts.from_datetime(utc_dt)

    # define an observer using the world geodetic system data
    observer = api.wgs84.latlon(latitude_degrees=lat, longitude_degrees=long).at(t)

    # center the observation point in the middle of the sky
    ra, dec, _ = observer.radec()
    center_object = api.Star(ra=ra, dec=dec)

    # find where our center object is relative to earth
    # and build a projection with 180 degree view
    center = earth.at(t).observe(center_object)
    projection = projections.build_stereographic_projection(center)

    # calculate star positions and project them onto a plain space
    star_positions = earth.at(t).observe(api.Star.from_dataframe(stars))
    stars["x"], stars["y"] = projection(star_positions)

    edges = [edge for name, edges in constellations for edge in edges]
    edges_star1 = [star1 for star1, star2 in edges]
    edges_star2 = [star2 for star1, star2 in edges]

    print("Max bright before magnitude: " + str(amax(stars.magnitude)))

    bright_stars = stars.magnitude <= max_magnitude
    magnitude = stars["magnitude"][bright_stars]

    print("Max bright after magnitude: " + str(amax(magnitude)))

    marker_size = star_scaling * 10 ** (magnitude / -2.5)
    print("Max bright after scale: " + str(amax(marker_size)))
    marker_size = clip(marker_size, a_min=None, a_max=star_limit)

    fig, ax = subplots(
        figsize=(FIGURE_SIZE, FIGURE_SIZE), facecolor=(bg_color, bg_alpha)
    )
    ax.scatter(
        stars["x"][bright_stars],
        stars["y"][bright_stars],
        s=marker_size,
        color=star_color,
        marker=".",
        linewidths=0,
        zorder=2,
    )

    xy1 = stars[["x", "y"]].loc[edges_star1].values
    xy2 = stars[["x", "y"]].loc[edges_star2].values
    lines_xy = rollaxis(array([xy1, xy2]), 1)

    if use_constellations:
        ax.add_collection(
            LineCollection(
                lines_xy, colors=constellation_color, linewidths=constellation_width
            )
        )

    # set the aspect ratio of the plot to be equal
    ax.set_aspect("equal")

    # other settings
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.axis("off")
    fig.savefig(output, bbox_inches="tight", pad_inches=0, dpi=DPI)
    close(fig)

    Messagebox.ok(message="Done!")


def pick_color(color_chooser: colorchooser.ColorChooserDialog, color_var: StringVar):
    color_chooser.show()
    color_var.set(color_chooser.result.hex)


def add_color_chooser(root: Frame, button_text: str, color_value: StringVar):
    # Create container frame
    frame = Frame(root)

    # Create color chooser
    chooser = colorchooser.ColorChooserDialog()

    # Create button
    button = Button(
        frame, text=button_text, command=lambda: pick_color(chooser, color_value)
    )
    button.pack(padx=5, side=constants.LEFT, fill=constants.X, expand=True)

    # Create color value label
    label = Label(
        frame,
        text=color_value.get(),
        background=color_value.get(),
        foreground="grey",
        font="TkFixedFont",
    )
    label.pack(padx=5, side=constants.RIGHT)

    # Ensure label is updated when color changes
    color_value.trace_add(
        "write",
        lambda *args: label.config(
            text=color_value.get(), background=color_value.get()
        ),
    )

    frame.pack(fill=constants.X, pady=5)


def add_scale(root: Frame, scale_text: str, scale_value: DoubleVar, to: float = 1.0):
    # Create container frame
    frame = Frame(root)

    # Create label
    label = Label(frame, text=scale_text)
    label.pack(anchor=constants.NE, fill=constants.X, expand=True, padx=5)

    # Create scale
    button = Scale(frame, variable=scale_value, to=to)
    button.pack(padx=5, side=constants.LEFT, fill=constants.X, expand=True)

    # Create scale value label
    label = Label(
        frame,
        text=f"{scale_value.get():.2f}",
        font="TkFixedFont",
    )
    label.pack(padx=5, side=constants.RIGHT)

    # Ensure label is updated when value changes
    scale_value.trace_add(
        "write",
        lambda *args: label.config(text=f"{scale_value.get():.2f}"),
    )

    frame.pack(fill=constants.X, pady=5)


def choose_file(entry, value):
    filename = asksaveasfilename()
    if filename:
        entry.delete(0, constants.END)  # Clear the Entry widget
        entry.insert(constants.END, filename)
        value.set(filename)


def create_combobox(root, text: str, variable=None, values=None, state="readonly"):
    frame = Frame(root)

    label = Label(frame, text=text)
    label.pack(anchor=constants.NW, padx=5)

    combo_frame = Frame(frame)

    combo = Combobox(combo_frame, textvariable=variable)
    combo["values"] = values
    combo["state"] = state
    combo.pack(side=constants.LEFT, fill=constants.X, expand=True, padx=5)

    combo_frame.pack(expand=True, fill=constants.X)

    frame.pack(pady=5, expand=True, fill=constants.X)

    return combo


def create_entry(root, text: str, value="", add_button=False, button_var=None):
    frame = Frame(root)

    label = Label(frame, text=text)
    label.pack(anchor=constants.NW, padx=5)

    entry_frame = Frame(frame)

    entry = Entry(entry_frame)
    entry.insert(0, str(value))
    entry.pack(side=constants.LEFT, fill=constants.X, expand=True, padx=5)

    if add_button:
        # Filename chooser
        filename_button = Button(
            entry_frame,
            text="...",
            command=lambda: choose_file(entry, button_var),
        )
        filename_button.pack(side=constants.LEFT, padx=5)

    entry_frame.pack(expand=True, fill=constants.X)

    frame.pack(pady=5, expand=True, fill=constants.X)

    return entry


if __name__ == "__main__":
    root = Window(themename="darkly", iconphoto="assets/logo.png", title="Starmap")

    top_frame = Frame(root)

    # Create geospatial (time/location) settings frame #
    ##############################
    geospatial_settings = Labelframe(
        top_frame,
        text="Location and time",
    )

    date_frame = Frame(geospatial_settings)

    # Create label
    date_label = Label(date_frame, text="Date and time")
    date_label.pack(anchor=constants.NW, padx=5)

    # Date entry
    date_entry = DateEntry(date_frame, dateformat="%Y-%m-%d %H:%M")
    date_entry.pack(padx=5)

    date_frame.pack(pady=5)

    # Latitude
    latitude = create_entry(geospatial_settings, text="Latitude")

    # Longitude
    longitude = create_entry(geospatial_settings, text="Longitude")

    geospatial_settings.pack(padx=5, pady=5, fill=constants.Y, side=constants.LEFT)

    # Create color settings frame #
    ###############################
    color_settings = Labelframe(top_frame, text="Colors")

    # Star color settings
    star_color = StringVar(value=STAR_COLOR)
    add_color_chooser(color_settings, "Star color", star_color)

    # Background color settings
    bg_color = StringVar(value=BG_COLOR)
    add_color_chooser(color_settings, "Background color", bg_color)

    # Background transparency
    bg_alpha = DoubleVar(value=ALPHA)
    add_scale(color_settings, "Background opacity", bg_alpha)

    # Constellation color settings
    constellation_color = StringVar(value=CONSTELLATION_COLOR)
    add_color_chooser(color_settings, "Constellation color", constellation_color)

    # Constellation line width
    constellation_width = DoubleVar(value=CONSTELLATION_WIDTH)
    add_scale(color_settings, "Constellation line width", constellation_width, to=3.0)

    color_settings.pack(padx=5, pady=5, fill=constants.Y, side=constants.LEFT)

    # Create star settings frame #
    ##############################
    star_settings = Labelframe(top_frame, text="Star settings")

    magnitude = StringVar(value="10 - most stars are visible")
    magnitude_box = create_combobox(
        star_settings,
        text="Magnitude filtering level",
        values=MAGNITUDE_LEVELS,
        variable=magnitude,
    )

    # Star scaling
    star_scaling = create_entry(
        star_settings, text="Star scaling (in %)", value=str(STAR_SCALING)
    )

    # Star limit
    star_limit = create_entry(
        star_settings, text="Star size limit", value=str(STAR_SIZE_LIMIT)
    )

    # DPI
    dpi = create_entry(star_settings, text="DPI", value=str(DPI))

    star_settings.pack(padx=5, pady=5, fill=constants.Y, side=constants.LEFT)

    top_frame.pack(side=constants.TOP)

    bottom_frame = Frame(root)

    # Constellations checkbox
    use_constellations = BooleanVar(value=ADD_CONSTELLATIONS)
    constellation_box = Checkbutton(
        bottom_frame, variable=use_constellations, text="Add constellations"
    )
    constellation_box.pack(padx=10, pady=10)

    # Filename input
    filename = StringVar(value=FILENAME)
    filename_input = create_entry(
        bottom_frame,
        value=filename.get(),
        text="Output filename",
        add_button=True,
        button_var=filename,
    )

    filename_input.pack(expand=True, fill=constants.X)

    # Create start button
    start_button = Button(
        bottom_frame,
        text="Start",
        command=lambda: generate_starmap(
            use_constellations.get(),
            constellation_color=constellation_color.get(),
            constellation_width=constellation_width.get(),
            star_color=star_color.get(),
            bg_color=bg_color.get(),
            bg_alpha=bg_alpha.get(),
            time=date_entry.entry.get(),
            lat=latitude.get(),
            long=longitude.get(),
            star_scaling=star_scaling.get(),
            max_magnitude=magnitude.get()[:2],
            output=filename.get(),
            dpi=dpi.get(),
            star_limit=star_limit.get(),
        ),
    )
    start_button.pack(padx=10, pady=10)

    bottom_frame.pack(side=constants.BOTTOM, fill=constants.X, expand=True)

    # Start window
    root.mainloop()
