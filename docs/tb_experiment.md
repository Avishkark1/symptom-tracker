# TB Toy Simulation (Safe, Non-Lab)

This is a **purely computational**, **toy** simulation related to *Mycobacterium tuberculosis*. It models a simple population with four compartments:

- `S`: Susceptible
- `L`: Latent infection (infected, not infectious)
- `A`: Active TB (infectious)
- `R`: Recovered (non-infectious)

It is **not** a scientific or clinical model—just an educational experiment to explore dynamics.

## Run

```powershell
python .\experiments\tb_spread_sim.py
```

## Output

- `tb_simulation.csv` — time series for `S/L/A/R`
- `tb_simulation_params.json` — parameters used

## Notes

- Parameters are intentionally simple and not calibrated.
- You can tweak parameters in `experiments\tb_spread_sim.py` to see how outcomes change.
