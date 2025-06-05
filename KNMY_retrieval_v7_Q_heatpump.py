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
Q_heat = dT_heat * (10/18)  # hourly values, at 0'C heat load = 10kW thus dt 20'K = 10kW, thus 20*X=10.000, thus X=500W/'K - Convert temperature difference to heat demand in kWh (assuming 1 degree Celsius = 1000 kWh for simplicity)
COP_heat = 5.5 - dT_heat*(2.5/18)  # COP at 20'C Ambient is 5.5, and at 0'C it is 3.5, thus 20'K lowers it with 2.0 thus 0.1 per 1'K in dT -  Coefficient of Performance (COP) of the heat pump, assuming a linear decrease with increasing temperature difference
E_WP_heating_input = Q_heat / COP_heat  # kW electricity per hour (thus is also kWh) convert heat demand to electrical input energy in kWh


T_cool_setpoint = 23  # Setpoint temperature in Celsius of building
dT_cool = T_cool_setpoint - df['T_260']
dT_cool[dT_cool > 2] = 0  # Only enable cooling when Tamb > 25'C , as no cooling demand when T_260 is above setpoint
Q_cool = -dT_cool * (4/10) # kW-th 
COP_cool = 5.0 + dT_cool*(2.0/23)
E_WP_cooling_input = Q_cool / COP_cool  # kW electricity per hour (thus is also kWh) convert cooling demand to electrical input energy in kWh

Q_heat_sum = Q_heat.sum()
Q_heat_avg = Q_heat.mean()
COP_heat_avg = COP_heat.mean()
E_WP_heating_input_sum = E_WP_heating_input.sum()


print(f"Total heat demand: {Q_heat_sum:_.0f} kWh-thermal average over the year".replace('_', '.'))
print(f"Gas eq. demand: {Q_heat_sum/10:.0f} m3/year")
print(f"Average heat demand: {Q_heat_avg:.1f} kW-thermal")
print(f"Average COP of heat pump: {COP_heat_avg:.2f}")
print(f"Total electricity input for heating: {E_WP_heating_input_sum:.0f} kWh/year")

#%% Electricity cost by Entsoe data




#%% Electricity emissions on hourly basis by NED.nl data
# Define the API endpoint for hourly emissions data
url = "https://api.ned.nl/v1/energy/co2-emissions"

# Define the parameters for the API request
params = {
    "year": 2024,
    "format": "json"  # Specify the format as JSON
}

try:
    # Make the API request
    response = requests.get(url, params=params)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Process the data (example: print the first few entries)
        print("First 5 CO2 emission entries:")
        for i in range(min(5, len(data))):
            print(data[i])

        # Convert the JSON data to a Pandas DataFrame
        emissions_df = pd.DataFrame(data)

        # Convert 'datetime' column to datetime objects
        emissions_df['datetime'] = pd.to_datetime(emissions_df['datetime'])

        # Set 'datetime' column as index
        emissions_df = emissions_df.set_index('datetime')

        # Rename the 'co2_emissions' column to 'CO2_emissions'
        emissions_df.rename(columns={'co2_emissions': 'CO2_emissions'}, inplace=True)

        # Print the info of the DataFrame
        print("\nDataFrame Info:")
        print(emissions_df.info())

        # Display the first few rows of the DataFrame
        print("\nDataFrame Head:")
        print(emissions_df.head())

        # Optionally, save the data to a CSV file
        emissions_df.to_csv("co2_emissions_2024.csv")
        print("CO2 emissions data saved to co2_emissions_2024.csv")

        # Merge the DataFrames based on the datetime index
        df = pd.merge(df, emissions_df, left_index=True, right_index=True, how='left')

        # Print the info of the DataFrame
        print("\nDataFrame Info:")
        print(df.info())

        # Display the first few rows of the DataFrame
        print("\nDataFrame Head:")
        print(df.head())

    else:
        # Print an error message if the request was not successful
        print(f"Error: API request failed with status code {response.status_code}")
        print(response.text)  # Print the response content for debugging

except requests.exceptions.RequestException as e:
    # Handle any exceptions that may occur during the API request
    print(f"Error: An error occurred during the API request: {e}")
except json.JSONDecodeError as e:
    # Handle JSON decoding errors
    print(f"Error: Could not decode JSON response: {e}")
except Exception as e:
    # Handle other exceptions
    print(f"An unexpected error occurred: {e}")



#%% Plotly HTML plotting
# Create subplots
fig = make_subplots(rows=3, cols=1, subplot_titles=(
    f"Ambient Temperature NL: (De Bilt) Avg: {df['T_260'].mean():.1f}°C, Min: {df['T_260'].min():.1f}°C, Max: {df['T_260'].max():.1f}°C",
    f"Heat: {Q_heat_sum/10.5:.0f} m3 gas eq. Q_heat_max ={Q_heat.max():.1f} kWth, COP_min: {COP_heat.min():.1f}, COP_max: {COP_heat.max():.1f}",
    f"Heat avg: {Q_heat_avg:.1f} kWth, Heatpump avg: {E_WP_heating_input.mean():.1f} kWe, COP avg: {COP_heat_avg:.1f}, Elec input: {E_WP_heating_input_sum:.0f} kWh/y"
))

# Temperature over time plot
fig.add_trace(go.Scatter(x=df.index, y=df["T_260"], mode='lines', name=f"KNMI Temperature at Station: {stations1['name'][260]}"), row=1, col=1)
#fig.add_trace(go.Scatter(x=df.index, y=df["T_380"], mode='lines', name=f"KNMI Temperature at Station: {stations2['name'][380]}"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=dT_heat, mode='lines', name='dT_heat'), row=1, col=1)

fig.update_xaxes(title_text="Date", row=1, col=1)
fig.update_yaxes(title_text="Temperature ['C] / Power in kW", row=1, col=1)


fig.add_trace(go.Scatter(x=df.index, y=Q_heat, mode='lines', name='Q_heat'), row=2, col=1)
fig.add_trace(go.Scatter(x=df.index, y=COP_heat, mode='lines', name='COP_heat'), row=2, col=1)
fig.add_trace(go.Scatter(x=df.index, y=E_WP_heating_input, mode='lines', name='E_WP_heating_input'), row=2, col=1)

fig.update_xaxes(title_text="Date", row=2, col=1)
fig.update_yaxes(title_text="Power in kW / COP", row=2, col=1)


# Histogram plot
data_hist1 = COP_heat 
fig.add_trace(go.Histogram(x=data_hist1, name='COP_heat', autobinx=False, xbins=dict(start=min(data_hist1), end=max(data_hist1), size=0.25), histnorm=''), row=3, col=1)

data_hist2 = Q_heat
fig.add_trace(go.Histogram(x=data_hist2, name='Q_heat', autobinx=False, xbins=dict(start=min(data_hist2), end=max(data_hist2), size=0.25), histnorm=''), row=3, col=1)

data_hist3 = E_WP_heating_input
fig.add_trace(go.Histogram(x=data_hist3, name='E_WP_heating_input', autobinx=False, xbins=dict(start=min(data_hist3), end=max(data_hist3), size=0.25), histnorm=''), row=3, col=1)


fig.update_xaxes(title_text="kW", row=3, col=1)
fig.update_yaxes(title_text="Ocurrence [hours/year]", row=3, col=1) # , tickformat=".0%"

fig.update_layout(title_text=f"Heat Pump annual analysis per hour, Date Range: {start}-{end}", title_x=0.5)






# Save figure to html
fig.write_html(output_filename+".html", auto_open=True)
print(f"Data and plots saved")


