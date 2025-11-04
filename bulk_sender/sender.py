# SCRIPT DE ENVÍO CON INFORMES v2 - THE JANITOR
import os
import csv
import time
import requests
import random
import argparse
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional, Tuple
import sys
from datetime import datetime

sys.tracebacklimit = 0

def load_environment():
    if not os.path.exists('.secrets.env'):
        print("❌ ERROR: Secrets file '.secrets.env' not found.")
        sys.exit(1)
    load_dotenv(dotenv_path='.secrets.env')
    required_vars = ['EVOLUTION_API_URL', 'EVOLUTION_API_KEY', 'EVOLUTION_INSTANCE_NAME']
    if missing_vars := [v for v in required_vars if not os.getenv(v)]:
        print(f"❌ ERROR: Missing environment variables in '.secrets.env': {', '.join(missing_vars)}")
        sys.exit(1)

def send_text_message(api_url: str, api_key: str, instance_name: str, number: str, message: str) -> Tuple[bool, str]:
    endpoint = f"{api_url}/message/sendText/{instance_name}"
    headers = {"apikey": api_key}
    payload = {"number": number, "options": {"delay": 1200, "presence": "composing"}, "text": message}
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=20)
        if response.status_code in [200, 201]:
            msg_id = response.json().get('key', {}).get('id', 'N/A')
            return True, msg_id
        else:
            return False, f"Status: {response.status_code}, Response: {response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Connection ERROR: {e}"

def send_media_message(api_url: str, api_key: str, instance_name: str, number: str, media_path: str) -> Tuple[bool, str]:
    endpoint = f"{api_url}/message/sendMedia/{instance_name}"
    headers = {"apikey": api_key}
    try:
        with open(media_path, 'rb') as f:
            files = {'file': (os.path.basename(media_path), f)}
            data = {'number': number, 'options[delay]': 1200, 'options[presence]': 'composing', 'mediatype': 'video'}
            response = requests.post(endpoint, headers=headers, data=data, files=files, timeout=30)
        if response.status_code in [200, 201]:
            msg_id = response.json().get('key', {}).get('id', 'N/A')
            return True, msg_id
        else:
            return False, f"Status: {response.status_code}, Response: {response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Connection ERROR: {e}"
    except FileNotFoundError:
        print(f"❌ FATAL: Video file not found at path: {media_path}")
        sys.exit(1)

def clean_phone_number(phone: str) -> Optional[str]:
    if not phone: return None
    cleaned = ''.join(filter(str.isdigit, phone.strip()))
    return f"57{cleaned[-10:]}" if len(cleaned) >= 10 else None

def read_contacts(csv_path: str) -> List[Dict[str, str]]:
    if not os.path.exists(csv_path):
        print(f"❌ FATAL: CSV file not found at '{csv_path}'")
        sys.exit(1)
    contacts = []
    try:
        with open(csv_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for i, row in enumerate(reader):
                name = row.get("Nombre Propietario", "").strip()
                phone = row.get("Telefono Propietario", "")
                if name and (clean_number := clean_phone_number(phone)):
                    contacts.append({"name": name, "phone": clean_number})
                else:
                    print(f"⏭️  Skipping row {i+2}: Incomplete data or invalid phone ('{phone}')")
    except Exception as e:
        print(f"❌ FATAL: Error reading CSV file: {e}")
        sys.exit(1)
    return contacts

def read_message_template(file_path: str) -> str:
    if not os.path.exists(file_path):
        print(f"❌ FATAL: Message file not found at '{file_path}'")
        sys.exit(1)
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read().strip()

def setup_report_writer(directory: str) -> Tuple[Any, Any]:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_filename = f"sending_report_{timestamp}.csv"
    report_path = os.path.join(directory, report_filename)

    file = open(report_path, 'w', newline='', encoding='utf-8')
    writer = csv.writer(file)
    writer.writerow(['timestamp', 'phone_number', 'contact_name', 'message_type', 'status', 'details'])

    print(f"📄 Report will be generated at: {report_path}")
    return file, writer

def log_to_report(writer, contact, msg_type, status, details):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    writer.writerow([timestamp, contact['phone'], contact['name'], msg_type, status, details])

def main():
    parser = argparse.ArgumentParser(description="WhatsApp sequential bulk sender with CSV reporting.")
    parser.add_argument("csv_file", help="Path to the .csv file with contacts.")
    parser.add_argument("message_file", help="Path to the .txt file with the message. Use {name} as placeholder.")
    parser.add_argument("video_file", help="Path to the video file to be sent.")
    args = parser.parse_args()

    load_environment()
    api_url, api_key, instance_name = os.getenv('EVOLUTION_API_URL'), os.getenv('EVOLUTION_API_KEY'), os.getenv('EVOLUTION_INSTANCE_NAME')

    print("--- STARTING SEQUENTIAL BULK SENDING PROCESS ---")

    report_file, report_writer = setup_report_writer(os.path.dirname(args.csv_file))

    contacts = read_contacts(args.csv_file)
    message_template = read_message_template(args.message_file)

    if not contacts:
        print("⚠️ No valid contacts found. Aborting.")
        report_file.close()
        return

    total = len(contacts)
    print(f"✅ Found {total} valid contacts.")
    sent_count, failed_count = 0, 0

    try:
        for i, contact in enumerate(contacts):
            print(f"\n--- Processing {i+1}/{total} for {contact['name']} ({contact['phone']}) ---")

            first_name = contact['name'].split()[0]
            personalized_message = message_template.replace("{nombre}", first_name)

            text_sent, text_details = send_text_message(api_url, api_key, instance_name, contact['phone'], personalized_message)
            log_to_report(report_writer, contact, 'TEXT', 'SUCCESS' if text_sent else 'FAILED', text_details)

            if text_sent:
                text_video_delay = random.uniform(2.5, 4.0)
                print(f"  ⏱️  Waiting {text_video_delay:.2f}s before sending video...")
                time.sleep(text_video_delay)

                video_sent, video_details = send_media_message(api_url, api_key, instance_name, contact['phone'], args.video_file)
                log_to_report(report_writer, contact, 'VIDEO', 'SUCCESS' if video_sent else 'FAILED', video_details)

                if video_sent:
                    sent_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1

            if i < total - 1:
                inter_contact_delay = random.uniform(5.0, 8.0)
                print(f"⏱️  Waiting {inter_contact_delay:.2f}s for the next contact...")
                time.sleep(inter_contact_delay)
    finally:
        report_file.close()

    print("\n--- PROCESS FINISHED ---")
    print(f"✔️ Sequences completed successfully: {sent_count}")
    print(f"❌ Failed sequences: {failed_count}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🚫 Process interrupted by user. Aborting.")
        sys.exit(0)