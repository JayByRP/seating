import zipfile

from flask import Flask, render_template, request, jsonify, session, send_file
from main import SeatingGenerator, visualize_seating, find_optimal_configuration, generate_test_data, \
    explore_arrangements
import json
import os
import io

from flask_session import Session

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './flask_session'
Session(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    try:
        guests = [g.strip() for g in data['guests']]
        constraints = [(c['a'], c['b'], c['type']) for c in data['constraints']]
        config = data['config']

        if config['mode'] == 'auto':
            result, tsize, ntables, _ = find_optimal_configuration(
                len(guests),
                guests,
                constraints,
                config['min_size'],
                config['max_size']
            )
            if not result['tables']:
                return jsonify({'error': result['message']}), 400

            arrangements = explore_arrangements(
                guests, constraints, tsize, ntables, max_attempts=100
            )
        else:
            tsize = config['fixed_size']
            ntables = (len(guests) + tsize - 1) // tsize
            arrangements = explore_arrangements(
                guests, constraints, tsize, ntables, max_attempts=100
            )

        if not arrangements:
            return jsonify({'error': 'No valid arrangements found'}), 400

        session['arrangements'] = [arr[1] for arr in arrangements]
        session['current_idx'] = 0
        session['guests'] = guests
        session['constraints'] = constraints

        # Send the first arrangement to frontend
        return jsonify({
            'tables': session['arrangements'][0],
            'current': 0,
            'total': len(session['arrangements'])
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/test-data')
def test_data():
    num_people = request.args.get('n', default=20, type=int)
    people, constraints = generate_test_data(num_people)
    return jsonify({
        'guests': people,
        'constraints': [{
            'a': a,
            'b': b,
            'type': typ
        } for a, b, typ in constraints]
    })


@app.route('/export')
def export_data():
    data = {
        'guests': session.get('guests', []),
        'constraints': [{
            'a': c[0],
            'b': c[1],
            'type': c[2]
        } for c in session.get('constraints', [])]
    }
    return send_file(
        io.BytesIO(json.dumps(data, indent=2).encode()),
        mimetype='application/json',
        as_attachment=True,
        download_name='seating_data.json'
    )


@app.route('/import', methods=['POST'])
def import_data():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    try:
        data = json.load(file)
        session['guests'] = data.get('guests', [])
        session['constraints'] = [(c['a'], c['b'], c['type'])
                                  for c in data.get('constraints', [])]
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/next')
def next_arrangement():
    current = session.get('current_idx', 0)
    arrangements = session.get('arrangements', [])
    total = len(arrangements)

    if total == 0:
        return jsonify({'error': 'No arrangements available'}), 400

    new_idx = (current + 1) % total
    session['current_idx'] = new_idx

    return jsonify({
        'tables': arrangements[new_idx],
        'current': new_idx,
        'total': total
    })


@app.route('/previous')
def previous_arrangement():
    current = session.get('current_idx', 0)
    arrangements = session.get('arrangements', [])
    total = len(arrangements)

    if total == 0:
        return jsonify({'error': 'No arrangements available'}), 400

    new_idx = (current - 1) % total
    session['current_idx'] = new_idx

    return jsonify({
        'tables': arrangements[new_idx],
        'current': new_idx,
        'total': total
    })


@app.route('/download-image')
def download_image():
    try:
        tables = session['arrangements'][session['current_idx']]
        fig = visualize_seating(tables)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        return send_file(buf, mimetype='image/png',
                         as_attachment=True,
                         download_name='seating_chart.png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download-text')
def download_text():
    try:
        tables = session['arrangements'][session['current_idx']]
        output = io.StringIO()
        output.write("Wedding Seating Arrangement\n\n")
        for i, table in enumerate(tables, 1):
            output.write(f"Table {i} ({len(table)} guests)\n")
            for name in table:
                output.write(f"* {name}\n")
            output.write("\n")
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/plain',
            as_attachment=True,
            download_name='seating_arrangement.txt'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download-both')
def download_combined():
    try:
        tables = session['arrangements'][session['current_idx']]

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            text_output = io.StringIO()
            text_output.write("Wedding Seating Arrangement\n\n")
            for i, table in enumerate(tables, 1):
                text_output.write(f"Table {i} ({len(table)} guests)\n")
                text_output.write("\n".join(f"• {name}" for name in sorted(table)) + "\n\n")
            text_output.seek(0)
            zip_file.writestr("seating_arrangement.txt", text_output.getvalue())

            fig = visualize_seating(tables)
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', bbox_inches='tight')
            img_buffer.seek(0)
            zip_file.writestr("seating_chart.png", img_buffer.getvalue())

        zip_buffer.seek(0)
        response = send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='Seating Arrangement.zip'
        )
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/save-data', methods=['POST'])
def save_data():
    session['guests'] = request.json.get('guests', [])
    session['constraints'] = request.json.get('constraints', [])
    return jsonify({'success': True})


@app.route('/load-data')
def load_data():
    return jsonify({
        'guests': session.get('guests', []),
        'constraints': session.get('constraints', [])
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
