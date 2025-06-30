import pycountry # to standardize country names
import difflib # to get close matches for country names
import pycountry_convert as pc # to convert country names to ISO codes
import re # to clean up age strings
import pandas as pd # for DataFrame handling

# For plotting
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, title_x=0.5, width=1200)

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
        paper_bgcolor='white'
    )

    return fig

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

def map_age_to_group(age):
    try:
        # Clean input
        if pd.isna(age) or age == 'unknown':
            return 'unknown'
        
        # Convert ranges to approximate midpoints (e.g., "50-54" -> 52)
        if '-' in age:
            parts = age.split('-')
            if all(part.isdigit() for part in parts): # check if both parts are numbers
                age = str((int(parts[0]) + int(parts[1])) // 2)
        
        # Convert strings like ">70", ">50" to numeric estimates
        if '>' in age:
            num = re.findall(r'\d+', age)
            if num:
                age = int(num[0]) + 1  # assume ">70" means at least 71
            else:
                return 'unknown'  # if no number found, return unknown
        
        # Convert fractional or float values
        if isinstance(age, str) and re.fullmatch(r'\d+(\.\d+)?', age):
            age = float(age)
        
        # Handle months/days
        if isinstance(age, str) and any(unit in age for unit in ['month', 'day']):
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
        margin=dict(l=0, r=0, t=40, b=0)
    )

    if save_path:
        fig.write_html(save_path)

    return fig