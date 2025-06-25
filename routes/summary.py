from flask import Blueprint, request, jsonify
from app.services.summary import correct_transcript, summarize_transcript, configure_api

summary_bp = Blueprint('summary', __name__)

@summary_bp.route('/correct', methods=['POST'])
def correct():
    """API endpoint to correct transcript text"""
    data = request.json
    if not data or 'text' not in data:
        return jsonify({"error": "Missing text in request"}), 400
    
    provider = data.get('provider', 'gemini')
    model = data.get('model', None)
    
    try:
        configure_api(provider=provider)
        corrected_text = correct_transcript(data['text'], provider=provider, model_name=model)
        return jsonify({"corrected_text": corrected_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@summary_bp.route('/summarize', methods=['POST'])
def summarize():
    """API endpoint to summarize transcript text"""
    data = request.json
    if not data or 'text' not in data:
        return jsonify({"error": "Missing text in request"}), 400
    
    provider = data.get('provider', 'gemini')
    model = data.get('model', None)
    
    try:
        configure_api(provider=provider)
        summary_text = summarize_transcript(data['text'], provider=provider, model_name=model)
        return jsonify({"summary": summary_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500