import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Configuración de la página de Streamlit ---
st.set_page_config(
    page_title="Pokédex Analítica",
    page_icon="📊",
    layout="wide"
)

# --- Colores para los tipos de Pokémon ---
TYPE_COLORS = {
    'normal': '#A8A77A', 'fire': '#EE8130', 'water': '#6390F0', 'electric': '#F7D02C',
    'grass': '#7AC74C', 'ice': '#96D9D6', 'fighting': '#C22E28', 'poison': '#A33EA1',
    'ground': '#E2BF65', 'flying': '#A98FF3', 'psychic': '#F95587', 'bug': '#A6B91A',
    'rock': '#B6A136', 'ghost': '#735797', 'dragon': '#6F35FC', 'dark': '#705746',
    'steel': '#B7B7CE', 'fairy': '#D685AD',
}

# --- Funciones de Carga de Datos (con caché para optimización) ---

@st.cache_data
def fetch_pokemon_data(identifier):
    """Obtiene datos de un único Pokémon."""
    try:
        url = f"https://pokeapi.co/api/v2/pokemon/{str(identifier).lower()}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        species_url = data['species']['url']
        species_response = requests.get(species_url)
        species_response.raise_for_status()
        species_data = species_response.json()

        description = next(
            (entry['flavor_text'].replace('\n', ' ').replace('\f', ' ') 
             for entry in species_data['flavor_text_entries'] if entry['language']['name'] == 'es'),
            "Descripción no disponible."
        )

        return {
            "id": data['id'], "name": data['name'].capitalize(),
            "image": data['sprites']['other']['official-artwork']['front_default'],
            "types": [t['type']['name'] for t in data['types']],
            "stats": {s['stat']['name']: s['base_stat'] for s in data['stats']},
            "height": data['height'] / 10.0, "weight": data['weight'] / 10.0,
            "description": description,
        }
    except requests.exceptions.RequestException:
        return None

@st.cache_data
def load_pokemon_for_analysis(limit=151):
    """Carga una lista de Pokémon para los análisis estadísticos."""
    all_pokemon_data = []
    url = f"https://pokeapi.co/api/v2/pokemon?limit={limit}"
    response = requests.get(url)
    if response.ok:
        results = response.json()['results']
        # --- CORRECCIÓN: Se eliminó st.progress de aquí ---
        for pokemon in results:
            data = fetch_pokemon_data(pokemon['name'])
            if data:
                flat_data = {
                    'ID': data['id'], 'Nombre': data['name'], 'Tipo Primario': data['types'][0],
                    'Tipo Secundario': data['types'][1] if len(data['types']) > 1 else None,
                    'HP': data['stats'].get('hp', 0), 'Ataque': data['stats'].get('attack', 0),
                    'Defensa': data['stats'].get('defense', 0), 'At. Especial': data['stats'].get('special-attack', 0),
                    'Def. Especial': data['stats'].get('special-defense', 0), 'Velocidad': data['stats'].get('speed', 0),
                    'Altura (m)': data['height'], 'Peso (kg)': data['weight']
                }
                all_pokemon_data.append(flat_data)
    return pd.DataFrame(all_pokemon_data)

# --- Carga de datos para análisis ---
# --- CORRECCIÓN: Usamos st.spinner para una mejor experiencia de carga ---
with st.spinner('Cargando datos para los análisis...'):
    df_pokemon = load_pokemon_for_analysis(151)

# --- Interfaz Principal con Pestañas ---
st.title("Pokédex Analítica 📊")

tab1, tab2, tab3 = st.tabs(["Pokédex", "Comparador de Stats", "Análisis de Tipos"])

# --- Pestaña 1: Pokédex ---
with tab1:
    st.header("Busca tu Pokémon")
    if 'current_pokemon_id' not in st.session_state:
        st.session_state.current_pokemon_id = 1
    
    search_term = st.text_input("Buscar por Nombre o Número:", key="search_input")
    if st.button("Buscar", key="search_button"):
        if search_term:
            st.session_state.current_pokemon_id = search_term

    pokemon = fetch_pokemon_data(st.session_state.current_pokemon_id)

    if pokemon:
        st.session_state.current_pokemon_id = pokemon['id']
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(pokemon['image'], use_container_width=True) 
        with col2:
            st.header(f"#{pokemon['id']} - {pokemon['name']}")
            type_html = "".join(
                f'<span style="background-color: {TYPE_COLORS.get(t, "#777")}; color: white; padding: 5px 10px; margin: 0 5px; border-radius: 15px; font-weight: bold;">{t.upper()}</span>'
                for t in pokemon['types']
            )
            st.markdown(type_html, unsafe_allow_html=True)
            st.info(f"**Descripción:** {pokemon['description']}")
            st.write(f"**Altura:** {pokemon['height']} m | **Peso:** {pokemon['weight']} kg")
            st.subheader("Estadísticas Base")
            for stat, value in pokemon['stats'].items():
                st.write(f"**{stat.replace('-', ' ').capitalize()}:** {value}")
                st.progress(value / 255.0)
    else:
        st.error(f"No se pudo encontrar el Pokémon '{st.session_state.current_pokemon_id}'.")

# --- Pestaña 2: Comparador de Stats ---
with tab2:
    st.header("Comparador de Pokémon")
    pokemon_list = df_pokemon['Nombre'].tolist()
    
    col1, col2 = st.columns(2)
    with col1:
        pokemon1_name = st.selectbox("Elige el primer Pokémon:", pokemon_list, index=0)
    with col2:
        pokemon2_name = st.selectbox("Elige el segundo Pokémon:", pokemon_list, index=6)

    data1 = fetch_pokemon_data(pokemon1_name.lower())
    data2 = fetch_pokemon_data(pokemon2_name.lower())

    if data1 and data2:
        stats1 = list(data1['stats'].values())
        stats2 = list(data2['stats'].values())
        stat_names = [s.replace('-', ' ').capitalize() for s in data1['stats'].keys()]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=stats1, theta=stat_names, fill='toself', name=data1['name']))
        fig.add_trace(go.Scatterpolar(r=stats2, theta=stat_names, fill='toself', name=data2['name']))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 160])),
            showlegend=True,
            title=f"Comparativa de Stats: {data1['name']} vs. {data2['name']}"
        )
        st.plotly_chart(fig, use_container_width=True)

# --- Pestaña 3: Análisis de Tipos (1ra Generación) ---
with tab3:
    st.header("Análisis de Tipos (Generación I)")

    # Gráfico 1: Distribución de Tipos Primarios
    st.subheader("Distribución de Tipos Primarios")
    type_counts = df_pokemon['Tipo Primario'].value_counts().reset_index()
    type_counts.columns = ['Tipo', 'Cantidad']
    fig1 = px.bar(type_counts, x='Tipo', y='Cantidad', color='Tipo',
                  color_discrete_map=TYPE_COLORS, title="Número de Pokémon por Tipo Primario")
    st.plotly_chart(fig1, use_container_width=True)

    # Gráfico 2: Stats Promedio por Tipo
    st.subheader("Estadísticas Promedio por Tipo Primario")
    stats_to_analyze = ['HP', 'Ataque', 'Defensa', 'At. Especial', 'Def. Especial', 'Velocidad']
    selected_stat = st.selectbox("Selecciona una estadística para analizar:", stats_to_analyze)
    
    avg_stats = df_pokemon.groupby('Tipo Primario')[selected_stat].mean().sort_values(ascending=False).reset_index()
    fig2 = px.bar(avg_stats, x='Tipo Primario', y=selected_stat, color='Tipo Primario',
                  color_discrete_map=TYPE_COLORS, title=f"Promedio de '{selected_stat}' por Tipo")
    st.plotly_chart(fig2, use_container_width=True)

    # Gráfico 3: Correlación entre Ataque y Defensa
    st.subheader("Relación entre Ataque y Defensa")
    fig3 = px.scatter(df_pokemon, x='Ataque', y='Defensa', color='Tipo Primario',
                      hover_name='Nombre', title="Correlación Ataque vs. Defensa",
                      color_discrete_map=TYPE_COLORS)
    st.plotly_chart(fig3, use_container_width=True)



# --- Fin de la aplicación Pokédex Analítica ---