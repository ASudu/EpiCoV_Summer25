import pycountry # to standardize country names
import difflib # to get close matches for country names
import pycountry_convert as pc # to convert country names to ISO codes
import re # to clean up age strings
import pandas as pd # for DataFrame handling
import numpy as np # for numerical operations
import matplotlib.pyplot as plt  # For plotting histograms

# For plotting
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ------------------------------ GEOGRAPHICAL FNS ------------------------------ 
def get_country_mapping()-> tuple:
    """Precompute a mapping of country names to their standard names and variants.
    This function creates a set of country names in lowercase and a mapping
    from lowercase names to the standard country name.
    """
    # Precompute country name variants
    country_names = set()
    name_map = {}

    for country in pycountry.countries:
        variants = {country.name}
        if hasattr(country, 'official_name'):
            variants.add(country.official_name)
        if hasattr(country, 'common_name'):
            variants.add(country.common_name)
        
        for variant in variants:
            lower_variant = variant.lower()
            country_names.add(lower_variant)
            name_map[lower_variant] = country.name  # map to standard name
    
    return country_names, name_map

def standardize_country_name(name:str) -> str:
    """Standardize a country name to its official name using pycountry and fuzzy matching.
    This function attempts to look up the country name using pycountry.
    If the name is not found, it uses fuzzy matching to find the closest match
    from a precomputed set of country names.

    Args:
        name (str): Name of the country to standardize.
    """
    country_names, name_map = get_country_mapping()
    name_lower = name
    if isinstance(name, str):
        name_lower = name.strip().lower()

        # Try direct lookup
        try:
            return pycountry.countries.lookup(name).name
        except LookupError:
            # Fallback: fuzzy match
            closest = difflib.get_close_matches(name_lower, country_names, n=1, cutoff=0.8)
            if closest:
                return name_map[closest[0]]
            return name  # Return original if no close match
    return name  # Return as is if not a string

def get_continent(country_name: str) -> str:
    """Get the continent name for a given country name.
    This function uses pycountry to look up the country and then converts
    the country code to a continent name using pycountry_convert.
    """
    try:
        # Normalize the country name using pycountry
        country = pycountry.countries.lookup(country_name)
        # Get the ISO alpha-2 country code
        country_code = country.alpha_2
        # Convert to continent code
        continent_code = pc.country_alpha2_to_continent_code(country_code)
        # Convert to full continent name
        continent_name = pc.convert_continent_code_to_continent_name(continent_code)
        return continent_name
    except (LookupError, KeyError):
        return "Unknown"

# ------------------------------ DATAFRAME FNS ------------------------------
def col_fillna(df, column: str, fill_value: float = -1.0) -> pd.DataFrame:
    """Fill NaN values in a DataFrame column with a specified value.

    Args:
        df (pd.DataFrame): The DataFrame to modify.
        column (str): The column name to fill NaN values.
        fill_value (float, optional): The value to use for filling NaNs. Defaults to 0.0.

    Returns:
        pd.DataFrame: The modified DataFrame with NaNs filled.
    """
    new_col = column + "_filled"
    df[new_col] = df[column].fillna(fill_value)
    return df

def map_age_to_group(age):
    try:        
        # Handle string inputs
        if isinstance(age, str):
            age = age.strip().lower()
            # Clean input
            if pd.isna(age) or age == 'unknown':
                return 'unknown'
            
            # Convert ranges to approximate midpoints (e.g., "50-54" -> 52)
            if '-' in age:
                parts = [x.strip() for x in age.split('-')]
                if all(part.isdigit() for part in parts): # check if both parts are numbers
                    age = str((int(parts[0]) + int(parts[1])) // 2)
            
            # Convert ranges with 'to' to approximate midpoints (e.g., "50 to 54" -> 52)
            if 'to' in age:
                parts = [x.strip() for x in age.split('to')]
                if all(part.isdigit() for part in parts): # check if both parts are numbers
                    age = str((int(parts[0]) + int(parts[1])) // 2)
            
            # Convert strings like ">70", ">50" to numeric estimates
            if '>' in age:
                num = re.findall(r'\d+', age)
                if num:
                    age = int(num[0]) + 1  # assume ">70" means at least 71
                else:
                    print('> in age but no number found')
                    return 'unknown'  # if no number found, return unknown
            
            # Convert fractional or float values
            if isinstance(age, str) and re.fullmatch(r'\d+(\.\d+)?', age):
                age = float(age)
            
            # Handle months/days
            if isinstance(age, str) and any(unit in age for unit in ['month', 'day']):
                print('age in months or days')
                return '<5'
        
        # Final conversion to float
        age = float(age)
        
        # Assign GBD group
        if age < 5:
            return '<5'
        elif 5 <= age <= 14:
            return '5-14'
        elif 15 <= age <= 49:
            return '15-49'
        elif 50 <= age <= 69:
            return '50-69'
        elif age >= 70:
            return '>70'
        else:
            return 'unknown'
    except:
        return 'unknown'

# ------------------------------ DOMAIN SPECIFIC FNS ------------------------------
def standardize_vaccine_status(df, col="Last vaccinated"):
    """Function to standardize vaccination status in a DataFrame column.

    Args:
        df (pd.DataFrame): The DataFrame containing the vaccination status column.
        col (str, optional): The name of the column to standardize. Defaults to "Last vaccinated".

    Returns:
        pd.DataFrame: The DataFrame with the standardized vaccination status column.
    """
    vacc_map = {("not vaccinated", "non-vaccinated", "non", "unvaccinated"): "no",
                ("unknown", "provide details if applicable", "INFLU 10/19", "Suspeito de reinfecção"): "unknown",
                ("partially vaccinated", "partially", "yes (1st dose)", "yes (1 dose)"): "partial",
                ("fully vaccinated", "fully", "yes (2nd dose)", "yes (2 doses)","yes (3rd dose)","yes (booster)"): "full"}
    
    # Use this map to standardize the 'Last vaccinated' column
    def map_vacc_status(status):
        if isinstance(status, str):
            status_lower = status.strip().lower()
            for keys, value in vacc_map.items():
                if status_lower in keys:
                    return value
        return "unknown"
    df[col] = df[col].apply(map_vacc_status)
    return df

def map_pat_status(df, df_pat, col):
    # mapping from target df column name to column name in df_pat
    col_map = {
        "clinical_status":"clinical status",
        "hospital_status": "hospital status",
        "severity": "severity",
        "who_category": "category"
    }
    # target = col_map.get(col.lower().replace(" ", "_"), col.lower().replace("_", " "))
    target = col
    if target not in df_pat.columns:
        raise ValueError(f"Mapping column '{target}' not found in df_pat")
    # build exact and lowercase lookup dicts
    exact_map = df_pat.set_index("patient_status")[target].to_dict()
    lower_map = { (k.lower() if isinstance(k, str) else k): v for k, v in exact_map.items() if isinstance(k, str) }
    def _map_value(x):
        if pd.isna(x):
            return np.nan
        # exact match
        if x in exact_map:
            return exact_map[x]
        # case-insensitive match
        if isinstance(x, str) and x.lower() in lower_map:
            return lower_map[x.lower()]
        return np.nan
    df[col] = df["Patient status"].apply(_map_value)
    return df

def inclusion_exclusion(df):
    """
    Counting meaningful samples based on inclusion/exclusion criteria from Ramarao-Milne (2022) (https://www.csbj.org/article/S2001-0370(22)00219-7/fulltext).
    """

    total = df.shape[0]
    removed = 0

    # Exclusion 1: Patient status annotated as ‘Unknown’
    unknown_stat = [x for x in df["Patient status"].unique() if str(x).lower().startswith("u")]
    u_count = df[df["Patient status"].isin(unknown_stat)].shape[0]
    removed += u_count
    df = df[~df["Patient status"].isin(unknown_stat)]
    print(f"Exclusion 1: Removed {u_count} samples with 'Unknown' patient status.")

    # Exclusion 2: Ambiguous annotations that cannot be associated with better or worse disease outcome including, ‘Live’, ‘Hospitalized’, ‘Outpatient’, ‘Symptomatic’, ‘Released’, ‘Ambulatory’, ‘Inpatient’, ‘other’.
    ambiguous_stat = [x for x in df["Patient status"].unique() if str(x).lower().startswith(("li", "hos", "out", "sy", "rel", "amb", "inp","in-p", "oth"))]
    a_count = df[df["Patient status"].isin(ambiguous_stat)].shape[0]
    removed += a_count
    df = df[~df["Patient status"].isin(ambiguous_stat)]
    print(f"Exclusion 2: Removed {a_count} samples with ambiguous patient status.")

    # Exclusion 3: Unannotated (missing patient status)
    na_count = df["Patient status"].isna().sum()
    removed += na_count
    df = df[~df["Patient status"].isna()]
    print(f"Exclusion 3: Removed {na_count} samples with missing patient status.")

    # Inclusion 1: ‘Deceased’, ‘Severe’, ‘Critical’, ‘Dead’, ‘Post-mortem’, ‘Death’ and ‘ICU’.
    severe_stat = [x for x in df["Patient status"].unique() if str(x).lower().startswith(("de", "se", "cr", "po", "ic"))]
    severe_count = df[df["Patient status"].isin(severe_stat)].shape[0]
    print(f"Inclusion 1: Included {severe_count} samples with severe patient status.")

    # Inclusion 2: ‘Asymptomatic’, ‘Mild’, ‘Mild clinical signs without hospitalisation’, and ‘Recovered’
    mild_stat = [x for x in df["Patient status"].unique() if str(x).lower().startswith(("as", "mi", "re"))]
    mild_count = df[df["Patient status"].isin(mild_stat)].shape[0]
    print(f"Inclusion 2: Included {mild_count} samples with mild patient status.")

    df = df[df["Patient status"].isin(severe_stat + mild_stat)]
    final_count = df.shape[0]
    print(f"Total samples after applying inclusion/exclusion criteria: {final_count} (Removed {removed} samples out of {total})")
    print(f"Percentage of meaningful samples: {100*final_count/total:.2f}%")

# ------------------------------ PLOTTING FNS ------------------------------
def plot_hist(df, col, n_bins=15, order=None, sort_by_counts=False):
    """
    Plots a histogram (for numeric columns) or a bar chart (for categorical columns).
    Allows forcing a custom ordering of categorical bars via `order` or sorting by counts.
    Args:
        df (pd.DataFrame): input DataFrame
        col (str): column to plot
        n_bins (int): bins for numeric histogram (ignored for categorical)
        order (list[str]|None): explicit category order for categorical plots
        sort_by_counts (bool): if True, order categories by descending frequency
    """
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np

    s = df[col].dropna()

    plt.figure(figsize=(10, 6))

    # If numeric, fallback to histogram
    if pd.api.types.is_numeric_dtype(s):
        counts, bins, patches = plt.hist(
            s,
            bins=n_bins,
            edgecolor='black',
            color='skyblue'
        )
        # annotate
        for p in patches:
            h = p.get_height()
            if h > 0:
                plt.text(p.get_x() + p.get_width() / 2, h + max(counts) * 0.01, f'{int(h)}',
                         ha='center', va='bottom', fontsize=9)
        plt.title(f'Frequency Distribution of {col}', fontsize=14)
        plt.xlabel(col, fontsize=12)
        plt.ylabel('Frequency (Count)', fontsize=12)
        plt.grid(axis='y', alpha=0.5)
        plt.tight_layout()
        plt.show()
        return

    # Categorical branch
    # determine category order
    if order is not None:
        cats = list(order)
    elif sort_by_counts:
        cats = s.value_counts().index.tolist()
    else:
        # preserve first-seen order
        cats = pd.unique(s).tolist()

    counts = s.value_counts().reindex(cats, fill_value=0)

    x = np.arange(len(cats))
    bars = plt.bar(x, counts.values, color='skyblue', edgecolor='black')
    # annotate bar labels
    for i, v in enumerate(counts.values):
        if v > 0:
            plt.text(i, v + max(counts.values) * 0.01, f'{int(v)}', ha='center', va='bottom', fontsize=9)

    plt.xticks(x, cats, rotation=45, ha='right')
    plt.title(f'Frequency Distribution of {col}', fontsize=14)
    plt.xlabel(col, fontsize=12)
    plt.ylabel('Frequency (Count)', fontsize=12)
    plt.grid(axis='y', alpha=0.5)
    plt.tight_layout()
    plt.show()
    plt.close()

def choropleth_world(df, value_column, color_scale="balance", title=None, hover_data=None, label=None):
    """Plot a choropleth map of the world using Plotly Express.

    Args:
        df (pd.DataFrame): DataFrame containing country data.
        value_column (str): Column name in the DataFrame to plot on the map.
        color_scale (Union[str, dict], optional): The color map to use. If custom one define it as a dict, else use str. Defaults to "balance".
        title (str, optional): Plot title. Defaults to None.
        hover_data (dict, optional): Boolean dict showing which columns of the dataframe to show on hovering over the country. Defaults to None.
        label (str, optional): Colorbar title. Defaults to None.
    """
    col_to_plot = value_column + "_filled"
    
    hover = hover_data if hover_data else {k: True for k in df.columns}

    fig = px.choropleth(
            df,
            locations='country',
            locationmode='country names',
            color=col_to_plot,
            color_continuous_scale=color_scale,
            title=title,
            labels={col_to_plot: label},
            hover_name='country',
            hover_data=hover,
            projection='natural earth',
            range_color=[df[col_to_plot].min(), df[col_to_plot].max()]  # Correct usage
        )

    fig.update_geos(showframe=True, showcoastlines=True)
    fig.update_layout(
        margin={"r":0,"t":40,"l":0,"b":0},
        title_x=0.5,
        width=1200,
        font=dict(size=20),
        title_font=dict(size=25),
        legend_font=dict(size=20),
        xaxis=dict(title_font=dict(size=20), tickfont=dict(size=18)),
        yaxis=dict(title_font=dict(size=20), tickfont=dict(size=18))
    )

    # Rename colorbar title
    fig.update_coloraxes(
        colorbar_title=label,
        cmin=0  # Prevent -1 from affecting the color scale
    )

    return fig

def choropleth_continent(df, value_column, color_scale="balance", title=None, label=None, hover_data=None, YEAR="2020"):
    """Plot a choropleth map of continents using Plotly Graph Objects.
    This function creates a 2x3 grid of choropleth maps, one for each continent.

    Args:
        df (pd.DataFrame): DataFrame containing country data.
        value_column (str): Column name in the DataFrame to plot on the map.
        color_scale (Union[str, dict], optional): The color map to use. If custom one define it as a dict, else use str. Defaults to "balance".
        title (str, optional): Plot title. Defaults to None.
        label (str, optional): Colorbar title. Defaults to None.
    """
    from plotly.colors import make_colorscale

    # Preset map bounds for continents
    continent_configs = {
        'Africa': dict(projection_type='natural earth', lonaxis_range=[-20, 60], lataxis_range=[-35, 40]),
        'Asia': dict(projection_type='natural earth', lonaxis_range=[25, 150], lataxis_range=[-10, 60]),
        'Europe': dict(projection_type='natural earth', lonaxis_range=[-25, 45], lataxis_range=[35, 70]),
        'North America': dict(projection_type='natural earth', lonaxis_range=[-170, -40], lataxis_range=[5, 80]),
        'South America': dict(projection_type='natural earth', lonaxis_range=[-90, -30], lataxis_range=[-60, 15]),
        'Oceania': dict(projection_type='natural earth', lonaxis_range=[110, 180], lataxis_range=[-50, 10])
    }

    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=list(continent_configs.keys()),
        specs=[[{'type': 'choropleth'}]*3]*2
    )

    row_col_map = {i: (i // 3 + 1, i % 3 + 1) for i in range(6)}
    col_to_plot = value_column + "_filled"

    # Add traces and update geo settings
    for i, (continent, geo_cfg) in enumerate(continent_configs.items()):
        row, col = row_col_map[i]
        df_cont = df[df['continent'] == continent]
        df_cont['hover_text'] = ("Population: " + df_cont[f'population_{YEAR}'].map('{:,}'.format) +
    "<br>"+label+": " + df_cont[col_to_plot].round(2).astype(str))

        subplot_geo_id = "geo" if i == 0 else f"geo{i+1}"

        trace = go.Choropleth(
            locations=df_cont['country'],
            locationmode='country names',
            z=df_cont[col_to_plot],
            colorscale=color_scale,
            zmin=df_cont[col_to_plot].min(),
            zmax=df_cont[col_to_plot].max(),
            marker_line_color='white',
            marker_line_width=0.5,
            showscale=True,
            colorbar=dict(
                title=label,
                orientation='h',
                thickness=10,
                len=0.25,
                xanchor='center',
                x=0.17 + 0.33 * (col - 1),
                y=-0.1 if row == 2 else 0.53
            ),
            text=df_cont['hover_text'],
            hovertemplate="<b>%{location}</b><br>%{text}<extra></extra>",
            autocolorscale=False,
            geo=subplot_geo_id
        )

        fig.add_trace(trace, row=row, col=col)

        fig.update_layout({
            subplot_geo_id: dict(
                showframe=True,
                showcoastlines=True,
                showcountries=True,
                countrycolor="white",
                showland=False,
                landcolor="white",
                bgcolor="white",
                lataxis_range=geo_cfg['lataxis_range'],
                lonaxis_range=geo_cfg['lonaxis_range'],
                projection_type=geo_cfg['projection_type']
            )
        })

    fig.update_layout(
        title_text=title,
        title_x=0.5,
        height=600,
        width=1200,
        margin={"r": 20, "t": 60, "l": 20, "b": 60},
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=20),
        title_font=dict(size=25),
        legend_font=dict(size=20),
        xaxis=dict(title_font=dict(size=20), tickfont=dict(size=18)),
        yaxis=dict(title_font=dict(size=20), tickfont=dict(size=18))
    )

    return fig

def plot_dominant_choropleth(df,value_column, color_map, title, year="2020", save_path=None):
    # 1. Group by country and value_column to count entries
    grouped = df.groupby(['country', value_column]).size().reset_index(name='count')

    # 2. Pivot to wide format: one row per country, one column per age group
    pivot_df = grouped.pivot(index='country', columns=value_column, values='count').fillna(0)

    # 3. Determine the dominant (most frequent) age group for each country
    new_col = value_column + '_dominant'
    pivot_df[new_col] = pivot_df.idxmax(axis=1)
    # pivot_df['total'] = pivot_df.sum(axis=1)


    # 5. Map dominant age group to color
    pivot_df['color'] = pivot_df[new_col].map(color_map)

    # 6. Build hover text
    hover_texts = []
    for idx, row in pivot_df.iterrows():
        hover_parts = [f"<b>{idx}</b>"]
        for age_group in color_map:
            hover_parts.append(f"{age_group}: {int(row.get(age_group, 0))}")
        hover_texts.append("<br>".join(hover_parts))

    # 7. Build choropleth
    fig = go.Figure(data=go.Choropleth(
        locations=pivot_df.index,
        locationmode='country names',
        z=[list(color_map.keys()).index(age) for age in pivot_df[new_col]],
        text=hover_texts,
        hoverinfo="text",
        colorscale=[[i / (len(color_map)-1), color] for i, color in enumerate(color_map.values())],
        colorbar=dict(
            tickvals=list(range(len(color_map))),
            ticktext=list(color_map.keys()),
            title=title
        ),
        showscale=True
    ))

    fig.update_layout(
        title={
        'text': f"{title} per Country (Hover for Full Distribution) | {year}",
        'x': 0.5,
        'xanchor': 'center'
        },
        geo=dict(
        showframe=False,
        showcoastlines=False,
        projection_type='natural earth',
        fitbounds="locations",
        lataxis_showgrid=False,
        lonaxis_showgrid=False
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        font=dict(size=20),
        title_font=dict(size=28),
        legend_font=dict(size=20),
        xaxis=dict(title_font=dict(size=20), tickfont=dict(size=18)),
        yaxis=dict(title_font=dict(size=20), tickfont=dict(size=18))
    )

    if save_path:
        fig.write_html(save_path)

    return fig