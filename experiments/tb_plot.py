import csv
from pathlib import Path

# Simple plotter for tb_simulation.csv
# Uses matplotlib if available; otherwise prints a short summary.


def load_rows(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def summarize(rows):
    if not rows:
        print("No rows found.")
        return
    peak = max(rows, key=lambda r: float(r["A"]))
    end = rows[-1]
    print("Summary from CSV")
    print(f"- Peak active TB: {float(peak['A']):.1f} on day {int(float(peak['day']))}")
    print(
        f"- End of sim: S={float(end['S']):.1f}, "
        f"L={float(end['L']):.1f}, A={float(end['A']):.1f}, R={float(end['R']):.1f}"
    )


def plot(rows):
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("matplotlib not installed; printing summary instead.")
        summarize(rows)
        return

    days = [int(float(r["day"])) for r in rows]
    s = [float(r["S"]) for r in rows]
    l = [float(r["L"]) for r in rows]
    a = [float(r["A"]) for r in rows]
    r = [float(r["R"]) for r in rows]

    plt.figure(figsize=(9, 5))
    plt.plot(days, s, label="Susceptible (S)")
    plt.plot(days, l, label="Latent (L)")
    plt.plot(days, a, label="Active (A)")
    plt.plot(days, r, label="Recovered (R)")
    plt.title("TB Toy Simulation")
    plt.xlabel("Day")
    plt.ylabel("People")
    plt.legend()
    plt.tight_layout()
    plt.show()


def main():
    path = Path("tb_simulation.csv")
    if not path.exists():
        print("tb_simulation.csv not found. Run tb_spread_sim.py first.")
        return
    rows = load_rows(path)
    plot(rows)


if __name__ == "__main__":
    main()
