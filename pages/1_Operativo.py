# --- TREEMAP DE TAXONOMÍA DE TAREAS (COSTO + HORAS) ---
        st.subheader("🧱 Distribución de Presupuesto y Esfuerzo por Tarea")
        
        # Agrupamos los datos sumando tanto el costo como el tiempo real
        df_treemap = df_filtrado.groupby(['Nombre del cliente', 'Tipo de tarea'])[['Costo_Devengado', 'Tiempo real']].sum().reset_index()
        
        # Filtramos para que no intente graficar tareas con costo 0 o negativo
        df_treemap = df_treemap[df_treemap['Costo_Devengado'] > 0]
        
        if not df_treemap.empty:
            # Creamos el Treemap. 'values' define el tamaño (Costo), 'custom_data' inyecta las horas
            fig_tree = px.treemap(
                df_treemap, 
                path=['Nombre del cliente', 'Tipo de tarea'], 
                values='Costo_Devengado',
                custom_data=['Tiempo real'],
                color='Nombre del cliente',
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            
            # Forzamos el diseño del texto para que muestre ambas métricas limpiamente sin hover
            fig_tree.update_traces(
                texttemplate="<b>%{label}</b><br>Costo: $%{value:,.0f}<br>Esfuerzo: %{customdata[0]:.1f} hrs",
                textposition="middle center",
                hovertemplate="<b>%{label}</b><br>Costo: $%{value:,.0f}<br>Esfuerzo: %{customdata[0]:.1f} hrs<extra></extra>"
            )
            
            fig_tree.update_layout(
                template="plotly_dark", 
                margin=dict(t=30, l=10, r=10, b=10)
            )
            
            st.plotly_chart(fig_tree, use_container_width=True)
        else:
            st.info("No hay datos suficientes para graficar el mapa de esfuerzo.")
