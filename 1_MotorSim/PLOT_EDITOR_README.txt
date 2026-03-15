MotorSim Plot-Konfiguration
===========================

Neu:
- plot.yaml wird automatisch neben config.json erkannt.
- Alternativ sind plot.yml oder plot.json möglich.
- Das Hauptplot-Layout wird vollständig aus der Plot-Konfiguration erzeugt.
- Steuerzeiten-Plot und Steuerkreis bleiben aktiv.
- Ein separater Editor ist enthalten:

  python run_plot_style_editor.py

Wichtige Dateien:
- plot.yaml                    Standard-Konfiguration
- run_plot_style_editor.py     Startscript für den Plot-Editor
- src/motor_sim/plot_config.py Loader für YAML/JSON
- src/motor_sim/post/plotting.py generisches konfigurierbares Plotting

Unterstützte typische Keys:
- p_cyl_bar
- p_ref_compression_bar
- p_ref_expansion_bar
- V_cm3
- mdot_in_kg_s
- mdot_out_kg_s
- lift_in_mm
- lift_ex_mm
- alphaK_in
- alphaK_ex
- alphaV_in
- alphaV_ex
- A_in_mm2
- A_ex_mm2
- qdot_combustion_W
- xb_combustion
- T_cyl_K
- m_cyl_kg
- p_cyl_pa
- V_m3

Beispiel:
- rows: 1, cols: 2  => 2 Plots nebeneinander
- rows: 2, cols: 1  => 2 Plots untereinander
- rows: 2, cols: 2  => 4er-Layout
