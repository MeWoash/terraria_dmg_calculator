from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    form_data = request.form if request.method == 'POST' else {}

    if request.method == 'POST':
        try:
            def get_bonus(name, scale=1):
                if f'enable_{name}' in request.form:
                    return float(request.form.get(name, 0)) * scale
                return 0

            # Base stats
            base_dmg = float(request.form.get('base_dmg', 0))
            base_crit = float(request.form.get('base_crit', 0))
            use_time = float(request.form.get('use_time', 1))
            projectiles = float(request.form.get('projectiles', 1))

            # Prefix bonuses
            bonus_dmg_prefix = get_bonus('bonus_dmg_prefix', 0.01)
            bonus_crit_prefix = get_bonus('bonus_crit_prefix')
            bonus_speed_prefix = get_bonus('bonus_speed_prefix', 0.01)

            # Set bonuses
            bonus_dmg_set = get_bonus('bonus_dmg_set', 0.01)
            bonus_crit_set = get_bonus('bonus_crit_set')
            bonus_crit_dmg_set = get_bonus('bonus_crit_dmg_set', 0.01)

            # Equipment bonuses
            bonus_dmg_eq = get_bonus('bonus_dmg_eq', 0.01)
            bonus_crit_eq = get_bonus('bonus_crit_eq')
            bonus_crit_dmg_eq = get_bonus('bonus_crit_dmg_eq', 0.01)

            # Reforge bonuses
            bonus_dmg_reforge = get_bonus('bonus_dmg_reforge', 0.01)
            bonus_crit_reforge = get_bonus('bonus_crit_reforge')

            # Sums
            total_bonus_dmg = bonus_dmg_prefix + bonus_dmg_set + bonus_dmg_eq + bonus_dmg_reforge
            total_crit_chance = base_crit + bonus_crit_prefix + bonus_crit_set + bonus_crit_eq + bonus_crit_reforge
            total_crit_dmg = bonus_crit_dmg_set + bonus_crit_dmg_eq
            crit_multiplier = 2 + total_crit_dmg

            # Calculations
            total_damage = base_dmg * (1 + total_bonus_dmg)
            avg_damage = total_damage * (1 + (total_crit_chance / 100) * (crit_multiplier - 1))
            real_use_time = use_time * (1 - bonus_speed_prefix)
            attacks_per_sec = 60 / real_use_time if real_use_time > 0 else 0
            dps = avg_damage * attacks_per_sec * projectiles

            result = {
                'total_damage': round(total_damage, 2),
                'total_crit_chance': round(total_crit_chance, 2),
                'avg_damage': round(avg_damage, 2),
                'dps': round(dps, 2)
            }

        except (ValueError, ZeroDivisionError) as e:
            result = {'error': f'Calculation error: {e}'}

    return render_template('index.html', result=result, form_data=form_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
