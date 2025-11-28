from flask import Flask, request, jsonify, Response
import google.generativeai as genai
import json
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# Configure Gemini API (FREE)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'YOUR_API_KEY_HERE')
genai.configure(api_key=GEMINI_API_KEY)
 model = genai.GenerativeModel('gemini-pro')

DB_FILE = 'clinical_master.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS patients
                 (patient_id TEXT PRIMARY KEY,
                  date_added TEXT,
                  data_json TEXT)''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Clinical Data Extractor - FREE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .badge {
            background: #4CAF50;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            display: inline-block;
            margin-bottom: 20px;
        }
        textarea {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            font-family: monospace;
            resize: vertical;
            box-sizing: border-box;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            box-sizing: border-box;
        }
        button {
            padding: 15px 30px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            width: 100%;
            margin-top: 10px;
            transition: background 0.3s;
        }
        button:hover {
            background: #5568d3;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .result {
            margin-top: 20px;
            padding: 20px;
            border-radius: 8px;
            display: none;
        }
        .success {
            background: #d4edda;
            border: 2px solid #c3e6cb;
            color: #155724;
        }
        .error {
            background: #f8d7da;
            border: 2px solid #f5c6cb;
            color: #721c24;
        }
        .excel-section {
            margin-top: 40px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 2px solid #dee2e6;
        }
        .code-block {
            background: #2d2d2d;
            color: #4CAF50;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            margin: 10px 0;
            overflow-x: auto;
        }
        pre {
            margin: 0;
            white-space: pre-wrap;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
            padding: 20px;
            background: #f0f4ff;
            border-radius: 8px;
        }
        .stat-item {
            text-align: center;
        }
        .stat-number {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            font-size: 14px;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 Clinical Data Extractor</h1>
        <span class="badge">100% FREE - Powered by Google Gemini AI</span>
        
        <div class="stats" id="stats">
            <div class="stat-item">
                <div class="stat-number" id="totalPatients">0</div>
                <div class="stat-label">Total Patients</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">1,500</div>
                <div class="stat-label">Daily Limit (FREE)</div>
            </div>
        </div>
        
        <h3>📄 Upload Clinical Note:</h3>
        <input type="text" id="patient_id" placeholder="Enter Patient ID (e.g., 001, 002, PAT123)">
        
        <textarea id="note" rows="12" placeholder="Paste clinical note here...

Example:
BIODATA
Name: John Doe
Age: 45 years
Gender: Male
Address: 123 Hospital Road

PRESENTING COMPLAINTS
Patient presented with chest pain for 3 days...

VITALS
BP: 140/90 mmHg
PR: 88 b/m
..."></textarea>
        
        <button onclick="extract()" id="extractBtn">
            🔍 Extract Data with AI
        </button>
        
        <div id="result" class="result"></div>
        
        <div class="excel-section">
            <h3>📊 Connect Excel to Live Data</h3>
            <p><strong>Step 1:</strong> Open Microsoft Excel</p>
            <p><strong>Step 2:</strong> Go to <code>Data → Get Data → From Web</code></p>
            <p><strong>Step 3:</strong> Enter this URL:</p>
            <div class="code-block">
                <span id="apiUrl"></span>
            </div>
            <p><strong>Step 4:</strong> Click "Load" and your data appears!</p>
            <p><strong>Step 5:</strong> Set auto-refresh: Right-click table → Properties → Refresh every 5 minutes</p>
        </div>
    </div>
    
    <script>
        // Set API URL
        document.getElementById('apiUrl').textContent = window.location.origin + '/api/export/csv';
        
        // Load stats
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                document.getElementById('totalPatients').textContent = data.total || 0;
            } catch (e) {
                console.error('Failed to load stats');
            }
        }
        
        loadStats();
        
        async function extract() {
            const note = document.getElementById('note').value.trim();
            const patient_id = document.getElementById('patient_id').value.trim();
            const resultDiv = document.getElementById('result');
            const btn = document.getElementById('extractBtn');
            
            if (!note || !patient_id) {
                alert('⚠️ Please enter both Patient ID and Clinical Note');
                return;
            }
            
            // Show loading
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Processing with AI...';
            resultDiv.style.display = 'none';
            
            try {
                const response = await fetch('/api/extract', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: note, patient_id: patient_id})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    resultDiv.className = 'result success';
                    resultDiv.innerHTML = 
                        '<h3>✅ Extraction Successful!</h3>' +
                        '<p><strong>Patient ID:</strong> ' + data.data.patient_id + '</p>' +
                        '<p><strong>Diagnosis:</strong> ' + (Array.isArray(data.data.diagnosis) ? data.data.diagnosis.join(', ') : data.data.diagnosis) + '</p>' +
                        '<p><strong>Triage Level:</strong> ' + data.data.triage_level + '</p>' +
                        '<details><summary><strong>View Complete JSON</strong></summary>' +
                        '<pre style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 10px;">' + 
                        JSON.stringify(data.data, null, 2) + 
                        '</pre></details>' +
                        '<p style="margin-top: 15px; color: #28a745;"><strong>✓ Saved to master database</strong></p>';
                    
                    // Clear form
                    document.getElementById('note').value = '';
                    document.getElementById('patient_id').value = '';
                    
                    // Update stats
                    loadStats();
                } else {
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = 
                        '<h3>❌ Extraction Failed</h3>' +
                        '<p><strong>Error:</strong> ' + data.error + '</p>' +
                        '<p>Please check your clinical note format and try again.</p>';
                }
                
                resultDiv.style.display = 'block';
                
            } catch (error) {
                resultDiv.className = 'result error';
                resultDiv.innerHTML = 
                    '<h3>❌ Connection Error</h3>' +
                    '<p><strong>Error:</strong> ' + error.message + '</p>';
                resultDiv.style.display = 'block';
            }
            
            // Reset button
            btn.disabled = false;
            btn.innerHTML = '🔍 Extract Data with AI';
        }
        
        // Allow Enter key to submit
        document.getElementById('patient_id').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') extract();
        });
    </script>
</body>
</html>
    '''

@app.route('/api/extract', methods=['POST'])
def extract():
    try:
        data = request.json
        clinical_note = data.get('text', '')
        patient_id = data.get('patient_id', '')
        
        if not clinical_note or not patient_id:
            return jsonify({'success': False, 'error': 'Missing clinical note or patient ID'}), 400
        
        # Extraction prompt
        prompt = f"""You are an expert clinical data extraction specialist. Extract structured data from this clinical note.

Clinical Note:
{clinical_note}

Extract the following fields and return ONLY valid JSON with no markdown, no preamble:

{{
  "patient_id": "{patient_id}",
  "address": "Extract text after 'Address'",
  "age_years": "Extract age as number only (e.g., '54 year old' → '54')",
  "gender": "Male or Female",
  "occupation": "Extract from biodata or 'NA'",
  "presenting_complaints": ["Array of main symptoms"],
  "duration_of_symptoms": "Duration (e.g., '3 days', '1/12')",
  "referral_source": "'Report' if referred mentioned, else 'Self'",
  "comorbidities_present": "'True' if history of DM/HTN/PUD/Asthma mentioned, else 'False'",
  "comorbidities_list": ["List comorbidities or ['NA']"],
  "diagnosis": "Primary diagnosis",
  "category_of_emergency": "'Medical', 'Surgical', or 'Trauma'",
  "triage_level": "'Mild', 'Moderate', or 'Severe' based on severity",
  "vitals_bp": "Blood pressure (e.g., '120/80mmHg')",
  "vitals_pr": "Pulse rate (e.g., '88b/m')",
  "vitals_rr": "Respiratory rate (e.g., '20c/m')",
  "vitals_temperature": "Temperature (e.g., '36.5C')",
  "vitals_spo2": "SpO2 percentage or 'NA'",
  "vitals_gcs": "GCS score or 'NA'",
  "initial_treatment": ["Array of treatments from PLAN"],
  "treat_antibiotics": "'True' if antibiotics present, else 'False'",
  "treat_analgesics": "'True' if analgesics present, else 'False'",
  "treat_ivfluid": "'True' if IV fluids mentioned, else 'False'",
  "treat_oxygen": "'True' if oxygen mentioned, else 'False'",
  "outcome": "'Discharge' or 'Admitted' or 'Died' or 'LAMA'"
}}

Return ONLY the JSON object."""

        # Call Gemini API (FREE)
        response = model.generate_content(prompt)
        extracted = response.text.strip()
        
        # Clean up response
        extracted = extracted.replace('```json', '').replace('```', '').strip()
        
        # Parse JSON
        data_dict = json.loads(extracted)
        data_dict['date_added'] = datetime.now().isoformat()
        
        # Save to SQLite database
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO patients VALUES (?, ?, ?)',
                  (patient_id, data_dict['date_added'], json.dumps(data_dict)))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'data': data_dict})
    
    except json.JSONDecodeError as e:
        return jsonify({'success': False, 'error': f'Failed to parse AI response: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/csv')
def export_csv():
    """Excel connects to this endpoint!"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT data_json FROM patients ORDER BY date_added DESC')
        
        rows = []
        for row in c.fetchall():
            rows.append(json.loads(row[0]))
        
        conn.close()
        
        if not rows:
            return "patient_id,date_added,diagnosis,outcome\n", 200, {'Content-Type': 'text/csv'}
        
        # Convert to CSV
        import csv
        from io import StringIO
        
        output = StringIO()
        
        # Get all unique keys
        all_keys = set()
        for row in rows:
            all_keys.update(row.keys())
        
        fieldnames = sorted(all_keys)
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in rows:
            # Convert arrays to strings
            clean_row = {}
            for k, v in row.items():
                if isinstance(v, list):
                    clean_row[k] = '; '.join(str(x) for x in v)
                else:
                    clean_row[k] = v
            writer.writerow(clean_row)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment;filename=clinical_master_data.csv'}
        )
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/api/stats')
def stats():
    """Get database statistics"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM patients')
        total = c.fetchone()[0]
        conn.close()
        return jsonify({'total': total})
    except:
        return jsonify({'total': 0})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
