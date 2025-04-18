from flask import Flask, render_template, request
from matplotlib import pyplot as plt
import numpy as np
from io import BytesIO
import base64
from copy import deepcopy

app = Flask(__name__)

def get_bonus(form, name, scale=1):
    if f'enable_{name}' in form:
        return float(form.get(name, 0)) * scale
    return 0

def calculate_dps_from_form(form):
    base_dmg = float(form.get('base_dmg', 0))
    base_crit = float(form.get('base_crit', 0))
    use_time = float(form.get('use_time', 1))
    projectiles = float(form.get('projectiles', 1))
    mob_defense = float(form.get('mob_defense', 0))

    # weapon prefix
    bonus_dmg_prefix = get_bonus(form, 'bonus_dmg_prefix', 0.01)
    bonus_crit_prefix = get_bonus(form, 'bonus_crit_prefix')
    bonus_speed_prefix = get_bonus(form, 'bonus_speed_prefix', 0.01)

    # Armor, eq
    bonus_dmg_set = get_bonus(form, 'bonus_dmg_set', 0.01)
    bonus_dmg_eq = get_bonus(form, 'bonus_dmg_eq', 0.01)
    bonus_dmg_reforge = get_bonus(form, 'bonus_dmg_reforge', 0.01)

    bonus_crit_set = get_bonus(form, 'bonus_crit_set')
    bonus_crit_eq = get_bonus(form, 'bonus_crit_eq')
    bonus_crit_reforge = get_bonus(form, 'bonus_crit_reforge')

    bonus_crit_dmg_set = get_bonus(form, 'bonus_crit_dmg_set', 0.01)
    bonus_crit_dmg_eq = get_bonus(form, 'bonus_crit_dmg_eq', 0.01)

    prefixed_base_dmg = base_dmg * (1 + bonus_dmg_prefix)

    total_bonus_dmg = bonus_dmg_set + bonus_dmg_eq + bonus_dmg_reforge
    total_crit_chance = base_crit + bonus_crit_prefix + bonus_crit_set + bonus_crit_eq + bonus_crit_reforge
    crit_multiplier = 2 + bonus_crit_dmg_set + bonus_crit_dmg_eq

    total_damage = prefixed_base_dmg * (1 + total_bonus_dmg)

    # mob defense correction
    effective_damage = max(total_damage - (mob_defense / 2), 1)

    # final damage calculation
    avg_hit = effective_damage * (1 + (total_crit_chance / 100) * (crit_multiplier - 1))
    real_use_time = use_time * (1 - bonus_speed_prefix)
    attacks_per_sec = 60 / real_use_time if real_use_time > 0 else 0
    dps = avg_hit * attacks_per_sec * projectiles

    return {
        'total_damage': total_damage,
        'effective_damage': effective_damage,
        'avg_hit': avg_hit,
        'crit_chance': total_crit_chance,
        'dps': dps
    }


@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    form_data = request.form if request.method == 'POST' else {}

    if request.method == 'POST':
        try:
            stats = calculate_dps_from_form(form_data)
            result = {
                'total_damage': round(stats['total_damage'], 2),
                'avg_damage': round(stats['avg_hit'], 2),
                'total_crit_chance': round(stats['crit_chance'], 2),
                'dps': round(stats['dps'], 2)
            }
        except (ValueError, ZeroDivisionError) as e:
            result = {'error': f'Calculation error: {e}'}

    return render_template('index.html', result=result, form_data=form_data)

@app.route('/heatmap', methods=['POST'])
def heatmap():
    form = request.form
    accessory_slots = int(form.get('accessory_slots', 6))
    per_item_dmg = float(form.get('per_item_dmg', 4)) / 100
    per_item_crit = float(form.get('per_item_crit', 4))
    def_min = int(form.get('def_min', 0))
    def_max = int(form.get('def_max', 100))
    def_samples = int(form.get('def_samples', 5))
    def_values = np.linspace(def_min, def_max, def_samples, dtype=int)

    all_dps = {mob_def: [] for mob_def in def_values}
    labels = []

    for dmg_count in range(accessory_slots + 1):
        crit_count = accessory_slots - dmg_count
        label = f"{dmg_count}xDMG\n{crit_count}xCRIT"
        labels.append(label)

        for mob_def in def_values:
            modified_form = dict(form)
            modified_form.update({
                'bonus_dmg_reforge': str(dmg_count * per_item_dmg * 100),
                'bonus_crit_reforge': str(crit_count * per_item_crit),
                'enable_bonus_dmg_reforge': 'on',
                'enable_bonus_crit_reforge': 'on',
                'mob_defense': str(mob_def)
            })
            stats = calculate_dps_from_form(modified_form)
            all_dps[mob_def].append(stats["dps"])

    avg_dps = np.mean(list(all_dps.values()), axis=0)
    avg_img = draw_bar_chart(avg_dps, labels, "Average DPS across defenses")

    individual_imgs = []
    max_charts = 6
    step = max(1, len(def_values) // max_charts)
    for mob_def in def_values[::step]:
        chart = draw_bar_chart(all_dps[mob_def], labels, f"Defense: {mob_def}")
        individual_imgs.append((mob_def, chart))

    return render_template("realistic_reforge.html", avg_image=avg_img, charts=individual_imgs)


def draw_bar_chart(dps_values, labels, title, accessory_slots=None):
    fig, ax = plt.subplots(figsize=(12, 7))

    best_index = int(np.argmax(dps_values))
    worst_index = int(np.argmin(dps_values))
    colors = [
        'green' if i == best_index else
        'red' if i == worst_index else
        'gray'
        for i in range(len(dps_values))
    ]

    bars = ax.bar(labels, dps_values, color=colors)

    for bar, val in zip(bars, dps_values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(dps_values) * 0.01,
                f'{int(val)}', ha='center', va='bottom',
                fontsize=11, color='white', weight='bold')

    best_label = labels[best_index].replace("\n", " / ")
    best_value = int(dps_values[best_index])
    
    ax.text(0.5, -0.25, f"Best setup: {best_label} → {best_value} DPS",
            transform=ax.transAxes, fontsize=13, ha='center', color='lightgreen')

    ax.set_ylabel("DPS")
    ax.set_title(title)

    y_min = min(dps_values) * 0.95
    y_max = max(dps_values) * 1.1
    ax.set_ylim(y_min, y_max)

    if accessory_slots is not None:
        base_dps = dps_values[accessory_slots // 2] 
        ax.axhline(base_dps, color='orange', linestyle='--', linewidth=1)
        ax.text(len(dps_values) - 1, base_dps + (y_max - y_min) * 0.01,
                f'AVG DPS: {int(base_dps)}', ha='right', color='orange', fontsize=10)

    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()
    return img_base64



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
