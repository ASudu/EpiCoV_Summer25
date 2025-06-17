import pycountry # to standardize country names
import difflib # to get close matches for country names
import pycountry_convert as pc # to convert country names to ISO codes

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
    
    # Replace NaNs with a sentinel value (e.g., -1)
    df[col_to_plot] = df[value_column].fillna(-1)

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

def choropleth_continent(df, value_column, color_scale="balance", title=None, label=None, hover_data=None):
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
        df_cont['hover_text'] = ("Population: " + df_cont['population_2020'].map('{:,}'.format) +
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