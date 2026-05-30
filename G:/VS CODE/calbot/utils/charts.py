import io
from datetime import date
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


DAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def make_week_chart(week_data: list[dict], daily_limit: int) -> bytes:
    labels = []
    calories = []
    today = date.today()

    for entry in week_data:
        d = entry["date"]
        day_name = DAYS_RU[d.weekday()]
        label = f"{day_name}\n{d.day:02d}.{d.month:02d}"
        if d == today:
            label = f"▶ {day_name}\n{d.day:02d}.{d.month:02d}"
        labels.append(label)
        calories.append(entry["calories"])

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    bar_colors = []
    for c in calories:
        if c == 0:
            bar_colors.append("#3a3a5c")
        elif c <= daily_limit:
            bar_colors.append("#4cc9f0")
        else:
            bar_colors.append("#f72585")

    bars = ax.bar(labels, calories, color=bar_colors, width=0.6, zorder=3)

    ax.axhline(y=daily_limit, color="#ffd60a", linewidth=1.5, linestyle="--", zorder=4, alpha=0.85)

    for bar, cal in zip(bars, calories):
        if cal > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 15,
                f"{int(cal)}",
                ha="center", va="bottom",
                color="white", fontsize=9, fontweight="bold"
            )

    ax.set_ylim(0, max(max(calories, default=0), daily_limit) * 1.2 + 100)
    ax.set_title("Калории за 7 дней", color="white", fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("ккал", color="#aaaacc", fontsize=10)
    ax.tick_params(colors="white", labelsize=9)
    ax.spines[:].set_visible(False)
    ax.yaxis.grid(True, color="#2a2a4a", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    limit_patch = mpatches.Patch(color="#ffd60a", label=f"Лимит {daily_limit} ккал")
    ok_patch = mpatches.Patch(color="#4cc9f0", label="В норме")
    over_patch = mpatches.Patch(color="#f72585", label="Превышение")
    ax.legend(handles=[limit_patch, ok_patch, over_patch],
              facecolor="#1a1a2e", edgecolor="#3a3a5c",
              labelcolor="white", fontsize=8, loc="upper left")

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()
