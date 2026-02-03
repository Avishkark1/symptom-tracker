import csv
import json
from dataclasses import dataclass
from typing import Dict, List

# Simple, safe, toy model for TB spread with latent infection.
# Compartments:
#   S: Susceptible
#   L: Latent (infected, not infectious)
#   A: Active TB (infectious)
#   R: Recovered (non-infectious)
#
# This is a didactic simulation only. It does NOT represent real-world TB dynamics.


@dataclass
class Params:
    population: int = 10000
    initial_active: int = 12
    initial_latent: int = 80
    beta: float = 0.25           # transmission rate per active per day (toy value)
    latent_rate: float = 0.85    # fraction of new infections entering latent state
    prog_rate: float = 0.0006    # daily progression L -> A (toy value)
    recovery_rate: float = 0.03  # daily A -> R (toy value)
    loss_immunity: float = 0.0   # daily R -> S (toy value)
    days: int = 365


def step(state: Dict[str, float], p: Params) -> Dict[str, float]:
    s = state["S"]
    l = state["L"]
    a = state["A"]
    r = state["R"]

    # Force of infection (toy)
    lam = p.beta * (a / p.population)

    # New infections
    new_inf = min(s, lam * s)
    new_latent = p.latent_rate * new_inf
    new_active = (1 - p.latent_rate) * new_inf

    # Progression and recovery
    prog = min(l, p.prog_rate * l)
    recov = min(a, p.recovery_rate * a)
    loss = min(r, p.loss_immunity * r)

    s_next = s - new_inf + loss
    l_next = l + new_latent - prog
    a_next = a + new_active + prog - recov
    r_next = r + recov - loss

    return {"S": s_next, "L": l_next, "A": a_next, "R": r_next}


def simulate(p: Params) -> List[Dict[str, float]]:
    s0 = p.population - p.initial_active - p.initial_latent
    state = {"S": float(s0), "L": float(p.initial_latent), "A": float(p.initial_active), "R": 0.0}

    history = []
    for day in range(p.days + 1):
        history.append({"day": day, **state})
        state = step(state, p)
    return history


def save_csv(history: List[Dict[str, float]], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["day", "S", "L", "A", "R"])
        writer.writeheader()
        for row in history:
            writer.writerow(row)


def summarize(history: List[Dict[str, float]]) -> str:
    peak = max(history, key=lambda r: r["A"])
    end = history[-1]
    lines = []
    lines.append("Summary (toy model)")
    lines.append(f"- Peak active TB: {peak['A']:.1f} on day {peak['day']}")
    lines.append(f"- End of sim: S={end['S']:.1f}, L={end['L']:.1f}, A={end['A']:.1f}, R={end['R']:.1f}")
    return "\n".join(lines)


def main():
    p = Params()
    history = simulate(p)
    save_csv(history, "tb_simulation.csv")

    with open("tb_simulation_params.json", "w", encoding="utf-8") as handle:
        json.dump(p.__dict__, handle, indent=2)

    print(summarize(history))
    print("\nWrote tb_simulation.csv and tb_simulation_params.json")


if __name__ == "__main__":
    main()
