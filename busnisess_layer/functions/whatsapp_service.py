"""
WhatsApp Cloud API Service — Meta Business API Integration
Sends appointment notifications to patients via WhatsApp when visits are booked.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

# ── Configuration (read from environment) ──────────────────────────────────
WHATSAPP_API_TOKEN = os.environ.get('WHATSAPP_API_TOKEN', '')
WHATSAPP_PHONE_ID = os.environ.get('WHATSAPP_PHONE_ID', '201019278838')
WHATSAPP_TEMPLATE_NAME = os.environ.get('WHATSAPP_TEMPLATE_NAME', 'hello_world')
SITE_URL = os.environ.get('SITE_URL', 'https://alteb.almarkazy.com')

GRAPH_API_URL = f"https://graph.facebook.com/v25.0/{WHATSAPP_PHONE_ID}/messages"


def _format_phone_for_whatsapp(phone: str) -> str:
    """
    Convert a local Egyptian phone number to international format for WhatsApp.
    Examples:
        '01550010435'  →  '201550010435'
        '1550010435'   →  '201550010435'
        '201550010435' →  '201550010435'  (already international)
    """
    if not phone:
        return ''
    
    # Remove any spaces, dashes, or plus signs
    phone = phone.strip().replace(' ', '').replace('-', '').replace('+', '')
    
    # Already in international format (starts with 20 and is 12 digits)
    if phone.startswith('20') and len(phone) == 12:
        return phone
    
    # Local format starting with 0 (e.g., 01550010435)
    if phone.startswith('0') and len(phone) == 11:
        return '20' + phone[1:]
    
    # Without leading zero (e.g., 1550010435)
    if len(phone) == 10 and not phone.startswith('0'):
        return '20' + phone
    
    # Fallback: return as-is (let Meta API handle validation)
    return phone


def send_appointment_whatsapp(
    patient_phone: str,
    clinic_name: str,
    doctor_name: str,
    appointment_date: str,
    appointment_time: str,
    auto_lookup_url: str
) -> dict:
    """
    Send appointment confirmation via WhatsApp using Meta Cloud API template message.
    
    Args:
        patient_phone: Patient's phone number (local or international)
        clinic_name: Name of the clinic
        doctor_name: Name of the doctor
        appointment_date: Formatted appointment date string
        appointment_time: Formatted appointment time string
        auto_lookup_url: Full URL for auto-lookup (e.g., https://alteb.almarkazy.com/patient/auto/TOKEN)
    
    Returns:
        dict with 'success' (bool) and 'message' or 'error'
    """
    if not WHATSAPP_API_TOKEN:
        logger.warning("WHATSAPP_API_TOKEN not set — skipping WhatsApp notification")
        return {'success': False, 'error': 'WhatsApp API token not configured'}
    
    formatted_phone = _format_phone_for_whatsapp(patient_phone)
    if not formatted_phone:
        logger.warning(f"Invalid phone number: {patient_phone}")
        return {'success': False, 'error': 'Invalid phone number'}
    
    headers = {
        'Authorization': f'Bearer {WHATSAPP_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Build template message with parameters
    payload = {
        "messaging_product": "whatsapp",
        "to": formatted_phone,
        "type": "template",
        "template": {
            "name": WHATSAPP_TEMPLATE_NAME,
            "language": {
                "code": "ar"  # Arabic
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": clinic_name},
                        {"type": "text", "text": doctor_name},
                        {"type": "text", "text": appointment_date},
                        {"type": "text", "text": appointment_time},
                        {"type": "text", "text": auto_lookup_url}
                    ]
                }
            ]
        }
    }
    
    try:
        response = requests.post(GRAPH_API_URL, json=payload, headers=headers, timeout=10)
        response_data = response.json()
        
        if response.status_code == 200:
            msg_id = response_data.get('messages', [{}])[0].get('id', 'unknown')
            logger.info(f"✅ WhatsApp sent to {formatted_phone} — message_id: {msg_id}")
            return {'success': True, 'message_id': msg_id}
        else:
            error_msg = response_data.get('error', {}).get('message', response.text)
            logger.error(f"❌ WhatsApp API error ({response.status_code}): {error_msg}")
            return {'success': False, 'error': error_msg}
    
    except requests.exceptions.Timeout:
        logger.error(f"❌ WhatsApp API timeout for {formatted_phone}")
        return {'success': False, 'error': 'API request timed out'}
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ WhatsApp API request failed: {str(e)}")
        return {'success': False, 'error': str(e)}


def build_auto_lookup_url(lookup_token: str) -> str:
    """Build the full auto-lookup URL for a visit."""
    base_url = SITE_URL.rstrip('/')
    return f"{base_url}/patient/auto/{lookup_token}"
