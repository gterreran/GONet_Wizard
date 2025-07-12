"""
Load and preprocess multi-epoch GONet observation data from JSON files.

This module provides functionality for aggregating and flattening GONet
nightly observation data into a single dictionary suitable for dashboard
visualization and analysis. Each JSON file in the folder specified by
`env.DASHBOARD_DATA_PATH` is expected to contain structured nightly data
in the GONet format.

**Key features**

- Parses and validates nightly GONet JSON files
- Flattens metadata and multi-channel metrics into a unified structure
- Dynamically generates feature labels for dashboard dropdowns
- Computes channel ratios and localized time features
- Handles data format mismatches and missing fields gracefully

Notes
-----

- Time features are computed in UTC and localized form.
- Derived channel ratios (e.g., 'blue-green') are included in the output.
- Labels for dashboard dropdowns are dynamically assigned in `env.LABELS`.

"""

import json, datetime

def load_data_from_json(env):
    """
    Load and prepare all available GONet data from JSON files in the `env.DASHBOARD_DATA_PATH` folder.

    This simplified version assumes that every valid `.json` file in `env.DASHBOARD_DATA_PATH`
    contains nightly observation data in the expected GONet format.

    ``time_unix``, ``float_hours_utc``, and ``float_hours_local`` are 3 hidden columns that cannot be
    visualized in the main plot, since are not very human-readable. The purpose of these columns
    is to provide some numerical values for time and dates, making them more easily filterable. 

    Parameters
    ----------
    env : module-like
        Object with required attributes:
        
        - env.DASHBOARD_DATA_PATH: :class:`pathlib.Path` — path to the folder containing JSON files.
        - env.CHANNELS: list of str — e.g., ['red', 'green', 'blue']
        - env.LABELS: dict to be populated with 'gen' and 'fit' keys.
        - env.LOCAL_TZ: tzinfo object for localizing timestamps.

    Returns
    -------
    data : :class:`dict`
        Flattened dictionary of all GONet metadata and channel-specific values.

    options_x : :class:`list` of :class:`dict`
        Dropdown options for the x-axis selector.

    options_y : :class:`list` of :class:`dict`
        Dropdown options for the y-axis selector.

    Raises
    ------
    FileNotFoundError
        If the directory is empty or contains no valid JSON files.

    ValueError
        If the JSON files are malformed or missing required fields.
    """
    if not env.DASHBOARD_DATA_PATH.exists():
        raise FileNotFoundError(f"The directory '{env.DASHBOARD_DATA_PATH}' defined in GONET_ROOT does not exist.")

    json_files = sorted(f.name for f in env.DASHBOARD_DATA_PATH.iterdir() if f.suffix == ".json")
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in GONET_ROOT: {env.DASHBOARD_DATA_PATH}")

    data = {'idx': [], 'channel': []}
    image_idx = -1
    data_initialized = False

    for file_name in json_files:
        json_path = env.DASHBOARD_DATA_PATH / file_name
        try:
            with open(json_path) as inp:
                night_dict = json.load(inp)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON file '{file_name}': {e}")

        if not data_initialized:
            try:
                env.LABELS['gen'] = [l for l in night_dict[0] if l not in env.CHANNELS]
                env.LABELS['gen'] += env.CHANNEL_COLORS
                data.update({l: [] for l in env.LABELS['gen']})

                env.LABELS['fit'] = list(night_dict[0]['red'].keys())
                data.update({l: [] for l in env.LABELS['fit']})
                data_initialized = True
            except Exception as e:
                raise ValueError(f"Could not initialize data structures from '{file_name}': {e}")

        for img in night_dict:
            image_idx += 1
            for c in env.CHANNELS:
                try:
                    data['idx'].append(image_idx)
                    data['channel'].append(c)

                    for label in env.LABELS['gen']:
                        if label not in img and label not in env.CHANNEL_COLORS:
                            data[label].append(None)
                        elif label == "date":
                            data[label].append(datetime.datetime.fromisoformat(img[label]))
                        elif label in env.CHANNEL_COLORS:
                            ch1,ch2 = label.split('/')
                            data[label].append(img[ch1]['mean_counts'] / img[ch2]['mean_counts'])
                        else:
                            data[label].append(img[label])
                    for label in env.LABELS['fit']:
                        data[label].append(img[c][label])
                except Exception as e:
                    raise ValueError(f"Error parsing image {image_idx} in file '{file_name}': {e}")
        
    # Renaming time related keys and creating alternatives
    data['time_unix'] = data.pop('time')
    data['date_utc'] = data.pop('date')
    data['date_local'] = []
    data['MJD'] = []
    data['hours_utc'] = []
    data['hours_local'] = []
    # This is just to make easier time of the day comparisons
    data['float_hours_utc'] = []
    data['float_hours_local'] = []
    
    mjd0 = datetime.datetime.fromisoformat('1858-01-11 00:00:00.000+00:00')

    for t in  data['date_utc']:
        data['date_local'].append(t.astimezone(env.LOCAL_TZ))
        data['MJD'].append((t - mjd0).total_seconds() / 86400)

        parsed_time = t.time()
        decimal_time = data['MJD'][-1] - int(data['MJD'][-1])

        if parsed_time > env.DAY_START_UTC:
            data['hours_utc'].append(datetime.datetime.fromisoformat(f'2025-01-01T{parsed_time}'))
            
        else:
            data['hours_utc'].append(datetime.datetime.fromisoformat(f'2025-01-02T{parsed_time}'))
            decimal_time = decimal_time + 1
        data['float_hours_utc'].append(decimal_time)


        parsed_time = data['date_local'][-1].time()
        decimal_time = sum(x * int(t) for x, t in zip([3600, 60, 1], str(parsed_time).split(':'))) / 86400

        if parsed_time > env.DAY_START_LOCAL:
            data['hours_local'].append(datetime.datetime.fromisoformat(f'2025-01-01T{parsed_time}'))
        else:
            data['hours_local'].append(datetime.datetime.fromisoformat(f'2025-01-02T{parsed_time}'))
            decimal_time = decimal_time + 1 

        data['float_hours_local'].append(decimal_time)

    # adding time related labels at the top of the labels list
    # time_unix and float_hours are not very much human readable,
    # so I removed them
    for label in ['hours_local', 'hours_utc', 'date_local', 'date_utc', 'MJD']:
        env.LABELS['gen'].insert(0, label)

    for label in ['time', 'date']:
        env.LABELS['gen'].remove(label)

    if image_idx == -1:
        raise FileNotFoundError("No valid data was extracted from any JSON file.")

    return data