#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 23 13:44:10 2024
@author: mayk
"""
#%% Sources and manuals used:
# https://github.com/EnergieID/KNMI-py
# https://www.knmi.nl/kennis-en-datacentrum/achtergrond/data-ophalen-vanuit-een-script
# https://www.daggegevens.knmi.nl/klimatologie/uurgegevens


#%% Retrieve KNMI data through API
from knmy import knmy
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
import os
import requests
import json
os.system('clear')

start   = '20240101'
end     = '20241231'
variables_selected = ['TEMP']
inseason=False
parse=True

stations_selected1 = [260] # De Bilt
disclaimer, stations1, variables, data_260 = knmy.get_hourly_data(stations=stations_selected1, start=start, end=end,inseason=inseason, variables=variables_selected, parse=parse)

stations_selected2 = [380] # Maastricht
disclaimer, stations2, variables, data_380 = knmy.get_hourly_data(stations=stations_selected2, start=start, end=end,inseason=inseason, variables=variables_selected, parse=parse)



# 1. Read the CSV data without parsing dates
df = data_260
df['TD'] = df['TD'] / 10  # Convert temperature to Celsius
df['T'] = df['T'] / 10  # Convert temperature to Celsius
df['T_260'] = df['T']

df = df.drop('STN', axis=1)
df = df.drop('T10N', axis=1)

#combine two dataframes, where df2.T is put into df.T_380
df2 = data_380
df['T_380'] = df2['T']/10

# 2. Combine 'YYYYMMDD' and 'HH' to create a datetime column
df['datetime'] = df['YYYYMMDD'].astype(str) + (df['HH'].astype(int) - 1).astype(str).str.zfill(2) + '00'  # Subtract 1 from HH, Adding '00' for minutes and seconds
df['datetime'] = pd.to_datetime(df['datetime'], format='%Y%m%d%H%M%S')
df = df.set_index('datetime')
print(df)


# Save data to excel
output_filename = f"Q_heatpump_De_Bilt_{start}_{end}" 
df.to_excel(output_filename+".xlsx", index=False)
print(f"Data saved to {output_filename}")




# Show all stations information: knmi.stations
# station: 260 = De Bilt, 138 en 380 = Maastricht, 616 = Amsterdam, 250 = Terschelling, 


# print(disclaimer)
# print(stations)
# print(variables)
# print(data)
# print(df.legend)



#%% Heat demand calculation

T_heat_setpoint = 18  # Setpoint temperature in Celsius of building
dT_heat = T_heat_setpoint - df['T_260']  # Temperature difference between setpoint and actual temperature
dT_heat[dT_heat < 1] = 0  # Set heating off when dT is < 1 values to zero, as no heat demand when T_260 is above setpoint
Q_heat = dT_heat * (6.0/T_heat_setpoint)  # hourly values, at 0'C heat load = 7.5kW (25% less than 10kW), thus dt 20'K = 7.5kW, thus 20*X=7,500, thus X=375W/'K - Convert temperature difference to heat demand in kWh
COP_heat = 5.5 - dT_heat*(2.5/T_heat_setpoint)  # COP at 20'C Ambient is 5.5, and at 0'C it is 3.5, thus 20'K lowers it with 2.0 thus 0.1 per 1'K in dT -  Coefficient of Performance (COP) of the heat pump, assuming a linear decrease with increasing temperature difference
E_WP_heating_input = Q_heat / COP_heat  # kW electricity per hour (thus is also kWh) convert heat demand to electrical input energy in kWh


T_cool_setpoint = 21  # Setpoint temperature in Celsius of building
dT_cool = df['T_260'] - T_cool_setpoint
dT_cool[dT_cool < 1] = 0  # Only enable cooling when Tamb > 25'C , as no cooling demand when T_260 is above setpoint
Q_cool = dT_cool * (5/10) # kW-th so 4.0kW cooling demand at 10'K above cooling setpoint, so 33'C ambient temperature
COP_cool = 4.5 - dT_cool*(2.0/23)
E_WP_cooling_input = Q_cool / COP_cool  # kW electricity per hour (thus is also kWh) convert cooling demand to electrical input energy in kWh



Q_heat_sum = Q_heat.sum()
Q_heat_avg = Q_heat[Q_heat != 0].mean()
E_WP_heating_input_sum = E_WP_heating_input.sum()
COP_heat_avg = Q_heat_sum / E_WP_heating_input_sum


print(f"Total heat demand: {Q_heat_sum:_.0f} kWh-thermal average over the year".replace('_', '.'))
print(f"Gas eq. demand: {Q_heat_sum/10:.0f} m3/year")
print(f"Average heat demand: {Q_heat_avg:.1f} kW-thermal")
print(f"Average COP of heat pump: {COP_heat_avg:.2f}")
print(f"Total electricity input for heating: {E_WP_heating_input_sum:.0f} kWh/year")


Q_cool_sum = Q_cool.sum()
Q_cool_avg = Q_cool[Q_cool != 0].mean()
E_WP_cooling_input_sum = E_WP_cooling_input.sum()
COP_cool_avg = Q_cool_sum / E_WP_cooling_input_sum

print(f"Total cooling demand: {Q_cool_sum:_.0f} kWh-thermal average over the year".replace('_', '.'))
print(f"Average cooling demand: {Q_cool_avg:.1f} kW-thermal")
print(f"Average COP of cooling airco: {COP_cool_avg:.2f}")
print(f"Total electricity input for cooling: {E_WP_cooling_input_sum:.0f} kWh/year")



#%% Electricity cost by Entsoe data
DA = pd.read_csv("outfile_DA_60min_NL_20240101_to_20250101.csv")
print(DA)

# Convert datetime to pandas datetime and handle timezone
DA['datetime'] = pd.to_datetime(DA['datetime'], utc=True)
DA.set_index('datetime', inplace=True)

# Convert timezone-aware to timezone-naive for compatibility
DA.index = DA.index.tz_convert(None)

price = DA['DA_price']  # Keep in EUR/MWh

# Align price data with main dataframe
price_aligned = price.reindex(df.index, method='nearest')

cost_heating_per_hour = E_WP_heating_input * price_aligned / 1000  # cost per hour in EUR (convert kWh to MWh)
df['cost_heating_per_hour'] = cost_heating_per_hour

cost_cooling_per_hour = E_WP_cooling_input * price_aligned / 1000  # cost per hour in EUR (convert kWh to MWh)
df['cost_cooling_per_hour'] = cost_cooling_per_hour

total_heating_cost = cost_heating_per_hour.sum()
total_cooling_cost = cost_cooling_per_hour.sum()

print(f"Total electricity cost for heating: {total_heating_cost:_.0f} EUR/year".replace('_', '.'))
print(f"Total electricity cost for cooling: {total_cooling_cost:_.0f} EUR/year".replace('_', '.'))

avg_heating_cost_per_MWh = total_heating_cost / E_WP_heating_input_sum * 1000
avg_cooling_cost_per_MWh = total_cooling_cost / E_WP_cooling_input_sum * 1000

print(f"Average electricity cost for heating: {avg_heating_cost_per_MWh:.1f} EUR/MWh".replace('_', '.'))
print(f"Average electricity cost for cooling: {avg_cooling_cost_per_MWh:.1f} EUR/MWh".replace('_', '.'))

average_price_per_MWh = price_aligned.mean()
print(f"Average electricity price over the year: {average_price_per_MWh:.1f} EUR/MWh")





#%% Electricity emissions on hourly basis by NED.nl data
import pandas as pd

# Load hourly electricity emissions data from NED.nl
ned_emissions_file = "data_export_NED_CO2_20240101_to_20241231_hourly.xlsx"
ned_emissions_df = pd.read_excel(ned_emissions_file)
print(ned_emissions_df)

# The file has columns: 'validfrom' and 'emissionfactor'
# Convert 'validfrom' to pandas datetime if not already
ned_emissions_df['datetime'] = pd.to_datetime(ned_emissions_df['validfrom'])

# Set datetime as index for easy alignment
ned_emissions_df.set_index('datetime', inplace=True)

# Convert timezone-aware datetime to timezone-naive for compatibility
ned_emissions_df.index = ned_emissions_df.index.tz_localize(None)

# Align emissions data with the main dataframe (df)
# Assume df.index is also datetime and at hourly frequency
# If not, convert df.index to datetime
if not pd.api.types.is_datetime64_any_dtype(df.index):
    df.index = pd.to_datetime(df.index)

# Reindex emissions to match df, forward/backward fill if needed
co2_emissions = ned_emissions_df['emissionfactor'].reindex(df.index, method='nearest') * 1000 # gCO2/kWh
print(co2_emissions.describe())

# Calculate hourly emissions for heat pump electricity input
# E_WP_heating_input is in kWh per hour
E_WP_heating_input_CO2 = E_WP_heating_input * co2_emissions  # gCO2 per hour
E_WP_cooling_input_CO2 = E_WP_cooling_input * co2_emissions  # gCO2 per hour

# Add to df for further analysis/plotting if desired
df['E_WP_heating_input_CO2_g'] = E_WP_heating_input_CO2
df['E_WP_cooling_input_CO2_g'] = E_WP_cooling_input_CO2

# Calculate total annual CO2 emissions for heating
total_CO2_emissions_kg_heating = E_WP_heating_input_CO2.sum() / 1000  # convert g to kg
total_CO2_emissions_kg_cooling = E_WP_cooling_input_CO2.sum() / 1000  # convert g to kg

# Calculate average CO2 emissions per kWh for heat pump+
avg_CO2_per_Q_heatpump = (E_WP_heating_input_CO2.sum() / Q_heat.sum()) if Q_heat.sum() > 0 else 0
avg_CO2_per_kWh_heatpump = (E_WP_heating_input_CO2.sum() / E_WP_heating_input.sum()) if E_WP_heating_input.sum() > 0 else 0
avg_CO2_per_Q_coolpump = (E_WP_cooling_input_CO2.sum() / Q_cool.sum()) if Q_cool.sum() > 0 else 0
avg_CO2_per_kWh_coolpump = (E_WP_cooling_input_CO2.sum() / E_WP_cooling_input.sum()) if E_WP_cooling_input.sum() > 0 else 0



# Calculate average CO2 emissions from source
avg_CO2_source = co2_emissions.mean()

print(f"Total CO2 emissions for heat pump heating: {total_CO2_emissions_kg_heating:_.0f} kg/year".replace('_', '.'))
print(f"Average CO2 emissions per kWh for heat pump: {avg_CO2_per_kWh_heatpump:.1f} gCO2/kWh")


print(f"Total CO2 emissions for cooling airco: {total_CO2_emissions_kg_cooling:_.0f} kg/year".replace('_', '.'))
print(f"Average CO2 emissions per kWh for cooling airco: {avg_CO2_per_kWh_coolpump:.1f} gCO2/kWh")

print(f"Average CO2 emissions NL 2024: {avg_CO2_source:.1f} gCO2/kWh")









#%% Plotly HTML plotting for Heat Pump / Heating
# Create subplots
fig = make_subplots(rows=5, cols=1, subplot_titles=(
    f"Ambient Temperature NL: (De Bilt) Avg: {df['T_260'].mean():.1f}°C, Min: {df['T_260'].min():.1f}°C, Max: {df['T_260'].max():.1f}°C",
    f"Heating: {Q_heat.sum()/10.5:.0f} m3 gas eq. Heat_max = {Q_heat.max():.1f} kWth, COP_min = {COP_heat.min():.1f}, COP_max = {COP_heat.max():.1f}",
    f"Heating avg: {Q_heat[Q_heat != 0].mean():.1f} kWth, Heatpump avg: {E_WP_heating_input[E_WP_heating_input != 0].mean():.1f} kWe, COP avg: {COP_heat_avg:.1f}, Elec input: {E_WP_heating_input.sum():.0f} kWh/y",
    f"Heatpump avg: {avg_CO2_per_Q_heatpump:.1f} gCO2/kWh-th, {avg_CO2_per_kWh_heatpump:.1f} gCO2/kWh, NL 2024 avg: {avg_CO2_source:.1f} gCO2/kWh, Total: {total_CO2_emissions_kg_heating:_.0f} kg/y".replace('_', '.'),
    f"Eletricity: Heatpump avg: {avg_heating_cost_per_MWh:.1f} EUR/MWh, Market avg : {average_price_per_MWh:.0f} EUR/MWh, ratio: {100*avg_heating_cost_per_MWh/average_price_per_MWh:,.0f}%, Total: {total_heating_cost:_.0f} EUR/y".replace('_', '.')
))

# Temperature over time plot
fig.add_trace(go.Scatter(x=df.index, y=df["T_260"], mode='lines', name=f"KNMI Temperature at Station: {stations1['name'][260]}"), row=1, col=1)
#fig.add_trace(go.Scatter(x=df.index, y=df["T_380"], mode='lines', name=f"KNMI Temperature at Station: {stations2['name'][380]}"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=dT_heat, mode='lines', name='dT_heat'), row=1, col=1)

fig.update_xaxes(title_text="Date", row=1, col=1)
fig.update_yaxes(title_text="Temperature [°C] / Power in kW", row=1, col=1)

# Heating power and COP plot
fig.add_trace(go.Scatter(x=df.index, y=Q_heat, mode='lines', name='Q_heat'), row=2, col=1)
fig.add_trace(go.Scatter(x=df.index, y=COP_heat, mode='lines', name='COP_heat'), row=2, col=1)
fig.add_trace(go.Scatter(x=df.index, y=E_WP_heating_input, mode='lines', name='E_WP_heating_input'), row=2, col=1)

fig.update_xaxes(title_text="Date", row=2, col=1)
fig.update_yaxes(title_text="Power in kW / COP", row=2, col=1)

# Histogram plot for heating
data_hist1 = COP_heat 
fig.add_trace(go.Histogram(x=data_hist1, name='COP_heat', autobinx=False, xbins=dict(start=min(data_hist1), end=max(data_hist1), size=0.25), histnorm=''), row=3, col=1)

data_hist2 = Q_heat
fig.add_trace(go.Histogram(x=data_hist2, name='Q_heat', autobinx=False, xbins=dict(start=min(data_hist2), end=max(data_hist2), size=0.25), histnorm=''), row=3, col=1)

data_hist3 = E_WP_heating_input
fig.add_trace(go.Histogram(x=data_hist3, name='E_WP_heating_input', autobinx=False, xbins=dict(start=min(data_hist3), end=max(data_hist3), size=0.25), histnorm=''), row=3, col=1)

fig.update_xaxes(title_text="kW", row=3, col=1)
fig.update_yaxes(title_text="Occurrence [hours/year]", row=3, col=1) # , tickformat=".0%"

# CO2 Emissions subplot for heating
fig.add_trace(go.Scatter(x=df.index, y=co2_emissions, mode='lines', name='CO2 Source Emissions', line=dict(color='red')), row=4, col=1)
fig.add_trace(go.Scatter(x=df.index, y=E_WP_heating_input_CO2, mode='lines', name='Heat Pump CO2 Emissions', line=dict(color='orange')), row=4, col=1)

fig.update_xaxes(title_text="Date", row=4, col=1)
fig.update_yaxes(title_text="CO2 Emissions [gCO2/kWh]", row=4, col=1)

# Cost subplot for heating
fig.add_trace(go.Scatter(x=df.index, y=cost_heating_per_hour, mode='lines', name='Heating Cost per Hour', line=dict(color='green')), row=5, col=1)
fig.add_trace(go.Scatter(x=df.index, y=price_aligned, mode='lines', name='Electricity Price', line=dict(color='purple')), row=5, col=1)

fig.update_xaxes(title_text="Date", row=5, col=1)
fig.update_yaxes(title_text="Cost [EUR/h] / Price [EUR/MWh]", row=5, col=1)

fig.update_layout(title_text=f"Heat Pump (Heating) annual analysis per hour, Date Range: {start}-{end}", title_x=0.5)

# Save figure to html
fig.write_html(output_filename+".html", auto_open=True)
print(f"Data and plots saved")








#%% Cooling HTML plotting
# Create subplots for cooling analysis
fig_cooling = make_subplots(rows=5, cols=1, subplot_titles=(
    f"Ambient Temperature NL: (De Bilt) Avg: {df['T_260'].mean():.1f}°C, Min: {df['T_260'].min():.1f}°C, Max: {df['T_260'].max():.1f}°C",
    f"Cooling demand: {Q_cool_sum:,.0f} kWh-th, Max power: {Q_cool[Q_cool != 0].max():.1f} kW-th, COPmin: {COP_cool[COP_cool != 0].min():.1f}, COPavg: {COP_cool_avg:.1f} volume weighted, COPmax: {COP_cool[COP_cool != 0].max():.1f}",
    f"Cooling avg: {Q_cool[Q_cool != 0].mean():.1f} kW-th, Airco avg: {E_WP_cooling_input[E_WP_cooling_input != 0].mean():.1f} kWe, Elec input: {E_WP_cooling_input.sum():.0f} kWh/y",
    f"Airco per heat: {avg_CO2_per_Q_coolpump:,.0f} gCO2/kWh-th , Airco avg per electricity: {avg_CO2_per_kWh_coolpump:.0f} gCO2/kWh, NL 2024 avg: {avg_CO2_source:.0f} gCO2/kWh, Total: {total_CO2_emissions_kg_cooling:_.0f} kg/y".replace('_', '.'),
    f"Electricity: Airco avg:{avg_cooling_cost_per_MWh:.1f} EUR/MWh, Market avg: {average_price_per_MWh:.0f} EUR/MWh, ratio: {100*avg_cooling_cost_per_MWh/average_price_per_MWh:,.0f}%, Total: {total_cooling_cost:_.0f} EUR/y".replace('_', '.')
    )
)               

# Temperature over time plot for cooling
fig_cooling.add_trace(go.Scatter(x=df.index, y=df["T_260"], mode='lines', name=f"KNMI Temperature at Station: {stations1['name'][260]}"), row=1, col=1)
fig_cooling.add_trace(go.Scatter(x=df.index, y=dT_cool, mode='lines', name='dT_cool'), row=1, col=1)

fig_cooling.update_xaxes(title_text="Date", row=1, col=1)
fig_cooling.update_yaxes(title_text="Temperature ['C] / Power in kW", row=1, col=1)

# Cooling power and COP plot
fig_cooling.add_trace(go.Scatter(x=df.index, y=Q_cool, mode='lines', name='Q_cool'), row=2, col=1)
fig_cooling.add_trace(go.Scatter(x=df.index, y=COP_cool, mode='lines', name='COP_cool'), row=2, col=1)
fig_cooling.add_trace(go.Scatter(x=df.index, y=E_WP_cooling_input, mode='lines', name='E_WP_cooling_input'), row=2, col=1)

fig_cooling.update_xaxes(title_text="Date", row=2, col=1)
fig_cooling.update_yaxes(title_text="Power in kW / COP", row=2, col=1)

# Histogram plot for cooling
data_hist_cool1 = COP_cool 
fig_cooling.add_trace(go.Histogram(x=data_hist_cool1, name='COP_cool', autobinx=False, xbins=dict(start=min(data_hist_cool1), end=max(data_hist_cool1), size=0.25), histnorm=''), row=3, col=1)

data_hist_cool2 = Q_cool
fig_cooling.add_trace(go.Histogram(x=data_hist_cool2, name='Q_cool', autobinx=False, xbins=dict(start=min(data_hist_cool2), end=max(data_hist_cool2), size=0.25), histnorm=''), row=3, col=1)

data_hist_cool3 = E_WP_cooling_input
fig_cooling.add_trace(go.Histogram(x=data_hist_cool3, name='E_WP_cooling_input', autobinx=False, xbins=dict(start=min(data_hist_cool3), end=max(data_hist_cool3), size=0.25), histnorm=''), row=3, col=1)

fig_cooling.update_xaxes(title_text="kW", row=3, col=1)
fig_cooling.update_yaxes(title_text="Ocurrence [hours/year]", row=3, col=1)

# CO2 Emissions subplot for cooling
E_WP_cooling_input_CO2 = E_WP_cooling_input * co2_emissions  # gCO2 per hour
fig_cooling.add_trace(go.Scatter(x=df.index, y=co2_emissions, mode='lines', name='CO2 Source Emissions', line=dict(color='red')), row=4, col=1)
fig_cooling.add_trace(go.Scatter(x=df.index, y=E_WP_cooling_input_CO2, mode='lines', name='Cooling Airco CO2 Emissions', line=dict(color='blue')), row=4, col=1)

fig_cooling.update_xaxes(title_text="Date", row=4, col=1)
fig_cooling.update_yaxes(title_text="CO2 Emissions [gCO2/kWh]", row=4, col=1)

# Cost subplot for cooling
fig_cooling.add_trace(go.Scatter(x=df.index, y=cost_cooling_per_hour, mode='lines', name='Cooling Cost per Hour', line=dict(color='green')), row=5, col=1)
fig_cooling.add_trace(go.Scatter(x=df.index, y=price_aligned, mode='lines', name='Electricity Price', line=dict(color='purple')), row=5, col=1)

fig_cooling.update_xaxes(title_text="Date", row=5, col=1)
fig_cooling.update_yaxes(title_text="Cost [EUR/h] / Price [EUR/MWh]", row=5, col=1)

fig_cooling.update_layout(title_text=f"Cooling Airco annual analysis per hour, Date Range: {start}-{end}", title_x=0.5)

# Save cooling figure to html
cooling_output_filename = f"Q_cooling_De_Bilt_{start}_{end}"
fig_cooling.write_html(cooling_output_filename+".html", auto_open=True)
print(f"Cooling data and plots saved to {cooling_output_filename}.html")









