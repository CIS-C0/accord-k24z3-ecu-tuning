# HDS logs: fuel pump or MAF? (plan of 2026-10-31)

Goal: see whether the fuel shortfall (+11-16 %) changes with the fuel LEVEL and with the pump TEMPERATURE.
- If it changes: it is the fuel supply (pump, strainer, regulator).
- If it stays fixed: it is the MAF or the intake (or the injectors, or the regulator).

## Signals to tick in HDS SnapShot
Simplest: tick EVERYTHING, as in the earlier logs. It works and the decoder reads it.
If you must choose, this is the minimum, with the names shown in HDS:

| HDS name | Why |
|---|---|
| Engine Speed | rpm |
| Vehicle Speed | speed |
| MAP Sensor | load |
| MAF Sensor | air flow |
| ECT Sensor 1 | engine warm |
| IAT Sensor (1) | air temperature |
| Baro Sensor | reference |
| AF FB (ST Fuel Trim) | short-term correction |
| AF FB AVE (LT Fuel Trim) | long-term correction |
| AF Lambda | measured lambda |
| AF Lambda Cmd | commanded lambda |
| FSS | closed / open loop |
| HO2S S2 | rear O2 sensor |
| Fuel Cut | fuel cut |
| Idling | idle |
| Fuel Level | fuel level (instant) |
| Fuel Level(Average) | fuel level (average) |
| F Injector | injection time |
| Battery | voltage (the pump depends on it) |
| APP Sensor | pedal |
| Gear Position | gear |
| Spark Advance | ignition advance |
| Knock Retard | knock |
| Eng Run Time | run time |

## Before leaving
- Tank between 1/3 and 1/2. Not lower: the seller's notes say "fuel pump small problem, keep the tank full".
- Photo of the fuel gauge needle. It is used to find the scale of "Fuel Level".
- No flash, no DTC clearing and no ECU reset until then.
- A/C OFF during the measurements (the load must be the same for every series).

## The SERIES (always the same, warm engine ECT >= 80 °C)
Each point: 30 s STEADY (pedal held), snapshot running.
1. Idle in neutral, stopped: 60 s
2. 50 km/h in 4th
3. 80 km/h in 5th
4. 100 km/h in 5th
5. Gentle acceleration in 3rd, from 2,000 to 4,000 rpm, about half pedal (MAP 60-80). NO full load.

## The 4 phases
| Phase | When | What |
|---|---|---|
| P1 | after 10-15 min of driving (engine warm), tank 1/3 to 1/2 | the SERIES |
| P2 | after another 25-30 min of driving (pump warm) | the SERIES |
| P3 | FILL UP (note the litres and the time), drive off at once | the SERIES within 5 min |
| P4 | 15 min after the fill | the SERIES |

Note the start time of each phase (the snapshot names contain the time). Photo of the needle at P1 and at P3.

## Reading the results
Compare the total correction (short term x long term) at the SAME point of the series. Between two drives it varies by
~2 % for no reason.

| Result | Conclusion | Next |
|---|---|---|
| P3/P4 lower than P2 by at least 4 % | the level matters: fuel supply | pressure gauge, then pump or strainer |
| P2 higher than P1 by at least 4 % | the heat matters: pump weak when hot | pressure gauge with the pump hot |
| all the same (± 3 %), ~+13 % everywhere | fixed error: MAF / intake / injectors / regulator | stock intake or MAF cleaning, then pressure gauge |

## Safety
- No full load. The ECU stays in closed loop up to MAP ~95 and corrects.
- If "AF FB (ST Fuel Trim)" stays stuck at the top (above ~1.30) or the engine hesitates: lift off.
- Do not go below 1/3 of a tank.

Note (later finding, 2026-11-07): the long-term trim shown by HDS is not used by the injection on this ROM; the short-term
trim is the real correction. See KNOWLEDGE.md "ROM ANSWER 2026-11-07".
