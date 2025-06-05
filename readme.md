🏡 Heat Pump Load & COP Analysis (NL)

This repository provides a Python-based tool to estimate the electricity demand and performance of heat pumps for residential buildings in the Netherlands, using KNMI temperature data.

🔍 Purpose

To simulate the hourly heat load, electric load, and coefficient of performance (COP) of heat pumps in homes switching from gas heating. The tool:
	•	Retrieves hourly temperature data from KNMI for a selectable Dutch weather station.
	•	Computes hourly heat demand based on the difference between indoor and outdoor temperature.
	•	Estimates the COP of the heat pump using a linear approximation based on temperature delta.
	•	Calculates the hourly electricity consumption of the heat pump.
	•	Aggregates to yearly values:
	•	Total electricity demand in kWh/year
	•	Weighted average COP

⚙️ Features

Feature	Description
KNMI integration	Uses hourly outdoor temperature data from KNMI
Custom station support	User can select any KNMI station by code
Building model	Constant indoor temperature (typically 20°C) and fixed heat loss coefficient
Hourly COP estimation	Based on linear relation: COP = a - b * ΔT
Annual aggregation	Yearly kWh and weighted COP values computed
Ready for future expansion	Integration with day-ahead electricity prices & CO₂ intensities (via NED.nl) is planned

📈 Example Output

The script produces:
	•	A CSV or DataFrame with:
	•	Hour
	•	Ambient temperature
	•	Heat demand (W)
	•	Estimated COP
	•	Electricity demand (W)
	•	Annual totals:
	•	Total electric energy used (kWh/year)
	•	Weighted annual COP

🔜 Next Steps

The next version will integrate:
	•	⚡ Day-ahead electricity prices
	•	🌍 Hourly CO₂ intensity of electricity production

Using data from the Nationaal Energie Dashboard (NED.nl).

🛠 Requirements
	•	Python 3.8+
	•	pandas
	•	numpy
	•	Internet access for KNMI data download

📂 Usage

python KNMY_retrieval_v7_Q_heatpump.py

You can customize parameters such as:
	•	station: KNMI station code (e.g., 260 for De Bilt)
	•	year: Year to analyze
	•	indoor_temp: Setpoint temperature in the house
	•	Q_loss_factor: W/K heat loss coefficient of the building

📝 License

MIT License

👤 Author:  Mayk Thewessen – Treehouse Energy